import os
from typing import List, Optional

import uvicorn
from fastapi import BackgroundTasks, Body, FastAPI
from pydantic import BaseModel

from server.config import VAULT_PATH, PORT
from server.engine import InferenceEngine

app = FastAPI(title="Second Brain Core")
engine = InferenceEngine()
SYNC_STATUS = {"running": False, "last_error": None}


# --- Request Models ---
class RAGRequest(BaseModel):
    query: str
    model: Optional[str] = None
    top_k: int = 3
    temperature: float = 0.2
    num_ctx: int = 2048


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class AutoLinkRequest(BaseModel):
    content: str


# --- Background Sync ---
def run_sync_logic():
    global SYNC_STATUS
    SYNC_STATUS["running"] = True
    try:
        try:
            os.nice(15)
        except:
            pass
        from server.database import VectorStore
        from server.processor import NoteProcessor

        proc, db = NoteProcessor(), VectorStore()
        chunks, v_ids = proc.process_vault(VAULT_PATH)
        if chunks:
            db.upsert_notes(chunks)
        db.cleanup_deleted(v_ids)
        engine.refresh_indices(force=True)
        SYNC_STATUS["last_error"] = None
    except Exception as e:
        SYNC_STATUS["last_error"] = str(e)
    finally:
        SYNC_STATUS["running"] = False


# --- Endpoints ---
@app.get("/sync/status")
async def get_status():
    return SYNC_STATUS


@app.post("/sync")
async def sync(bt: BackgroundTasks):
    bt.add_task(run_sync_logic)
    return {"message": "Sync started"}


@app.post("/chat")
async def chat(req: RAGRequest):
    return engine.query_rag(req.model_dump())  # Updated for Pydantic V2


@app.post("/search/hybrid")
async def hybrid(req: SearchRequest):
    return engine.query_hybrid(req.query, top_k=req.top_k)


@app.post("/auto-link")
async def auto_link(req: AutoLinkRequest):
    return {"links": engine.get_auto_links(req.content)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
