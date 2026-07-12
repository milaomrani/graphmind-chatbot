import json
import logging
from typing import List, Dict, Any, TypedDict, Optional
from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

from backend import config
from backend.database import db

logger = logging.getLogger(__name__)

# Initialize LLM based on configuration
def get_llm():
    if config.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        if not config.OPENAI_API_KEY:
            raise ValueError("OpenAI LLM provider selected but OPENAI_API_KEY is not set.")
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.1, openai_api_key=config.OPENAI_API_KEY)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not config.GEMINI_API_KEY:
            raise ValueError("Google Gemini LLM provider selected but GEMINI_API_KEY is not set.")
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1, google_api_key=config.GEMINI_API_KEY)

# Define State Structure
class AgentState(TypedDict):
    messages: List[BaseMessage]
    extracted_entities: List[str]
    discovered_relations: List[Dict[str, str]]  # list of {"source": "...", "target": "...", "type": "...", "desc": "..."}
    subgraph_nodes: List[Dict[str, Any]]
    subgraph_edges: List[Dict[str, Any]]
    cypher_queries: List[str]
    response: str

# Helper to parse JSON from LLM output
def parse_json_safely(text: str) -> Dict[str, Any]:
    text = text.strip()
    # Strip markdown formatting if present
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}. Raw text: {text}")
        return {}

# 1. Node: Extract Entities and Identify New Relationships
def extract_entities(state: AgentState) -> Dict[str, Any]:
    logger.info("--- NODE: EXTRACT ENTITIES ---")
    last_message = state["messages"][-1].content
    
    # Check if there are concepts already in the db to help LLM match names
    existing_concepts_res = db.execute_query("MATCH (c:Concept) RETURN c.name as name")
    existing_names = [r["name"] for r in existing_concepts_res] if existing_concepts_res else []
    existing_names_str = ", ".join(existing_names)

    system_prompt = """
    You are an AI specialized in building and expanding Knowledge Graphs.
    Given a user's prompt, you need to:
    1. Identify any key concepts, technologies, terms, or entities they are asking about or mentioning.
    2. Try to map these terms to existing concepts in our database if they are similar (Existing concepts: {existing_concepts}).
    3. Determine if the user is introducing or implying a NEW relationship or concept that should be added to the graph database.
       - A relationship represents how two concepts connect (e.g., 'React' --USES--> 'Javascript').
       - If they ask a simple query, just extract the concepts.
       - If they explain a new fact, e.g., 'Antigravity is built by Google Deepmind', extract:
         * Entities: 'Antigravity', 'Google Deepmind'
         * Relationship: Source: 'Antigravity', Target: 'Google Deepmind', Type: 'BUILT_BY', Description: 'Antigravity is an agentic coding assistant built by Google Deepmind.'
       - Keep relationship types short, uppercase, and with underscores (e.g., 'BUILT_BY', 'INTEGRATES_WITH', 'USES', 'SUBFIELD_OF').

    Respond ONLY with a JSON object of this structure:
    {{
        "concepts": ["Concept1", "Concept2"],
        "new_relations": [
            {{
                "source": "Concept1",
                "target": "Concept2",
                "type": "RELATIONSHIP_TYPE",
                "description": "Short explanation of this relationship"
            }}
        ]
    }}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "User Prompt: {user_prompt}")
    ])
    
    try:
        llm = get_llm()
        chain = prompt | llm
        result = chain.invoke({
            "existing_concepts": existing_names_str,
            "user_prompt": last_message
        })
        
        parsed = parse_json_safely(result.content)
        concepts = parsed.get("concepts", [])
        new_relations = parsed.get("new_relations", [])
        
        logger.info(f"Extracted concepts: {concepts}")
        if new_relations:
            logger.info(f"Discovered new relations: {new_relations}")
            
        return {
            "extracted_entities": concepts,
            "discovered_relations": new_relations
        }
    except Exception as e:
        logger.error(f"Error extracting entities: {e}")
        return {"extracted_entities": [], "discovered_relations": []}

# 2. Node: Update the Graph Database (if new relations are found)
def update_graph(state: AgentState) -> Dict[str, Any]:
    logger.info("--- NODE: UPDATE GRAPH ---")
    discovered = state.get("discovered_relations", [])
    queries = []
    
    if not discovered:
        logger.info("No new relationships discovered to insert.")
        return {"cypher_queries": []}

    for rel in discovered:
        source = rel.get("source")
        target = rel.get("target")
        rel_type = rel.get("type", "RELATES_TO").upper().replace(" ", "_")
        desc = rel.get("description", "")
        
        if not source or not target:
            continue

        # Cypher query to merge nodes and relationships
        query = f"""
        MERGE (s:Concept {{name: $source}})
        ON CREATE SET s.category = 'Discovered', s.description = 'Discovered concept'
        MERGE (t:Concept {{name: $target}})
        ON CREATE SET t.category = 'Discovered', t.description = 'Discovered concept'
        MERGE (s)-[r:{rel_type}]->(t)
        ON CREATE SET r.description = $desc
        RETURN s, r, t
        """
        try:
            db.execute_query(query, {"source": source, "target": target, "desc": desc})
            queries.append(f"MERGE (s:Concept {{name: '{source}'}}) -[:{rel_type}]-> (t:Concept {{name: '{target}'}})")
            logger.info(f"Inserted relationship: {source} -> {rel_type} -> {target}")
        except Exception as e:
            logger.error(f"Failed to execute merge query: {e}")

    # Add the extracted concepts of these new relations to extracted_entities to ensure they are fetched in the context retrieval
    new_concepts = []
    for rel in discovered:
        if rel.get("source") not in state["extracted_entities"]:
            new_concepts.append(rel.get("source"))
        if rel.get("target") not in state["extracted_entities"]:
            new_concepts.append(rel.get("target"))

    return {
        "cypher_queries": queries,
        "extracted_entities": list(set(state["extracted_entities"] + new_concepts))
    }

# 3. Node: Query Graph Context from Neo4j
def query_graph_context(state: AgentState) -> Dict[str, Any]:
    logger.info("--- NODE: QUERY GRAPH CONTEXT ---")
    entities = state.get("extracted_entities", [])
    queries = []
    nodes_dict = {}
    edges = []

    if not entities:
        logger.info("No concepts extracted. Skipping query.")
        return {"subgraph_nodes": [], "subgraph_edges": [], "cypher_queries": []}

    # Fetch context for each extracted concept
    for entity in entities:
        # We query the node itself and its immediate 1-step relationships (in or out)
        query = """
        MATCH (c:Concept)
        WHERE toLower(c.name) = toLower($name)
        OPTIONAL MATCH (c)-[r]-(neighbor:Concept)
        RETURN c, r, neighbor,
               elementId(c) as c_id,
               elementId(neighbor) as neighbor_id,
               elementId(r) as r_id,
               elementId(startNode(r)) as start_id,
               elementId(endNode(r)) as end_id
        LIMIT 15
        """
        queries.append(f"MATCH (c:Concept {{name: '{entity}'}}) OPTIONAL MATCH (c)-[r]-(neighbor:Concept) RETURN c, r, neighbor LIMIT 15")
        
        try:
            records = db.execute_query(query, {"name": entity})
            for record in records:
                c = record.get("c")
                c_id = record.get("c_id")
                if c is not None and c_id is not None:
                    c_name = c.get("name", "Unknown")
                    if c_id not in nodes_dict:
                        nodes_dict[c_id] = {
                            "id": c_id,
                            "label": c_name,
                            "group": c.get("category", "Concept"),
                            "properties": dict(c)
                        }

                r = record.get("r")
                neighbor = record.get("neighbor")
                neighbor_id = record.get("neighbor_id")
                edge_id = record.get("r_id")
                from_id = record.get("start_id")
                to_id = record.get("end_id")
                
                if (r is not None and neighbor is not None and neighbor_id is not None 
                        and edge_id is not None and from_id is not None and to_id is not None):
                    n_name = neighbor.get("name", "Unknown")
                    if neighbor_id not in nodes_dict:
                        nodes_dict[neighbor_id] = {
                            "id": neighbor_id,
                            "label": n_name,
                            "group": neighbor.get("category", "Concept"),
                            "properties": dict(neighbor)
                        }
                    
                    # Prevent duplicates in edge list
                    if not any(e["id"] == edge_id for e in edges):
                        edges.append({
                            "id": edge_id,
                            "from": from_id,
                            "to": to_id,
                            "label": r.type,
                            "properties": dict(r)
                        })

        except Exception as e:
            logger.error(f"Error querying context for {entity}: {e}")

    logger.info(f"Retrieved {len(nodes_dict)} nodes and {len(edges)} edges from Neo4j.")
    return {
        "subgraph_nodes": list(nodes_dict.values()),
        "subgraph_edges": edges,
        "cypher_queries": queries
    }

# 4. Node: Generate Answer
def generate_answer(state: AgentState) -> Dict[str, Any]:
    logger.info("--- NODE: GENERATE ANSWER ---")
    messages = state["messages"]
    nodes = state.get("subgraph_nodes", [])
    edges = state.get("subgraph_edges", [])

    # Format the subgraph context as a readable string for the LLM
    context_str = ""
    if nodes:
        context_str += "Concepts Found in Knowledge Graph:\n"
        for n in nodes:
            props = n["properties"]
            desc = props.get("description", "No description.")
            cat = props.get("category", "Uncategorized")
            context_str += f"- {n['label']} ({cat}): {desc}\n"
        
        if edges:
            context_str += "\nRelationships Connects:\n"
            for e in edges:
                # Resolve names
                from_name = next((n["label"] for n in nodes if n["id"] == e["from"]), "Unknown")
                to_name = next((n["label"] for n in nodes if n["id"] == e["to"]), "Unknown")
                context_str += f"- {from_name} --[{e['label']}]--> {to_name}\n"
    else:
        context_str = "No directly relevant concepts found in the knowledge graph. Use your general knowledge but mention that this wasn't found in the graph."

    system_prompt = f"""
    You are GraphMind, a helpful chatbot specialized in exploring and explanation based on a Knowledge Graph.
    You have queried a Neo4j Graph Database and retrieved the following subgraph context:
    ---
    {context_str}
    ---
    
    Guidelines:
    1. Answer the user's question accurately using the provided Graph Context.
    2. Explicitly mention relationships and connections that are present in the graph (e.g. 'Since Graph RAG uses Neo4j...').
    3. If answering with general AI knowledge (because the database doesn't cover all details), explain that you are augmenting the graph context with general knowledge.
    4. Keep your answer engaging, structured, and easy to read. Use Markdown formatting.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        # Pass conversation history except latest user message (since prompt handles it)
        *messages
    ])

    try:
        llm = get_llm()
        chain = prompt | llm
        response = chain.invoke({})
        return {"response": response.content}
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return {"response": "I'm sorry, I encountered an error while trying to generate my response."}

# Build LangGraph Workflow
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("extract_entities", extract_entities)
workflow.add_node("update_graph", update_graph)
workflow.add_node("query_graph_context", query_graph_context)
workflow.add_node("generate_answer", generate_answer)

# Connect Nodes (Sequential Workflow)
workflow.add_edge(START, "extract_entities")
workflow.add_edge("extract_entities", "update_graph")
workflow.add_edge("update_graph", "query_graph_context")
workflow.add_edge("query_graph_context", "generate_answer")
workflow.add_edge("generate_answer", END)

# Compile Graph
graph_agent = workflow.compile()
