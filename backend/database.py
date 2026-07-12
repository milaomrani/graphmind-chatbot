import logging
from neo4j import GraphDatabase
from backend import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jDatabase:
    def __init__(self):
        self.uri = config.NEO4J_URI
        self.user = config.NEO4J_USER
        self.password = config.NEO4J_PASSWORD
        self._driver = None
        self.connect()

    def connect(self):
        try:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j database.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self._driver = None

    def close(self):
        if self._driver:
            self._driver.close()
            logger.info("Neo4j database connection closed.")

    def execute_query(self, query, parameters=None):
        if not self._driver:
            logger.warning("No active driver connection. Attempting to reconnect...")
            self.connect()
            if not self._driver:
                raise Exception("Neo4j driver is not available.")
        
        with self._driver.session() as session:
            try:
                result = session.run(query, parameters)
                return list(result)
            except Exception as e:
                logger.error(f"Error executing Cypher query: {e}\nQuery: {query}")
                raise e

    def get_graph(self):
        """
        Retrieves the entire graph structure formatted for frontend graph visualization.
        """
        query = """
        MATCH (n:Concept)
        OPTIONAL MATCH (n)-[r]->(m:Concept)
        RETURN n, r, m, elementId(n) as n_id, elementId(m) as m_id, elementId(r) as r_id
        """
        try:
            records = self.execute_query(query)
            nodes_dict = {}
            edges = []

            for record in records:
                # Process source node n
                n = record.get("n")
                n_id = record.get("n_id")
                if n is not None and n_id is not None:
                    name = n.get("name", "Unknown")
                    if n_id not in nodes_dict:
                        label = n.get("category", "Concept")
                        nodes_dict[n_id] = {
                            "id": n_id,
                            "label": name,
                            "group": label,
                            "properties": dict(n)
                        }

                # Process target node m and relationship r
                r = record.get("r")
                m = record.get("m")
                m_id = record.get("m_id")
                edge_id = record.get("r_id")
                if r is not None and m is not None and m_id is not None and edge_id is not None:
                    m_name = m.get("name", "Unknown")
                    if m_id not in nodes_dict:
                        m_label = m.get("category", "Concept")
                        nodes_dict[m_id] = {
                            "id": m_id,
                            "label": m_name,
                            "group": m_label,
                            "properties": dict(m)
                        }
                    
                    # Prevent duplicates in edge list
                    if not any(e["id"] == edge_id for e in edges):
                        edges.append({
                            "id": edge_id,
                            "from": n_id,
                            "to": m_id,
                            "label": r.type,
                            "properties": dict(r)
                        })

            return {
                "nodes": list(nodes_dict.values()),
                "edges": edges
            }
        except Exception as e:
            logger.error(f"Failed to fetch graph data: {e}")
            return {"nodes": [], "edges": []}

    def clear_database(self):
        """
        Deletes all nodes and relationships.
        """
        query = "MATCH (n) DETACH DELETE n"
        self.execute_query(query)
        logger.info("Database cleared.")

    def seed_database(self):
        """
        Seeds the Neo4j database with an initial 'AI & Tech Concepts' graph if empty.
        """
        # First, check if database is empty
        check_query = "MATCH (n) RETURN count(n) as count"
        res = self.execute_query(check_query)
        if res and res[0]["count"] > 0:
            logger.info("Database is already seeded. Skipping seed.")
            return False

        logger.info("Seeding Neo4j database with AI & Tech Concepts graph...")

        # Setup Constraints/Indexes (using newer Cypher syntax for Neo4j 5.x)
        try:
            self.execute_query("CREATE CONSTRAINT unique_concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE")
        except Exception as e:
            logger.warning(f"Could not create constraint (might be community edition or permission issue): {e}")

        # List of concepts (Nodes)
        concepts = [
            # Core AI
            {"name": "Artificial Intelligence", "label": "CoreAI", "desc": "The broad simulation of human intelligence processes by machines."},
            {"name": "Machine Learning", "label": "CoreAI", "desc": "A subset of AI that allows software applications to learn from data without explicit programming."},
            {"name": "Deep Learning", "label": "CoreAI", "desc": "A subset of Machine Learning based on artificial neural networks with multiple layers."},
            {"name": "Neural Networks", "label": "CoreAI", "desc": "Computing systems vaguely inspired by biological neural networks."},
            
            # NLP & Transformers
            {"name": "Transformers", "label": "NLP", "desc": "A deep learning model architecture introduced in 2017 utilizing self-attention mechanisms."},
            {"name": "Large Language Models", "label": "NLP", "desc": "Advanced language models trained on massive text datasets (e.g. GPT-4, Gemini)."},
            {"name": "Generative AI", "label": "NLP", "desc": "AI systems capable of generating text, images, code, or other media in response to prompts."},
            
            # Databases & Search
            {"name": "Knowledge Graphs", "label": "Database", "desc": "A network of real-world entities and their interrelations, stored in a graph structure."},
            {"name": "Vector Database", "label": "Database", "desc": "A database designed to store and query high-dimensional vector embeddings efficiently."},
            {"name": "Neo4j", "label": "Database", "desc": "A popular open-source native graph database management system."},
            
            # RAG & Agents
            {"name": "Retrieval-Augmented Generation", "label": "RAG", "desc": "A technique to optimize LLM output by querying an external knowledge base first."},
            {"name": "Graph RAG", "label": "RAG", "desc": "A RAG pattern that uses structured knowledge graphs instead of or alongside vector databases."},
            {"name": "Agentic Workflows", "label": "Agent", "desc": "Iterative, stateful LLM design patterns where agents can plan, act, and use tools autonomously."},
            {"name": "LangChain", "label": "Framework", "desc": "A popular open-source framework designed to simplify the creation of LLM-based applications."},
            {"name": "LangGraph", "label": "Framework", "desc": "An extension of LangChain designed for building stateful multi-agent system applications."}
        ]

        # Insert nodes
        for c in concepts:
            query = """
            MERGE (c:Concept {name: $name})
            SET c.description = $desc, c.category = $label
            """
            self.execute_query(query, {"name": c["name"], "desc": c["desc"], "label": c["label"]})

        # Define relationships
        relationships = [
            ("Machine Learning", "SUBFIELD_OF", "Artificial Intelligence"),
            ("Deep Learning", "SUBFIELD_OF", "Machine Learning"),
            ("Deep Learning", "USES", "Neural Networks"),
            ("Deep Learning", "EVOLVED_INTO", "Transformers"),
            ("Transformers", "POWER", "Large Language Models"),
            ("Large Language Models", "USED_IN", "Generative AI"),
            ("Generative AI", "IMPLEMENTS", "Retrieval-Augmented Generation"),
            ("Retrieval-Augmented Generation", "EVOLVED_INTO", "Graph RAG"),
            ("Retrieval-Augmented Generation", "USES", "Vector Database"),
            ("Graph RAG", "USES", "Neo4j"),
            ("Graph RAG", "COMBINES", "Retrieval-Augmented Generation"),
            ("Graph RAG", "COMBINES", "Knowledge Graphs"),
            ("Neo4j", "STORES", "Knowledge Graphs"),
            ("LangChain", "INTEGRATES_WITH", "Neo4j"),
            ("LangChain", "BUILDS", "Retrieval-Augmented Generation"),
            ("LangGraph", "EXTENDS", "LangChain"),
            ("LangGraph", "BUILDS", "Agentic Workflows"),
            ("Agentic Workflows", "CAN_IMPLEMENT", "Graph RAG")
        ]

        # Insert relationships
        for source, rel_type, target in relationships:
            query = f"""
            MATCH (a:Concept {{name: $source}})
            MATCH (b:Concept {{name: $target}})
            MERGE (a)-[r:{rel_type}]->(b)
            """
            self.execute_query(query, {"source": source, "target": target})

        logger.info("Database successfully seeded with default tech concepts graph!")
        return True

# Initialize a global db instance
db = Neo4jDatabase()
if __name__ == "__main__":
    # Test seeding
    db.seed_database()
    print("Graph retrieved:")
    print(db.get_graph())
