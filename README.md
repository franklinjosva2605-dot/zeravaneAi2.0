# ⚡ ZeravaneAI

**Turn any website into structured intelligence — instantly.**

ZeravaneAI is an intelligent web research platform that scrapes any public URL, indexes the content into a vector database, and answers questions about it using a RAG (Retrieval-Augmented Generation) pipeline backed by Gemini 2.5 Flash.

---

## What It Does

Most AI assistants are stuck with knowledge cutoffs. ZeravaneAI isn't.

Point it at any URL — documentation, a competitor's website, a GitHub repo, any public page — and ask questions in plain English. ZeravaneAI scrapes it live, understands it, and gives you precise answers grounded in that exact content.

**Core capabilities:**
- **Web Research Agent** — Ask questions about any live URL
- **Multi-URL Research** — Scrape multiple sources and query across all of them
- **GitHub Intelligence** — Analyze any public repository instantly
- **Tech Stack Detection** — Identify what any website is built with
- **Code Generation from Docs** — Generate production code from live documentation

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│         Scraping Layer          │
│  Tier 1: ScraperAPI (JS + proxy)│
│  Tier 2: Residential Proxy      │
│  Tier 3: Direct HTTP            │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│          RAG Pipeline           │
│  Chunking → ChromaDB → Retrieval│
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│          LLM Layer              │
│  Tier 1: Gemini 2.5 Flash       │
│  Tier 2: Groq (llama-3.3-70b)   │
│  Tier 3: AI/ML API (gpt-4o-mini)│
└─────────────────────────────────┘
```

**Why triple fallback?** Zero downtime. If any tier fails — API quota, rate limit, network issue — the next tier activates automatically. The system never goes down for the user.

---

## Quickstart

**1. Clone and install**
```bash
git clone https://github.com/yourusername/zeravaneai
cd zeravaneai
pip install -r requirements.txt
```

**2. Configure environment**
```bash
cp .env.example .env
# Add your GEMINI_API_KEY and SCRAPER_API_KEY
```

**3. Run**
```bash
streamlit run frontend/app.py
```

---

## API Keys Needed

| Key | Required | Free Tier | Get It |
|-----|----------|-----------|--------|
| `GEMINI_API_KEY` | ✅ Yes | Yes (generous) | [aistudio.google.com](https://aistudio.google.com) |
| `SCRAPER_API_KEY` | Recommended | 1,000 calls/month | [scraperapi.com](https://scraperapi.com) |
| `GROQ_API_KEY` | Optional | Yes | [console.groq.com](https://console.groq.com) |
| `AIML_API_KEY` | Optional | Yes | [aimlapi.com](https://aimlapi.com) |

The platform runs in demo mode (direct HTTP scraping) without ScraperAPI. Add the key for full JS rendering and proxy rotation.

---

## Tech Stack

- **Frontend:** Streamlit
- **Scraping:** ScraperAPI + BeautifulSoup
- **Vector DB:** ChromaDB (persistent)
- **Embeddings:** ChromaDB default (all-MiniLM-L6-v2)
- **LLMs:** Google Gemini 2.5 Flash, Groq, AI/ML API
- **API:** FastAPI (run `uvicorn backend.api:app`)
- **Deployment:** Streamlit Cloud / any VPS

---

## REST API

```bash
uvicorn backend.api:app --reload
```

```
GET  /health          — System status
POST /scrape          — Scrape and index a URL
POST /query           — Query the RAG pipeline
```

---

## Built By

**Franklin Josva A** — [github.com/franklinjosva2605-dot](https://github.com/franklinjosva2605-dot) | [fiverr.com/franklinjosva](https://fiverr.com/franklinjosva)

Team **Singleton Vanguard**

---

*ZeravaneAI v2.0.0*
