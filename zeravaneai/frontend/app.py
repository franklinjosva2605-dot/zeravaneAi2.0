# =============================================================================
# PLATFORM PATCHES — run before everything else
# =============================================================================
import os, sys
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import re
import requests
import streamlit as st
from bs4 import BeautifulSoup

try:
    import chromadb
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

# =============================================================================
# ENGINE
# =============================================================================

class ZeravaneEngine:
    SCRAPER_API_BASE = "http://api.scraperapi.com"
    MIN_TEXT_LENGTH = 100

    def __init__(self):
        # ── Gemini API key ──
        api_key = (
            st.secrets.get("GEMINI_API_KEY")
            or st.secrets.get("GOOGLE_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not api_key:
            raise ValueError(
                "Gemini API key not found. "
                "Add GEMINI_API_KEY to Streamlit Cloud secrets."
            )

        if GENAI_AVAILABLE:
            self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"

        # ── ChromaDB (in-memory on Cloud) ──
        if CHROMA_AVAILABLE:
            try:
                self.chroma_client = chromadb.EphemeralClient()
            except Exception:
                self.chroma_client = None
        else:
            self.chroma_client = None

        # ── ScraperAPI ──
        self.scraper_api_key = (
            st.secrets.get("SCRAPER_API_KEY")
            or os.environ.get("SCRAPER_API_KEY", "")
        )
        self.scraper_enabled = bool(self.scraper_api_key)

        # ── Groq + AIML fallbacks ──
        self.groq_api_key = (
            st.secrets.get("GROQ_API_KEY")
            or os.environ.get("GROQ_API_KEY", "")
        )
        self.aiml_api_key = (
            st.secrets.get("AIML_API_KEY")
            or os.environ.get("AIML_API_KEY", "")
        )
        self.groq_enabled = bool(self.groq_api_key)
        self.aiml_enabled = bool(self.aiml_api_key)

        self._cached_url = None
        self._cached_collection = "zeravane_cache"

    # ── Scraping ──────────────────────────────────────────────────────────────

    def _parse_html(self, raw_bytes: bytes) -> str:
        soup = BeautifulSoup(raw_bytes.decode("utf-8", errors="ignore"), "html.parser")
        for el in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            el.extract()
        return re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()

    def scrape_with_scraper_api(self, url: str) -> str:
        try:
            resp = requests.get(
                self.SCRAPER_API_BASE,
                params={"api_key": self.scraper_api_key, "url": url, "render": "true"},
                timeout=60, stream=True,
            )
            content = b""
            for chunk in resp.iter_content(8192):
                content += chunk
                if len(content) > 2 * 1024 * 1024:
                    break
            if resp.status_code == 200:
                return self._parse_html(content)
            return f"Error: ScraperAPI returned {resp.status_code}"
        except Exception as e:
            return f"ScraperAPI_Error: {e}"

    def scrape_fallback(self, url: str) -> str:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=15, stream=True)
            content = b""
            for chunk in resp.iter_content(8192):
                content += chunk
                if len(content) > 2 * 1024 * 1024:
                    break
            if resp.status_code != 200:
                return f"Error: status {resp.status_code}"
            return self._parse_html(content)
        except Exception as e:
            return f"Fallback_Error: {e}"

    def scrape_live_url(self, url: str) -> tuple:
        _err = ("Error:", "ScraperAPI_Error:", "Fallback_Error:")
        if self.scraper_enabled:
            result = self.scrape_with_scraper_api(url)
            if result and not any(result.startswith(p) for p in _err):
                return result, "🟢 ScraperAPI (Bot-Proof)"
        result = self.scrape_fallback(url)
        return result, "⚪ Standard Requests"

    # ── RAG ───────────────────────────────────────────────────────────────────

    def chunk_text(self, text: str, max_chars: int = 3000, overlap: int = 300) -> list:
        if len(text) <= max_chars:
            return [text]
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start: start + max_chars])
            start += max_chars - overlap
        return chunks

    def refresh_vector_index(self, collection_name: str, text_chunks: list) -> bool:
        if not self.chroma_client:
            return False
        try:
            try:
                self.chroma_client.delete_collection(name=collection_name)
            except Exception:
                pass
            col = self.chroma_client.create_collection(name=collection_name)
            col.add(
                documents=text_chunks,
                ids=[f"chunk_{i}" for i in range(len(text_chunks))],
                metadatas=[{"index": i} for i in range(len(text_chunks))],
            )
            return True
        except Exception as e:
            print(f"[Engine] Vector index error: {e}")
            return False

    def query_vector_context(self, collection_name: str, query: str, n_results: int = 3) -> str:
        if not self.chroma_client:
            return ""
        try:
            col = self.chroma_client.get_collection(name=collection_name)
            available = col.count()
            if available == 0:
                return ""
            results = col.query(query_texts=[query], n_results=min(n_results, available))
            docs = []
            for sublist in results.get("documents", []):
                docs.extend(sublist)
            return "\n\n".join(docs)
        except Exception as e:
            print(f"[Engine] Vector query error: {e}")
            return ""

    # ── LLM Inference ─────────────────────────────────────────────────────────

    def _infer(self, system_instruction: str, prompt: str) -> tuple:
        # Tier 1 — Gemini
        if GENAI_AVAILABLE:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                    ),
                )
                return response.text, "⚡ Gemini 2.5 Flash"
            except Exception as e:
                gemini_err = str(e)
        else:
            gemini_err = "google-genai not available"

        # Tier 2 — Groq
        if self.groq_enabled:
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.3-70b-versatile",
                          "messages": [{"role": "system", "content": system_instruction},
                                       {"role": "user", "content": prompt}],
                          "temperature": 0.2},
                    timeout=30,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"], "🟣 Groq (llama-3.3-70b)"
            except Exception:
                pass

        # Tier 3 — AI/ML API
        if self.aiml_enabled:
            try:
                resp = requests.post(
                    "https://api.aimlapi.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.aiml_api_key}", "Content-Type": "application/json"},
                    json={"model": "gpt-4o-mini",
                          "messages": [{"role": "system", "content": system_instruction},
                                       {"role": "user", "content": prompt}],
                          "temperature": 0.2},
                    timeout=30,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"], "🔶 AI/ML API (gpt-4o-mini)"
            except Exception:
                pass

        return f"All providers failed: {gemini_err}", "❌ All Failed"

    # ── Capabilities ──────────────────────────────────────────────────────────

    def scrape_multiple_urls(self, urls: list) -> tuple:
        merged_chunks, summary = [], []
        _err = ("Error:", "ScraperAPI_Error:", "Fallback_Error:")
        collection_id = "zeravane_multi_url"
        for url in urls:
            url = url.strip()
            if not url:
                continue
            raw, method = self.scrape_live_url(url)
            ok = raw and len(raw) >= self.MIN_TEXT_LENGTH and not any(raw.startswith(p) for p in _err)
            if ok:
                merged_chunks.extend(self.chunk_text(f"[SOURCE: {url}]\n{raw}"))
                summary.append(f"✅ {url} — {method}")
            else:
                summary.append(f"❌ {url} — Failed: {raw[:80]}")
        if merged_chunks:
            self.refresh_vector_index(collection_id, merged_chunks)
            self._cached_url = "__multi__"
            self._cached_collection = collection_id
        return merged_chunks, "\n".join(summary)

    def analyze_github_repo(self, github_url: str) -> tuple:
        try:
            match = re.search(r"github\.com/([^/]+)/([^/?\s#]+)", github_url)
            if not match:
                return "Invalid GitHub URL format.", {}
            owner, repo = match.group(1), match.group(2).rstrip("/")
            api_base = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "ZeravaneAI"}
            meta = requests.get(api_base, headers=headers, timeout=15).json()
            metadata = {
                "name": meta.get("full_name", ""),
                "description": meta.get("description", "No description"),
                "language": meta.get("language", "Unknown"),
                "stars": meta.get("stargazers_count", 0),
                "forks": meta.get("forks_count", 0),
                "topics": meta.get("topics", []),
                "default_branch": meta.get("default_branch", "main"),
            }
            branch = metadata["default_branch"]
            readme = requests.get(f"{api_base}/readme",
                                   headers={**headers, "Accept": "application/vnd.github.v3.raw"},
                                   timeout=15)
            readme_text = readme.text[:8000] if readme.status_code == 200 else ""
            tree = requests.get(f"{api_base}/git/trees/{branch}?recursive=0", headers=headers, timeout=15)
            files = [i["path"] for i in tree.json().get("tree", []) if i["type"] == "blob"][:50] if tree.status_code == 200 else []
            combined = (
                f"=== GITHUB REPO: {owner}/{repo} ===\n"
                f"Description: {metadata['description']}\n"
                f"Language: {metadata['language']} | Stars: {metadata['stars']} | Forks: {metadata['forks']}\n"
                f"Topics: {', '.join(metadata['topics'])}\n\n"
                f"=== README ===\n{readme_text}\n\n"
                f"=== FILE TREE ===\n{chr(10).join(files)}\n"
            )
            collection_id = "zeravane_github"
            self.refresh_vector_index(collection_id, self.chunk_text(combined))
            self._cached_url = github_url
            self._cached_collection = collection_id
            return combined, metadata
        except Exception as e:
            return f"GitHub_Error: {e}", {}

    def detect_tech_stack(self, content: str, url: str = "") -> str:
        if not content or len(content) < 50:
            return "Insufficient content to detect tech stack."
        sys_inst = ("You are a tech stack detection engine. Analyze the web content and identify the technology stack. "
                    "Structure as: Frontend | Backend | Database | Deployment | Language | Styling | Other Tools. "
                    "Rate confidence (High/Medium/Low). Only list what you can confidently infer.")
        prompt = f"Target URL: {url}\n\n=== CONTENT (first 4000 chars) ===\n{content[:4000]}\n\nDetect the tech stack."
        result, _ = self._infer(sys_inst, prompt)
        return result

    def generate_code_from_docs(self, docs_url: str, request: str, language: str = "Python") -> tuple:
        _err = ("Error:", "ScraperAPI_Error:", "Fallback_Error:")
        raw, scrape_method = self.scrape_live_url(docs_url)
        scrape_ok = raw and len(raw) >= self.MIN_TEXT_LENGTH and not any(raw.startswith(p) for p in _err)
        if scrape_ok:
            collection_id = "zeravane_codegen"
            self.refresh_vector_index(collection_id, self.chunk_text(raw))
            context = self.query_vector_context(collection_id, request, n_results=4)
        else:
            context = f"[Scraping failed: {raw[:100]}]"
        sys_inst = (f"You are a code generation engine. Generate production-ready {language} code from the docs. "
                    "Include error handling, comments, and a usage example. Return ONLY clean runnable code.")
        prompt = f"Docs: {docs_url}\nLanguage: {language}\nRequest: {request}\n\n=== DOCS CONTEXT ===\n{context}\n\nGenerate code now."
        code, model_used = self._infer(sys_inst, prompt)
        return code, scrape_method, model_used

    def execute_live_agent_query(self, user_query: str, target_url: str = None, force_rescrape: bool = False) -> tuple:
        context_payload = ""
        collection_id = self._cached_collection
        scrape_method = "N/A"
        _err = ("Error:", "ScraperAPI_Error:", "Fallback_Error:")

        if target_url:
            if target_url != self._cached_url or force_rescrape:
                raw, scrape_method = self.scrape_live_url(target_url)
                scrape_ok = raw and len(raw) >= self.MIN_TEXT_LENGTH and not any(raw.startswith(p) for p in _err)
                if scrape_ok:
                    if self.refresh_vector_index(collection_id, self.chunk_text(raw)):
                        self._cached_url = target_url
                        context_payload = self.query_vector_context(collection_id, user_query)
                    else:
                        context_payload = "[Indexing Error]"
                else:
                    context_payload = f"[Scraping Warning: {raw}]"
            else:
                scrape_method = "✅ Cache Hit"
                context_payload = self.query_vector_context(collection_id, user_query)

        web_ok = target_url and context_payload and not context_payload.startswith("[")

        if web_ok:
            sys_inst = ("You are ZeravaneAI, a real-time web-aware developer agent. "
                        "Use the live documentation context provided to answer precisely. "
                        "Cite when drawing from the docs. Provide production-ready code.")
        elif target_url:
            sys_inst = (f"You are ZeravaneAI. The user provided: {target_url}. "
                        "Scraping failed — answer from training knowledge about this URL/library/framework. "
                        "Be transparent about the data source.")
        else:
            sys_inst = ("You are ZeravaneAI, a premium programming assistant. "
                        "Provide expert-level solutions with best practices and clean code.")

        prompt = (
            f"ScraperAPI: {'Active' if self.scraper_enabled else 'Demo Mode'} | "
            f"Scrape: {scrape_method} | URL: {target_url or 'None'} | Context: {'Yes' if web_ok else 'No'}\n\n"
            f"--- LIVE WEB CONTEXT ---\n{context_payload or '[No context — using training knowledge]'}\n\n"
            f"--- QUERY ---\n{user_query}"
        )
        response_text, model_used = self._infer(sys_inst, prompt)
        return response_text, context_payload, scrape_method, model_used


# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(page_title="ZeravaneAI", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    :root { --neon-cyan:#00D9FF; --neon-green:#00FF41; --neon-orange:#FF6B35; --neon-purple:#A855F7; }
    .main { background-color: #0F1419; color: #E0E6FF; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stButton>button {
        border: 1.5px solid var(--neon-cyan) !important;
        background-color: rgba(0,20,40,0.8) !important;
        color: #E0E6FF !important; border-radius: 8px !important;
        box-shadow: 0 0 8px rgba(0,217,255,0.3) !important;
    }
    .stButton>button:hover { transform:scale(1.02)!important; box-shadow:0 0 20px rgba(0,217,255,0.7)!important; }
    @keyframes pulse-green { 0%,100%{box-shadow:0 0 8px rgba(0,255,65,.4)} 50%{box-shadow:0 0 20px rgba(0,255,65,.8)} }
    @keyframes pulse-cyan  { 0%,100%{box-shadow:0 0 8px rgba(0,217,255,.4)} 50%{box-shadow:0 0 20px rgba(0,217,255,.8)} }
    @keyframes pulse-orange{ 0%,100%{box-shadow:0 0 8px rgba(255,107,53,.4)} 50%{box-shadow:0 0 20px rgba(255,107,53,.8)} }
    @keyframes pulse-purple{ 0%,100%{box-shadow:0 0 8px rgba(168,85,247,.4)} 50%{box-shadow:0 0 20px rgba(168,85,247,.8)} }
    .badge-green  { display:inline-block;padding:8px 16px;border-radius:6px;border:1.5px solid rgba(0,255,65,.6);background:rgba(0,50,30,.7);color:#00FF41;font-weight:600;font-size:14px;animation:pulse-green 2s ease-in-out infinite;margin:8px 0; }
    .badge-cyan   { display:inline-block;padding:8px 16px;border-radius:6px;border:1.5px solid rgba(0,217,255,.6);background:rgba(0,30,60,.7);color:#00D9FF;font-weight:600;font-size:14px;animation:pulse-cyan 2s ease-in-out infinite;margin:8px 0; }
    .badge-orange { display:inline-block;padding:8px 16px;border-radius:6px;border:1.5px solid rgba(255,107,53,.6);background:rgba(60,20,0,.7);color:#FF6B35;font-weight:600;font-size:14px;animation:pulse-orange 2s ease-in-out infinite;margin:8px 0; }
    .badge-purple { display:inline-block;padding:6px 14px;border-radius:6px;border:1.5px solid rgba(168,85,247,.6);background:rgba(40,0,60,.7);color:#A855F7;font-weight:600;font-size:12px;animation:pulse-purple 2s ease-in-out infinite;margin:4px; }
    .banner { background:linear-gradient(135deg,rgba(0,20,50,.9),rgba(0,40,80,.9));border:1px solid rgba(0,217,255,.3);border-radius:10px;padding:12px 20px;margin:10px 0;text-align:center; }
    .cache-banner { background:rgba(0,40,20,.6);border:1px solid rgba(0,255,65,.3);border-radius:8px;padding:8px 16px;margin:6px 0;font-size:13px;color:#00FF41; }
    .model-tag { display:inline-block;padding:3px 10px;border-radius:4px;background:rgba(168,85,247,.15);border:1px solid rgba(168,85,247,.4);color:#A855F7;font-size:11px;font-weight:600;margin-left:8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style='text-align:center;color:#00D9FF;text-shadow:0 0 16px rgba(0,217,255,.6);letter-spacing:2px;margin-bottom:2px;'>
⚡ ZeravaneAI — Web Intelligence Engine
</h1>
<p style='text-align:center;color:#00D9FF;font-size:11px;letter-spacing:2px;opacity:.7;margin-top:0;'>
POWERED BY SCRAPERAPI × GEMINI 2.5 FLASH × GROQ × AI/ML API
</p>
""", unsafe_allow_html=True)

# =============================================================================
# ENGINE INIT (cached)
# =============================================================================
@st.cache_resource
def get_engine():
    try:
        return ZeravaneEngine(), None
    except Exception as e:
        return None, str(e)

engine, init_error = get_engine()

if init_error:
    st.error(f"⚠️ Engine failed to start: {init_error}")
    st.info("Make sure **GEMINI_API_KEY** is set in your Streamlit Cloud secrets (Settings → Secrets).")
    st.stop()

# Banner
st.markdown(f"""
<div class='banner'>
    <span style='color:#00D9FF;font-weight:700;letter-spacing:1px;'>🌐 SCRAPERAPI INTEGRATION {'ACTIVE' if engine.scraper_enabled else 'DEMO MODE'}</span>
    <span style='color:#aaa;font-size:12px;margin-left:12px;'>JS Rendering · Rotating Proxies · Bot-Proof · Geo-Unblocked</span><br>
    <span class='badge-purple'>⚡ Gemini 2.5 Flash</span>
    <span class='badge-purple'>🟣 Groq llama-3.3-70b</span>
    <span class='badge-purple'>🔶 AI/ML API gpt-4o-mini</span>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# Session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_url" not in st.session_state:
    st.session_state.last_url = ""

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Agent Config")
    st.markdown(f"""
    <div style='background:rgba(0,20,40,.6);border:1px solid rgba(0,217,255,.2);border-radius:8px;padding:12px;font-size:12px;color:#aaa;'>
    <b style='color:#00D9FF;'>Scraping Stack</b><br>
    • ScraperAPI Tier 1 (JS + Proxy)<br>
    • Standard Requests Tier 2 (Fallback)<br><br>
    <b style='color:#A855F7;'>LLM Stack (3-Tier)</b><br>
    • Gemini 2.5 Flash (Primary)<br>
    • Groq llama-3.3-70b (Fallback)<br>
    • AI/ML API gpt-4o-mini (Last Resort)<br><br>
    <b style='color:#00D9FF;'>Vector Engine</b><br>
    • ChromaDB Ephemeral · 3000 chars / 300 overlap
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.write(f"**ScraperAPI:** {'🟢 Active' if engine.scraper_enabled else '🟡 Demo Mode'}")
    st.write(f"**Groq:** {'🟢 Active' if engine.groq_enabled else '⚪ Not configured'}")
    st.write(f"**AI/ML API:** {'🟢 Active' if engine.aiml_enabled else '⚪ Not configured'}")
    if engine._cached_url:
        st.markdown(f"<div class='cache-banner'>✅ Cached: <code style='font-size:11px;'>{engine._cached_url[:45]}...</code></div>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Cache", use_container_width=True):
        if engine.chroma_client:
            try:
                engine.chroma_client.delete_collection(engine._cached_collection)
            except Exception:
                pass
        engine._cached_url = None
        st.session_state.last_url = ""
        st.session_state.chat_history = []
        st.rerun()

# =============================================================================
# TABS
# =============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌐 Live Agent Query", "🔗 Multi-URL Scraper",
    "🐙 GitHub Analyzer", "🔍 Tech Stack Detector", "⚙️ Code Generator"
])

# ── TAB 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🌐 Ingestion Target")
        target_url = st.text_input("Target URL", placeholder="https://docs.github.com/en/rest",
                                   value=st.session_state.last_url, key="tab1_url")
    with col2:
        st.subheader("🔧 System Context")
        url_changed = target_url.strip() != st.session_state.last_url.strip()
        if url_changed and target_url.strip():
            st.info("🔄 New URL — will scrape fresh on next query.")
        elif engine._cached_url and not url_changed:
            st.success("✅ URL cached — skipping re-scrape.")
        else:
            st.caption("ZeravaneAI uses ScraperAPI to access any public URL including JS-heavy pages.")

    st.markdown("#### 📊 Agent Status")
    c1, c2 = st.columns([2, 1])
    with c1:
        if not target_url or not target_url.strip():
            st.markdown("<div class='badge-cyan'>🔵 [Standby] Enter URL to activate Web Intelligence</div>", unsafe_allow_html=True)
        elif engine.scraper_enabled:
            st.markdown("<div class='badge-green'>🟢 [Active] ScraperAPI Online — Bot-Proof Scraping Ready</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='badge-orange'>🟡 [Demo Mode] Add SCRAPER_API_KEY for full power</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='{'badge-green' if engine.scraper_enabled else 'badge-cyan'}'>{'🛡️ Bot Detection: BYPASSED' if engine.scraper_enabled else 'ℹ️ Demo Mode'}</div>", unsafe_allow_html=True)

    user_query = st.text_area("💬 Developer question", placeholder="How does authentication work on this platform?", height=100, key="tab1_query")
    force_rescrape = st.checkbox("🔄 Force re-scrape", value=False, key="tab1_force")
    st.markdown("---")

    if st.button("🚀 Execute Agent Search", use_container_width=True, key="tab1_execute"):
        if not user_query.strip():
            st.error("Please enter a query.")
        else:
            url_to_use = target_url.strip() or None
            with st.spinner("🌐 Scraping + indexing + querying..." if url_to_use else "🧠 Processing on base model..."):
                response_text, context_payload, scrape_method, model_used = engine.execute_live_agent_query(
                    user_query, url_to_use, force_rescrape)
            if url_to_use:
                st.session_state.last_url = url_to_use
            st.session_state.chat_history.append({"query": user_query, "response": response_text,
                                                   "scrape_method": scrape_method, "model_used": model_used, "url": url_to_use})
            st.markdown("### 🤖 ZeravaneAI Response")
            if url_to_use:
                st.markdown(f"<small style='color:#555;'>Source: <b style='color:#00D9FF;'>{scrape_method}</b><span class='model-tag'>{model_used}</span></small>", unsafe_allow_html=True)
            st.markdown(response_text)
            with st.expander("🔍 Raw Vector Context"):
                st.text_area("Context injected into LLM:", value=context_payload or "[No context — base model]", disabled=True, height=180)

    if st.session_state.chat_history:
        st.markdown("---")
        with st.expander(f"📜 Session History ({len(st.session_state.chat_history)} queries)"):
            for i, e in enumerate(reversed(st.session_state.chat_history), 1):
                st.markdown(f"**Q{i}:** {e['query']}  \n<small style='color:#555;'>Source: {e['scrape_method']} | Model: {e['model_used']} | URL: {e['url'] or 'None'}</small>", unsafe_allow_html=True)
                st.markdown(e["response"][:400] + "..." if len(e["response"]) > 400 else e["response"])
                st.markdown("---")

# ── TAB 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("🔗 Multi-URL Scraper")
    st.caption("Scrape multiple URLs and merge into a unified RAG knowledge base.")
    multi_urls = st.text_area("URLs (one per line)", placeholder="https://docs.fastapi.tiangolo.com\nhttps://docs.pydantic.dev", height=150, key="multi_urls")
    multi_query = st.text_area("💬 Query across all sources", placeholder="Compare authentication approaches...", height=80, key="multi_query")
    if st.button("🚀 Scrape All + Query", use_container_width=True, key="multi_execute"):
        urls = [u.strip() for u in multi_urls.strip().splitlines() if u.strip()]
        if not urls:
            st.error("Enter at least one URL.")
        elif not multi_query.strip():
            st.error("Enter a query.")
        else:
            with st.spinner(f"🌐 Scraping {len(urls)} URLs..."):
                chunks, summary = engine.scrape_multiple_urls(urls)
            for line in summary.splitlines():
                st.success(line) if line.startswith("✅") else st.error(line)
            if chunks:
                with st.spinner("🧠 Querying unified knowledge base..."):
                    response_text, _, _, model_used = engine.execute_live_agent_query(multi_query)
                st.markdown("### 🤖 ZeravaneAI Response")
                st.markdown(f"<small style='color:#555;'>{len(urls)} URLs merged | <span class='model-tag'>{model_used}</span></small>", unsafe_allow_html=True)
                st.markdown(response_text)
            else:
                st.warning("No URLs scraped successfully.")

# ── TAB 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("🐙 GitHub Repo Analyzer")
    st.caption("Analyze any public GitHub repo — README, file tree, metadata.")
    gh_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/tiangolo/fastapi", key="github_url")
    gh_query = st.text_area("💬 Ask about this repo", placeholder="What does this project do? How do I get started?", height=80, key="github_query")
    if st.button("🚀 Analyze Repository", use_container_width=True, key="github_execute"):
        if not gh_url.strip():
            st.error("Enter a GitHub URL.")
        elif not gh_query.strip():
            st.error("Enter a question.")
        else:
            with st.spinner("🐙 Fetching repo data..."):
                repo_content, metadata = engine.analyze_github_repo(gh_url.strip())
            if metadata:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("⭐ Stars", f"{metadata.get('stars',0):,}")
                m2.metric("🍴 Forks", f"{metadata.get('forks',0):,}")
                m3.metric("💻 Language", metadata.get("language","N/A"))
                m4.metric("📦 Repo", metadata.get("name","N/A").split("/")[-1])
                if metadata.get("description"):
                    st.info(f"📝 {metadata['description']}")
                if metadata.get("topics"):
                    st.markdown(" ".join([f"<span class='badge-purple'>{t}</span>" for t in metadata["topics"][:8]]), unsafe_allow_html=True)
            if not repo_content.startswith(("GitHub_Error", "Invalid")):
                with st.spinner("🧠 Analyzing..."):
                    response_text, _, _, model_used = engine.execute_live_agent_query(gh_query)
                st.markdown("### 🤖 ZeravaneAI Response")
                st.markdown(f"<small style='color:#555;'>Source: GitHub API | <span class='model-tag'>{model_used}</span></small>", unsafe_allow_html=True)
                st.markdown(response_text)
                with st.expander("📁 Raw Repo Content"):
                    st.text_area("Content:", value=repo_content[:3000], disabled=True, height=200)
            else:
                st.error(f"Failed: {repo_content}")

# ── TAB 4 ─────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader("🔍 Tech Stack Detector")
    st.caption("Scrape any URL live and detect its full technology stack.")
    stack_url = st.text_input("URL to analyze", placeholder="https://vercel.com", key="stack_url")
    if st.button("🔍 Detect Tech Stack", use_container_width=True, key="stack_execute"):
        if not stack_url.strip():
            st.error("Enter a URL.")
        else:
            with st.spinner("🌐 Scraping + analyzing..."):
                raw_content, scrape_method = engine.scrape_live_url(stack_url.strip())
                stack_report = engine.detect_tech_stack(raw_content, stack_url.strip())
            st.markdown(f"<small style='color:#555;'>Scrape: <b style='color:#00D9FF;'>{scrape_method}</b></small>", unsafe_allow_html=True)
            st.markdown("### 🛠️ Detected Tech Stack")
            st.markdown(stack_report)
            with st.expander("🔍 Raw Scraped Content"):
                st.text_area("Content:", value=raw_content[:2000], disabled=True, height=150)

# ── TAB 5 ─────────────────────────────────────────────────────────────────────
with tab5:
    st.subheader("⚙️ Code Generator from Live Docs")
    st.caption("Scrape any docs URL and generate production-ready code from it.")
    cg_url = st.text_input("Documentation URL", placeholder="https://docs.stripe.com/api", key="codegen_url")
    cg_request = st.text_area("💬 What code to generate?", placeholder="Create a REST API with CRUD + JWT auth...", height=80, key="codegen_request")
    cg_lang = st.selectbox("Target Language", ["Python","JavaScript","TypeScript","Go","Rust","Java","C#","PHP","Ruby"], key="codegen_lang")
    if st.button("⚙️ Generate Code", use_container_width=True, key="codegen_execute"):
        if not cg_url.strip():
            st.error("Enter a docs URL.")
        elif not cg_request.strip():
            st.error("Describe what to generate.")
        else:
            with st.spinner(f"🌐 Scraping docs + generating {cg_lang} code..."):
                generated_code, scrape_method, model_used = engine.generate_code_from_docs(cg_url.strip(), cg_request.strip(), cg_lang)
            st.markdown(f"<small style='color:#555;'>Source: <b style='color:#00D9FF;'>{scrape_method}</b> | <span class='model-tag'>{model_used}</span></small>", unsafe_allow_html=True)
            st.markdown(f"### ⚙️ Generated {cg_lang} Code")
            st.markdown(generated_code)

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.markdown("<p style='text-align:center;font-size:11px;color:#333;'>ZeravaneAI · ScraperAPI × Gemini 2.5 Flash × Groq × AI/ML API</p>", unsafe_allow_html=True)
