# GraphMind: Dynamic Knowledge Graph Chatbot (Neo4j & LangGraph)

GraphMind is a portfolio-grade agentic chatbot that dynamically queries, updates, and visualizes structured knowledge graphs in real time. It illustrates a complete **Graph RAG** implementation using a stateful multi-agent system powered by **LangGraph**, a backend orchestrated with **FastAPI**, and an interactive, animated network graph UI rendered with **Vis.js**.

---

## 🌟 Key Features

1. **Stateful Graph Agent (LangGraph)**:
   - **Entity Extraction**: Uses LLM reasoning (Gemini or GPT) to pull core technical concepts out of plain English conversation.
   - **Context Search**: Formulates Cypher queries to lookup nodes and their 1-step neighbors in Neo4j, pulling relevant definitions and connections.
   - **Dynamic Insertion (Continuous Learning)**: If the chatbot extracts a new connection/relationship from your inputs (e.g. *"I heard that LangGraph extends LangChain"*), it executes Cypher statements to dynamically merge these entities and relations directly into Neo4j.
   - **Context-Augmented Generation**: Answers the user's question by combining local graph schemas with LLM general reasoning.
2. **Interactive 2D Graph Visualizer**:
   - Built with **Vis.js Network** module.
   - Renders nodes according to their category (CoreAI, NLP, Databases, Frameworks, etc.) with custom color styles, neon borders, and physics forces.
   - Updates dynamically in real-time as the agent discovers new nodes or traces paths.
   - Interactive camera pans and focuses on the nodes queried/returned.
   - Clicking a node pulls up a sleek glassmorphism properties overlay displaying descriptions, categories, and properties.
3. **Agent Trace Log**:
   - Houses a real-time developer terminal panel at the bottom to view the exact **Cypher queries** executed by the agent on Neo4j for transparency and debugging.

---

## 🛠️ Technology Stack

* **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism design, Flexbox/Grid), JavaScript ES6, [Vis.js Network](https://visjs.org/), [Marked.js](https://marked.js.org/).
* **Backend**: Python 3.12, [FastAPI](https://fastapi.tiangolo.com/), [LangGraph](https://langchain-ai.github.io/langgraph/), [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/).
* **Database**: [Neo4j Community Edition 5.x](https://neo4j.com/) with APOC procedures enabled, hosted inside Docker.

---

## 🚀 Getting Started

### Prerequisites

* Docker & Docker Compose installed.
* Python 3.10+ and pip.
* An API Key for **Google Gemini** (`GEMINI_API_KEY`) or **OpenAI** (`OPENAI_API_KEY`).

### Step 1: Start Neo4j Database

Spin up the Neo4j database container. It will run in the background and configure credentials automatically:

```bash
docker compose up -d
```

* **HTTP Panel**: [http://localhost:7474](http://localhost:7474) (Username: `neo4j` | Password: `password123`)
* **Bolt Protocol**: `bolt://localhost:7687`

### Step 2: Install Backend Dependencies

It is highly recommended to run inside a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### Step 3: Set Environment Variables

Create a `.env` file inside the `backend/` directory or export them directly in your shell:

```env
# Set your preferred API Key (Gemini or OpenAI)
GEMINI_API_KEY="your-google-gemini-api-key"
# OR
# OPENAI_API_KEY="your-openai-api-key"
# LLM_PROVIDER="openai"

# Optional Neo4j configs (if different from default docker-compose setup)
# NEO4J_URI="bolt://localhost:7687"
# NEO4J_USER="neo4j"
# NEO4J_PASSWORD="password123"
```

### Step 4: Run the Application

Start the FastAPI backend server:

```bash
python3 backend/app.py
```
Or use uvicorn directly:
```bash
uvicorn backend.app:app --reload
```

Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 🔮 Exploring the Agent Workflow

1. **Ask a question about the seeded graph**:
   - Prompt: *"How does LangGraph connect to Neo4j?"*
   - *Result*: The chatbot looks up the entities `LangGraph` and `Neo4j` in the database, traces their path (e.g. `LangGraph -> Agentic Workflows -> Graph RAG -> Neo4j`), explains it in chat, and automatically centers the visualization viewport on those nodes!
2. **Teach the chatbot a new connection**:
   - Prompt: *"Antigravity is an AI coding assistant built by Google Deepmind"*
   - *Result*: The chatbot detects that `Antigravity` and `Google Deepmind` are not currently connected. It writes a `MERGE` statement, updates the Neo4j graph in real-time, displays the new nodes/relationship on your canvas, and answers confirming the insertion.
3. **Developer Cypher Log**:
   - Expand the bottom panel to see the exact queries generated and run.
