import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_PATH = "/home/user/Documents/MyVault"
DB_PATH = os.path.join(BASE_DIR, "..", "chroma_db")
CACHE_FILE = os.path.join(BASE_DIR, "..", "index_cache.json")
BM25_MODEL_PATH = os.path.join(BASE_DIR, "..", "bm25_model.pkl")
PORT = 8000

OLLAMA_GENERATE_API = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2:1b"
MAX_THREADS = 2
CHUNK_SIZE = 800
IGNORE_LIST = [".obsidian", ".git", ".trash", "node_modules"]
