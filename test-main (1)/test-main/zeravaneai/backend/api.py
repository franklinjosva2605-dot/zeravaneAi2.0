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

# Support both GEMINI_API_KEY and GOOGLE_API_KEY in .env
if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.engine import ZeravaneEngine

# ── App ─────────────────────────────────────────────────────────────[...]
app = FastAPI(
    title="ZeravaneAI API",
    description="Programmatic access to ZeravaneAI — ScraperAPI web intelligence + Gemini 2.5 Flash RAG pipeline.",
    version="2.1.0",
)

# ── CORS Configuration (Security: Restrict to specific domains) ──────────────
# Replace these with your actual Streamlit domain and development URLs
ALLOWED_ORIGINS = [
    "http://localhost:3000",              # Local development
    "http://localhost:8501",              # Streamlit local
    "https://localhost:8501",             # Streamlit local (HTTPS)
    "http://127.0.0.1:8501",              # Streamlit local (loopback)
    "https://fbwscyhen7qrebxr7yjncc.streamlit.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
    max_age=3600,
)

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
    scraper_enabled: bool


class ScrapeRequest(BaseModel):
    url: str


class ScrapeResponse(BaseModel):
    scrape_method: str
    context_preview: str
    chunks_indexed: int


class HealthResponse(BaseModel):
    status: str
    scraper_enabled: bool
    cached_url: Optional[str]
    model: str


# ── Routes ────────────────────────────────────────────────────────────[...]

@app.get("/", tags=["Health"])
def root():
    return {
        "app": "ZeravaneAI",
        "version": "2.1.0",
        "status": "running",
        "description": "ScraperAPI × Gemini 2.5 Flash RAG Agent",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health():
    engine = get_engine()
    return HealthResponse(
        status="healthy",
        scraper_enabled=engine.scraper_enabled,
        cached_url=engine._cached_url,
        model=engine.model_name,
    )


@app.post("/scrape", response_model=ScrapeResponse, tags=["Scraping"])
def scrape_endpoint(request: ScrapeRequest):
    """
    Scrape a URL via ScraperAPI and index it into ChromaDB.
    Use this to pre-warm the cache before sending /query requests.
    """
    if not request.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    engine = get_engine()
    raw_text, scrape_method = engine.scrape_live_url(request.url)

    error_prefixes = ("Error:", "ScraperAPI_Error:", "Fallback_Error:")
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

    engine._cached_url = request.url
    context_preview = engine.query_vector_context(
        collection_name=engine._cached_collection,
        query="summary",
        n_results=1,
    )

    return ScrapeResponse(
        scrape_method=scrape_method,
        context_preview=context_preview[:500],
        chunks_indexed=len(chunks),
    )


@app.post("/query", response_model=QueryResponse, tags=["Query"])
def query_endpoint(request: QueryRequest):
    """
    Execute the full RAG pipeline: scrape (if needed) → vector search → LLM inference.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    engine = get_engine()
    response_text, context_payload, scrape_method, model_used = engine.execute_live_agent_query(
        user_query=request.query,
        target_url=request.target_url,
        force_rescrape=request.force_rescrape or False,
    )

    return QueryResponse(
        answer=response_text,
        context_payload=context_payload,
        scrape_method=scrape_method,
        scraper_enabled=engine.scraper_enabled,
    )
