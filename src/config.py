# src/config.py - CONFIGURATION
"""
Central configuration for the Legal RAG system.
Set all environment variables in a .env file at the project root.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# ============================================================================
# BASE PATHS
# ============================================================================

BASE_DIR = Path(__file__).parent.parent  # Project root
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = BASE_DIR / "uploads"

# ============================================================================
# STORAGE FILES
# ============================================================================

CHUNKS_PATH = STORAGE_DIR / "chunks.jsonl"
CHROMA_PATH = STORAGE_DIR / "chroma"

# ============================================================================
# API KEYS & MODELS
# ============================================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
YOU_API_KEY = os.getenv("YOU_API_KEY", "")

# ============================================================================
# RETRIEVAL & GENERATION PARAMETERS
# ============================================================================

TOP_K = int(os.getenv("TOP_K", 12))           # Number of internal chunks to retrieve
MAX_RERANKED = int(os.getenv("MAX_RERANKED", 6))  # Max chunks to use in answer
TEMPERATURE = float(os.getenv("TEMPERATURE", 0))  # Generation temperature

# ============================================================================
# EMBEDDING MODEL
# ============================================================================

EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # SentenceTransformer model

# ============================================================================
# CREATE DIRECTORIES
# ============================================================================

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "chroma").mkdir(parents=True, exist_ok=True)

print("✅ Configuration loaded. API keys available:", {
    "GROQ": bool(GROQ_API_KEY),
    "YOU_API": bool(YOU_API_KEY),
    "Storage": str(STORAGE_DIR),
})
