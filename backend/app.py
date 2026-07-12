import os
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from langchain_core.messages import HumanMessage, AIMessage
from backend import config
from backend.database import db
from backend.agent import graph_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GraphMind API",
    description="Backend API for GraphMind - Neo4j + LangGraph Chatbot",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatMessage(BaseModel):
    role: str # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    response: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    queries: List[str]

# Endpoints
@app.on_event("startup")
def startup_event():
    # Make sure database is seeded on startup
    try:
        db.seed_database()
    except Exception as e:
        logger.error(f"Error seeding database on startup: {e}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Convert history to LangChain messages
        lc_messages = []
        for msg in request.history:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            else:
                lc_messages.append(AIMessage(content=msg.content))
        
        # Append the new user message
        lc_messages.append(HumanMessage(content=request.message))

        # Invoke LangGraph
        initial_state = {
            "messages": lc_messages,
            "extracted_entities": [],
            "discovered_relations": [],
            "subgraph_nodes": [],
            "subgraph_edges": [],
            "cypher_queries": [],
            "response": ""
        }

        result = graph_agent.invoke(initial_state)

        # Retrieve outputs from agent final state
        bot_response = result.get("response", "I could not formulate an answer.")
        nodes = result.get("subgraph_nodes", [])
        edges = result.get("subgraph_edges", [])
        queries = result.get("cypher_queries", [])

        return ChatResponse(
            response=bot_response,
            nodes=nodes,
            edges=edges,
            queries=queries
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph")
async def get_full_graph():
    try:
        graph_data = db.get_graph()
        return graph_data
    except Exception as e:
        logger.error(f"Error fetching full graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/seed")
async def seed_graph():
    try:
        db.clear_database()
        db.seed_database()
        return {"status": "success", "message": "Database cleared and re-seeded with default concepts graph."}
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clear")
async def clear_graph():
    try:
        db.clear_database()
        return {"status": "success", "message": "Database successfully cleared."}
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve static frontend files
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/{path:path}")
    async def serve_file(path: str):
        file_path = os.path.join(frontend_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fallback to index.html for SPA router behavior if needed
        return FileResponse(os.path.join(frontend_dir, "index.html"))
else:
    logger.warning(f"Frontend directory not found at {frontend_dir}. Static file serving disabled.")
    
    @app.get("/")
    async def root_placeholder():
        return {
            "message": "GraphMind API is running. Static frontend folder not found yet.",
            "api_doc": "/docs"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=config.HOST, port=config.PORT, reload=True)
