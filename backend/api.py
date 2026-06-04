"""
ZeravaneAI — FastAPI REST API
Provides programmatic access to the ZeravaneEngine scraping + RAG pipeline.

Run with:
    uvicorn backend.api:app --reload
"""

import os
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Normalise key name — support both GEMINI_API_KEY and GOOGLE_API_KEY in .env
if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.engine import ZeravaneEngine

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ZeravaneAI API",
    description=(
        "Programmatic access to ZeravaneAI — Bright Data web intelligence "
        "+ Gemini 2.5 Flash RAG pipeline."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton engine instance
_engine: ZeravaneEngine = None

def get_engine() -> ZeravaneEngine:
    global _engine
    if _engine is None:
        _engine = ZeravaneEngine()
    return _engine


# ── Request / Response models ──────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    target_url: Optional[str] = None
    force_rescrape: Optional[bool] = False

class QueryResponse(BaseModel):
    answer: str
    context_payload: str
    scrape_method: str
    bd_enabled: bool

class ScrapeRequest(BaseModel):
    url: str

class ScrapeResponse(BaseModel):
    scrape_method: str
    context_preview: str   # first 500 chars of indexed context
    chunks_indexed: int

class HealthResponse(BaseModel):
    status: str
    bd_enabled: bool
    cached_url: Optional[str]
    model: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "app": "ZeravaneAI",
        "version": "2.0.0",
        "status": "running",
        "description": "Bright Data × Gemini 2.5 Flash RAG Agent",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health():
    engine = get_engine()
    return HealthResponse(
        status="healthy",
        bd_enabled=engine.bd_enabled,
        cached_url=engine._cached_url,
        model=engine.model_name,
    )


@app.post("/scrape", response_model=ScrapeResponse, tags=["Scraping"])
def scrape_endpoint(request: ScrapeRequest):
    """
    Scrape a URL via the 3-tier Bright Data pipeline and index it into ChromaDB.
    Use this to pre-warm the cache before sending /query requests.
    """
    if not request.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    engine = get_engine()
    raw_text, scrape_method = engine.scrape_live_url(request.url)

    error_prefixes = ("Error:", "BrightData_Error:", "Fallback_Error:", "SERP_Error:")
    scrape_ok = (
        raw_text
        and len(raw_text) >= engine.MIN_TEXT_LENGTH
        and not any(raw_text.startswith(p) for p in error_prefixes)
    )

    if not scrape_ok:
        raise HTTPException(
            status_code=502,
            detail=f"Scraping failed: {raw_text[:300]}",
        )

    chunks = engine.chunk_text(raw_text)
    indexed = engine.refresh_vector_index(
        collection_name=engine._cached_collection,
        text_chunks=chunks,
    )
    if not indexed:
        raise HTTPException(status_code=500, detail="Failed to build vector index")

    engine
