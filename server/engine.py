import os
import pickle
import re

import requests
from rank_bm25 import BM25Okapi

from .config import BM25_MODEL_PATH, DEFAULT_MODEL, MAX_THREADS, OLLAMA_GENERATE_API
from .database import VectorStore


class InferenceEngine:
    def __init__(self):
        self.db = VectorStore()
        self.bm25, self.corpus, self.metadata = None, [], []
        self.refresh_indices()

    def refresh_indices(self, force=False):
        if not force and os.path.exists(BM25_MODEL_PATH):
            try:
                with open(BM25_MODEL_PATH, "rb") as f:
                    data = pickle.load(f)
                    self.bm25, self.corpus, self.metadata = (
                        data["m"],
                        data["c"],
                        data["me"],
                    )
                    return
            except:
                pass
        data = self.db.get_all()
        if data and data["documents"]:
            self.corpus, self.metadata = data["documents"], data["metadatas"]
            self.bm25 = BM25Okapi([d.lower().split() for d in self.corpus])
            with open(BM25_MODEL_PATH, "wb") as f:
                pickle.dump({"m": self.bm25, "c": self.corpus, "me": self.metadata}, f)

    def query_hybrid(self, query: str, top_k: int = 5):
        # 1. Vector Search (Semantic)
        vec_res = self.db.query(query, n=top_k * 2)

        # 2. Keyword Search (BM25)
        kw_indices = (
            self.bm25.get_top_n(
                query.lower().split(), list(range(len(self.corpus))), n=top_k * 2
            )
            if self.bm25
            else []
        )

        # 3. Reciprocal Rank Fusion (RRF) with Folder Boosting
        scores, k_constant = {}, 60

        # Process Vector Results
        for r, (doc, meta) in enumerate(
            zip(vec_res["documents"][0], vec_res["metadatas"][0])
        ):
            pid = meta["path"]
            if pid not in scores:
                scores[pid] = {"s": 0, "t": doc, "m": meta}
            scores[pid]["s"] += 1.0 / (k_constant + r)

        # Process Keyword Results
        for r, idx in enumerate(kw_indices):
            pid = self.metadata[idx]["path"]
            if pid not in scores:
                scores[pid] = {"s": 0, "t": self.corpus[idx], "m": self.metadata[idx]}
            scores[pid]["s"] += 1.0 / (k_constant + r)

        # Sort and return
        sorted_results = sorted(scores.values(), key=lambda x: x["s"], reverse=True)
        return [
            {"text": i["t"], "path": i["m"]["path"]} for i in sorted_results[:top_k]
        ]

    def query_rag(self, config):
        query = config.get("query")
        model_name = config.get("model") or DEFAULT_MODEL

        # STEP 1: Multi-Query Expansion (Optional but powerful for your new CPU)
        # We can find more relevant docs by asking the AI for synonyms
        search_queries = [query]
        try:
            # Simple prompt to get 2 variations
            expansion_prompt = f"Provide 2 short search variations for this query: '{query}'. Output only the variations, one per line."
            r_exp = requests.post(
                OLLAMA_GENERATE_API,
                json={
                    "model": model_name,
                    "prompt": expansion_prompt,
                    "stream": False,
                    "options": {"num_predict": 50, "temperature": 0.4},
                },
                timeout=10,
            )
            if r_exp.status_code == 200:
                variations = r_exp.json().get("response", "").strip().split("\n")
                search_queries.extend([v.strip() for v in variations if v.strip()])
        except:
            pass  # Fallback to single query if expansion fails

        # STEP 2: Gather context from all query variations
        all_docs = []
        seen_paths = set()
        for q in search_queries:
            results = self.query_hybrid(q, top_k=config.get("top_k", 3))
            for res in results:
                if res["path"] not in seen_paths:
                    all_docs.append(res)
                    seen_paths.add(res["path"])

        # STEP 3: Format the context with the new headers from processor.py
        context_text = "\n\n".join(
            [f"--- SOURCE {i+1} ---\n{d['text']}" for i, d in enumerate(all_docs[:6])]
        )

        # STEP 4: Final RAG call
        system_prompt = (
            "Use the provided documents to answer the question concisely.\n"
            "If the documents don't contain the answer, say you don't know.\n\n"
            f"RELEVANT NOTES:\n{context_text}\n\n"
            f"USER QUESTION: {query}\n"
            "EXPERT ANSWER:"
        )

        payload = {
            "model": model_name,
            "prompt": system_prompt,
            "stream": False,
            "options": {
                "num_ctx": config.get("num_ctx", 4096),
                "temperature": config.get("temperature", 0.2),
                "num_thread": 4,  # Leveraging your new CPU
            },
        }

        try:
            r = requests.post(OLLAMA_GENERATE_API, json=payload, timeout=120)
            return {"response": r.json()["response"], "context": all_docs[:6]}
        except Exception as e:
            return {"error": str(e)}

    def get_auto_links(self, content: str, k: int = 3):
        # Semantic linking using the vector DB
        results = self.db.query(content, n=k)
        suggestions = []
        if results and results["metadatas"]:
            for meta in results["metadatas"][0]:
                title = meta.get("title")
                if title:
                    suggestions.append(f"[[{title}]]")
        return list(set(suggestions))
