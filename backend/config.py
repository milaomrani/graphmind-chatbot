import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

# LLM Config
# Defaults to google if GEMINI_API_KEY is found, otherwise openai if OPENAI_API_KEY is found.
# Can be explicitly set via LLM_PROVIDER ('google' or 'openai').
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LLM_PROVIDER = os.getenv("LLM_PROVIDER")
if not LLM_PROVIDER:
    if GEMINI_API_KEY:
        LLM_PROVIDER = "google"
    elif OPENAI_API_KEY:
        LLM_PROVIDER = "openai"
    else:
        # Fallback default
        LLM_PROVIDER = "google"

# Ensure API Key is available
if LLM_PROVIDER == "google" and not GEMINI_API_KEY:
    # If no key in environment, we check standard Google application credentials or print warning
    print("WARNING: GEMINI_API_KEY is not set in environment variables.")
elif LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY is not set in environment variables.")

# FastAPI host and port
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
