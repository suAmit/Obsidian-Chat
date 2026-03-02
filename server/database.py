import chromadb
from chromadb.utils import embedding_functions

from .config import DB_PATH


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.model = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name="obsidian_notes",
            embedding_function=self.model,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_notes(self, chunks):
        if not chunks:
            return
        self.collection.upsert(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )

    def cleanup_deleted(self, valid_file_ids):
        all_data = self.collection.get()
        if not all_data["ids"]:
            return 0
        to_del = [
            all_data["ids"][i]
            for i, m in enumerate(all_data["metadatas"])
            if m["file_id"] not in valid_file_ids
        ]
        if to_del:
            self.collection.delete(ids=to_del)
        return len(to_del)

    def query(self, text, n=5):
        return self.collection.query(
            query_texts=[text],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

    def get_all(self):
        return self.collection.get(include=["documents", "metadatas"])
