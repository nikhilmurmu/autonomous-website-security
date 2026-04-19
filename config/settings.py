import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = BASE_DIR / "memory" / "chroma_db"
LOGS_DIR = BASE_DIR / "logs"
CLIENTS_DIR = BASE_DIR / "clients"

# Ensure directories exist
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CLIENTS_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2:3b")
CODE_MODEL = os.getenv("CODE_MODEL", "qwen2.5-coder:3b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

COMPANY_NAME = os.getenv("COMPANY_NAME", "AutoSec AI")
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "security@autosec.ai")