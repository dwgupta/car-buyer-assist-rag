"""
Application configuration and constants.

Centralizes paths, model names, and app metadata for consistency
and easier maintenance.
"""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(PROJECT_ROOT / "chroma_db"))

# Vertex AI
VERTEX_AI_MODEL = "gemini-2.5-pro"
EMBEDDING_MODEL = "text-embedding-005"

# Document processing (Design Doc §3.1)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
CHROMA_COLLECTION_NAME = "car_buyer_assist"

# App metadata
APP_TITLE = "Car Buyer Assist"
APP_DESCRIPTION = "Get instant, accurate answers about Toyota vehicles using conversational AI"
VEHICLE_MODELS = [
    "Corolla",
    "Camry",
    "RAV4",
    "Highlander",
    "Prius",
    "Prius Prime",
    "Tacoma",
    "bZ4X",
]
EXAMPLE_QUERIES = [
    "What is the fuel efficiency of the Camry hybrid?",
    "Compare RAV4 and Highlander for families",
    "What safety features does the Corolla have?",
    "What Toyota vehicle is best for a family of five?",
]
