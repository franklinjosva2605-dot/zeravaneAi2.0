# =============================================================================
# CRITICAL PLATFORM PATCHES — must run before all other imports
# =============================================================================
import os, sys
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

from dotenv import load_dotenv
load_dotenv()

import re
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.engine import ZeravaneEngine

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(page_title="ZeravaneAI", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    :root {
        --neon-cyan: #00D9FF;
        --neon-green: #00FF41;
        --neon-orange: #FF6B35;
        --neon-purple: #A855F7;
        --dark-bg: #0A0E27;
        --text-primary: #E0E6FF;
    }
    .main { background-color: #0F1419; color: var(--text-primary); }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stButton > button {
        border: 1.5px solid var(--neon-cyan) !important;
        background-color: rgba(0, 20, 40, 0.8) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
        box-shadow: 0 0 8px rgba(0, 217, 255, 0.3) !important;
    }
    .stButton > button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 0 20px rgba(0, 217, 255, 0.7) !important;
    }
    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 8px rgba(0,255,65,0.4); border-color: rgba(0,255,65,0.6); }
        50% { box-shadow: 0 0 20px rgba(0,255,65,0.8); border-color: rgba(0,255,65,1); }
    }
    @keyframes pulse-cyan {
        0%, 100% { box-shadow: 0 0 8px rgba(0,217,255,0.4); border-color: rgba(0,217,255,0.6); }
        50% { box-shadow: 0 0 20px rgba(0,217,255,0.8); border-color: rgba(0,217,255,1); }
    }
    @keyframes pulse-orange {
        0%, 100% { box-shadow: 0 0 8px rgba(255,107,53,0.4); border-color: rgba(255,107,53,0.6); }
        50% { box-shadow: 0 0 20px rgba(255,107,53,0.8); border-color: rgba(255,107,53,1); }
    }
    @keyframes pulse-purple {
        0%, 100% { box-shadow: 0 0 8px rgba(168,85,247,0.4); border-color: rgba(168,85,247,0.6); }
        50% { box-shadow: 0 0 20px rgba(168,85,247,0.8); border-color: rgba(168,85,247,1); }
    }
    .badge-green {
        display: inline-block; padding: 8px 16px; border-radius: 6px;
        border: 1.5px solid rgba(0,255,65,0.6); background: rgba(0,50,30,0.7);
        color: #00FF41; font-weight: 600; font-size: 14px;
        animation: pulse-green 2s ease-in-out infinite; margin: 8px 0;
    }
    .badge-cyan {
        display: inline-block; padding: 8px 16px; border-radius: 6px;
        border: 1.5px solid rgba(0,217,255,0.6); background: rgba(0,30,60,0.7);
        color: #00D9FF; font-weight: 600; font-size: 14px;
        animation: pulse-cyan 2s ease-in-out infinite; margin: 8px 0;
    }
    .badge-orange {
        display: inline-block; padding: 8px 16px; border-radius: 6px;
        border: 1.5px solid rgba(255,107,53,0.6); background: rgba(60,20,0,0.7);
        color: #FF6B35; font-weight: 600; font-size: 14px;
        animation: pulse-orange 2s ease-in-out infinite; margin: 8px 0;
    }
    .badge-purple {
        display: inline-block; padding: 6px 14px; border-radius: 6px;
        border: 1.5px solid rgba(168,85,247,0.6); background: rgba(40,0,60,0.7);
        color: #A855F7; font-weight: 600; font-size: 12px;
        animation: pulse-purple 2s ease-in-out infinite; margin: 4px 4px;
    }
    .scraper-banner {
        background: linear-gradient(135deg, rgba(0,20,50,0.9), rgba(0,40,80,0.9));
        border: 1px solid rgba(0,217,255,0.3);
        border-radius: 10px; padding: 12px 20px; margin: 10px 0;
        text-align: center;
    }
    .cache-hit-banner {
        background: rgba(0, 40, 20, 0.6);
        border: 1px solid rgba(0, 255, 65, 0.3);
        border-radius: 8px; padding: 8px 16px; margin: 6px 0;
        font-size: 13px; color: #00FF41;
    }
    .model-tag {
        display: inline-block; padding: 3px 10px; border-radius: 4px;
        background: rgba(168,85,247,0.15); border: 1px solid rgba(168,85,247,0.4);
        color: #A855F7; font-size: 11px; font-weight: 600; margin-left: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<h1 style='text-align:center; color:#00D9FF; text-shadow: 0 0 16px rgba(0,217,255,0.6);
           letter-spacing:2px; margin-bottom:2px;'>
⚡ ZeravaneAI — Web Intelligence Engine
</h1>
<p style='text-align:center; color:#00D9FF; font-size:11px; letter-spacing:2px;
          opacity:0.7; margin-top:0;'>
POWERED BY SCRAPERAPI × GEMINI 2.5 FLASH × GROQ × AI/ML API
</p>
""", unsafe_allow_html=True)

st.markdown("""
<div class='scraper-banner'>
    <span style='color:#00D9FF; font-weight:700; letter-spacing:1px;'>
        🌐 SCRAPERAPI INTEGRATION ACTIVE
    </span>
    <span style='color:#aaa; font-size:12px; margin-left:12px;'>
        JS Rendering · Rotating Proxies · Bot-Proof Scraping · Geo-Unblocked Access
    </span>
    <br>
    <span class='badge-purple'>⚡ Gemini 2.5 Flash</span>
    <span class='badge-purple'>🟣 Groq llama-3.3-70b</span>
    <span class='badge-purple'>🔶 AI/ML API gpt-4o-mini</span>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# ENGINE + SESSION STATE
# =============================================================================

@st.cache_resource
def get_engine():
    return ZeravaneEngine()

engine = get_engine()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_url" not in st.session_state:
    st.session_state.last_url = ""

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Agent Config")

    llm_tier = "⚡ Gemini 2.5 Flash"
    if engine.groq_enabled:
        llm_tier += " + 🟣 Groq"
    if engine.aiml_enabled:
        llm_tier += " + 🔶 AI/ML API"

    st.markdown(f"""
    <div style='background:rgba(0,20,40,0.6); border:1px solid rgba(0,217,255,0.2);
                border-radius:8px; padding:12px; font-size:12px; color:#aaa;'>
    <b style='color:#00D9FF;'>Scraping Stack</b><br>
    • ScraperAPI (Tier 1 — JS + Proxy)<br>
    • Standard Requests (Tier 2 — Fallback)<br><br>
    <b style='color:#A855F7;'>LLM Stack (3-Tier)</b><br>
    • Gemini 2.5 Flash (Primary)<br>
    • Groq llama-3.3-70b (Fallback)<br>
    • AI/ML API gpt-4o-mini (Last Resort)<br><br>
    <b style='color:#00D9FF;'>Vector Engine</b><br>
    • ChromaDB · 3000 chars / 300 overlap<br>
    • 2MB stream cap per URL
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    scraper_status = "🟢 Active" if engine.scraper_enabled else "🟡 Demo Mode (no SCRAPER_API_KEY)"
    groq_status = "🟢 Active" if engine.groq_enabled else "⚪ Not configured"
    aiml_status = "🟢 Active" if engine.aiml_enabled else "⚪ Not configured"

    st.write(f"**ScraperAPI:** {scraper_status}")
    st.write(f"**Groq:** {groq_status}")
    st.write(f"**AI/ML API:** {aiml_status}")

    if engine._cached_url:
        st.markdown(f"""
        <div class='cache-hit-banner'>
        ✅ Cached: <code style='font-size:11px;'>{engine._cached_url[:50]}{'...' if len(engine._cached_url) > 50 else ''}</code>
        </div>
        """, unsafe_allow_html=True)

    if st.button("🗑️ Clear Cache", use_container_width=True):
        try:
            engine.chroma_client.delete_collection(name=engine._cached_collection)
        except Exception:
            pass
        engine._cached_url = None
        st.session_state.last_url = ""
        st.session_state.chat_history = []
        st.rerun()

# =============================================================================
# MAIN TABS
# =============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌐 Live Agent Query",
    "🔗 Multi-URL Scraper",
    "🐙 GitHub Analyzer",
    "🔍 Tech Stack Detector",
    "⚙️ Code Generator"
])

# =============================================================================
# TAB 1 — LIVE AGENT QUERY
# =============================================================================
with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🌐 Ingestion Target")
        target_url = st.text_input(
            "Target URL (ScraperAPI handles JS-heavy and geo-blocked pages)",
            placeholder="https://docs.github.com/en/rest",
            value=st.session_state.last_url,
            key="tab1_url",
        )

    with col2:
        st.subheader("🔧 System Context")
        url_changed = target_url.strip() != st.session_state.last_url.strip()
        if url_changed and target_url.strip():
            st.info("🔄 New URL detected — will scrape fresh on next query.")
        elif engine._cached_url and not url_changed:
            st.success("✅ URL cached — skipping re-scrape for this query.")
        else:
            st.caption(
                "ZeravaneAI uses ScraperAPI to access any public URL — "
                "including JavaScript-heavy and geo-blocked pages."
            )

    st.markdown("#### 📊 Agent Status")
    col_s1, col_s2 = st.columns([2, 1])

    with col_s1:
        if not target_url or not target_url.strip():
            st.markdown(
                "<div class='badge-cyan'>🔵 [Standby] Core Engine Ready — Enter URL to activate Web Intelligence</div>",
                unsafe_allow_html=True,
            )
        elif engine.scraper_enabled:
            st.markdown(
                "<div class='badge-green'>🟢 [Active] ScraperAPI Web Intelligence Online — Bot-Proof Scraping Ready</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='badge-orange'>🟡 [Demo Mode] Standard Scraping — Add SCRAPER_API_KEY for full power</div>",
                unsafe_allow_html=True,
            )

    with col_s2:
        if engine.scraper_enabled:
            st.markdown("<div class='badge-green'>🛡️ Bot Detection: BYPASSED</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='badge-cyan'>ℹ️ Demo Mode Active</div>", unsafe_allow_html=True)

    user_query = st.text_area(
        "💬 Ask any technical or development question",
        placeholder="How does authentication work on this platform? Explain the API endpoints...",
        height=100,
        key="tab1_query",
    )

    force_rescrape = st.checkbox(
        "🔄 Force re-scrape (bypass URL cache)",
        value=False,
        key="tab1_force",
        help="Tick this to re-scrape the URL even if it was already cached.",
    )

    st.markdown("---")

    if st.button("🚀 Execute Agent Search", use_container_width=True, key="tab1_execute"):
        if not user_query.strip():
            st.error("Please enter a query before executing the agent search.")
        else:
            url_to_use = target_url.strip() if target_url and target_url.strip() else None
            spinner_msg = (
                "🌐 ScraperAPI fetching live web data... parsing nodes... updating vector index..."
                if url_to_use else
                "🧠 ZeravaneAI processing query on base model weights..."
            )
            with st.spinner(spinner_msg):
                response_text, context_payload, scrape_method, model_used = engine.execute_live_agent_query(
                    user_query=user_query,
                    target_url=url_to_use,
                    force_rescrape=force_rescrape,
                )

            if url_to_use:
                st.session_state.last_url = url_to_use

            st.session_state.chat_history.append({
                "query": user_query,
                "response": response_text,
                "scrape_method": scrape_method,
                "model_used": model_used,
                "url": url_to_use,
            })

            st.markdown("### 🤖 ZeravaneAI Response")
            if url_to_use:
                st.markdown(
                    f"<small style='color:#555;'>Data Source: "
                    f"<b style='color:#00D9FF;'>{scrape_method}</b>"
                    f"<span class='model-tag'>{model_used}</span></small>",
                    unsafe_allow_html=True,
                )
            st.markdown(response_text)

            with st.expander("🔍 Inspect Retrieved Vector Context"):
                st.text_area(
                    "Raw context injected into LLM:",
                    value=(context_payload if context_payload else "[No context retrieved — running on base model weights]"),
                    disabled=True,
                    height=180,
                )

    if st.session_state.chat_history:
        st.markdown("---")
        with st.expander(f"📜 Session History ({len(st.session_state.chat_history)} queries)"):
            for i, entry in enumerate(reversed(st.session_state.chat_history), 1):
                model_tag = entry.get("model_used", "")
                st.markdown(
                    f"**Q{i}:** {entry['query']}  \n"
                    f"<small style='color:#555;'>Source: {entry['scrape_method']} | "
                    f"Model: {model_tag} | URL: {entry['url'] or 'None'}</small>",
                    unsafe_allow_html=True,
                )
                st.markdown(entry["response"][:400] + "..." if len(entry["response"]) > 400 else entry["response"])
                st.markdown("---")

# =============================================================================
# TAB 2 — MULTI-URL SCRAPER
# =============================================================================
with tab2:
    st.subheader("🔗 Multi-URL Scraper")
    st.caption("Scrape multiple URLs simultaneously and merge into a single unified RAG knowledge base.")

    st.markdown("""
    <div class='scraper-banner'>
        <span style='color:#00D9FF; font-weight:700;'>📡 ScraperAPI — JS Rendering + Rotating Proxies</span>
        <span style='color:#aaa; font-size:12px; margin-left:12px;'>
            Each URL scraped independently via 2-tier fallback — merged into unified ChromaDB index
        </span>
    </div>
    """, unsafe_allow_html=True)

    multi_urls_input = st.text_area(
        "Enter URLs (one per line)",
        placeholder="https://docs.fastapi.tiangolo.com\nhttps://docs.pydantic.dev\nhttps://www.uvicorn.org",
        height=150,
        key="multi_urls",
    )

    multi_query = st.text_area(
        "💬 Ask a question across all scraped sources",
        placeholder="Compare authentication approaches across these frameworks...",
        height=80,
        key="multi_query",
    )

    if st.button("🚀 Scrape All URLs + Query", use_container_width=True, key="multi_execute"):
        urls = [u.strip() for u in multi_urls_input.strip().splitlines() if u.strip()]
        if not urls:
            st.error("Please enter at least one URL.")
        elif not multi_query.strip():
            st.error("Please enter a query.")
        else:
            with st.spinner(f"🌐 Scraping {len(urls)} URLs via ScraperAPI..."):
                chunks, summary = engine.scrape_multiple_urls(urls)

            st.markdown("#### 📊 Scrape Results")
            for line in summary.splitlines():
                if line.startswith("✅"):
                    st.success(line)
                else:
                    st.error(line)

            if chunks:
                with st.spinner("🧠 Querying unified knowledge base..."):
                    response_text, context_payload, scrape_method, model_used = engine.execute_live_agent_query(
                        user_query=multi_query,
                        target_url=None,
                        force_rescrape=False,
                    )
                st.markdown("### 🤖 ZeravaneAI Response")
                st.markdown(
                    f"<small style='color:#555;'>Sources: {len(urls)} URLs merged | "
                    f"<span class='model-tag'>{model_used}</span></small>",
                    unsafe_allow_html=True,
                )
                st.markdown(response_text)
            else:
                st.warning("No URLs scraped successfully. Check your URLs and try again.")

# =============================================================================
# TAB 3 — GITHUB REPO ANALYZER
# =============================================================================
with tab3:
    st.subheader("🐙 GitHub Repo Analyzer")
    st.caption("Analyze any public GitHub repository — README, file structure, metadata — then ask questions about it.")

    st.markdown("""
    <div class='scraper-banner'>
        <span style='color:#00D9FF; font-weight:700;'>🐙 GitHub API Integration</span>
        <span style='color:#aaa; font-size:12px; margin-left:12px;'>
            Fetches README + file tree + repo metadata · Works on all public repos · No auth required
        </span>
    </div>
    """, unsafe_allow_html=True)

    github_url_input = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/tiangolo/fastapi",
        key="github_url",
    )

    github_query = st.text_area(
        "💬 Ask about this repository",
        placeholder="What does this project do? What's the tech stack? How do I get started?",
        height=80,
        key="github_query",
    )

    if st.button("🚀 Analyze Repository", use_container_width=True, key="github_execute"):
        if not github_url_input.strip():
            st.error("Please enter a GitHub repository URL.")
        elif not github_query.strip():
            st.error("Please enter a question about the repository.")
        else:
            with st.spinner("🐙 Fetching repository data via GitHub API..."):
                repo_content, metadata = engine.analyze_github_repo(github_url_input.strip())

            if metadata:
                st.markdown("#### 📊 Repository Info")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("⭐ Stars", f"{metadata.get('stars', 0):,}")
                m2.metric("🍴 Forks", f"{metadata.get('forks', 0):,}")
                m3.metric("💻 Language", metadata.get('language', 'N/A'))
                m4.metric("📦 Repo", metadata.get('name', 'N/A').split('/')[-1])

                if metadata.get('description'):
                    st.info(f"📝 {metadata['description']}")

                if metadata.get('topics'):
                    topics_html = " ".join([f"<span class='badge-purple'>{t}</span>" for t in metadata['topics'][:8]])
                    st.markdown(topics_html, unsafe_allow_html=True)

            if not repo_content.startswith("GitHub_Error") and not repo_content.startswith("Invalid"):
                with st.spinner("🧠 Analyzing repository and answering your question..."):
                    response_text, context_payload, scrape_method, model_used = engine.execute_live_agent_query(
                        user_query=github_query,
                        target_url=None,
                        force_rescrape=False,
                    )
                st.markdown("### 🤖 ZeravaneAI Response")
                st.markdown(
                    f"<small style='color:#555;'>Source: GitHub API | "
                    f"<span class='model-tag'>{model_used}</span></small>",
                    unsafe_allow_html=True,
                )
                st.markdown(response_text)

                with st.expander("📁 View Raw Repository Content"):
                    st.text_area("Fetched content:", value=repo_content[:3000], disabled=True, height=200)
            else:
                st.error(f"Failed to fetch repository: {repo_content}")

# =============================================================================
# TAB 4 — TECH STACK DETECTOR
# =============================================================================
with tab4:
    st.subheader("🔍 Tech Stack Detector")
    st.caption("Enter any URL — ZeravaneAI scrapes it live and detects the complete technology stack.")

    st.markdown("""
    <div class='scraper-banner'>
        <span style='color:#00D9FF; font-weight:700;'>🔬 AI-Powered Stack Analysis</span>
        <span style='color:#aaa; font-size:12px; margin-left:12px;'>
            ScraperAPI fetches live content · Gemini analyzes patterns · Returns structured tech report
        </span>
    </div>
    """, unsafe_allow_html=True)

    stack_url = st.text_input(
        "Website or App URL to analyze",
        placeholder="https://vercel.com or https://github.com/tiangolo/fastapi",
        key="stack_url",
    )

    if st.button("🔍 Detect Tech Stack", use_container_width=True, key="stack_execute"):
        if not stack_url.strip():
            st.error("Please enter a URL to analyze.")
        else:
            with st.spinner("🌐 Scraping with ScraperAPI + analyzing tech stack..."):
                raw_content, scrape_method = engine.scrape_live_url(stack_url.strip())
                stack_report = engine.detect_tech_stack(raw_content, stack_url.strip())

            st.markdown(
                f"<small style='color:#555;'>Scrape Method: <b style='color:#00D9FF;'>{scrape_method}</b></small>",
                unsafe_allow_html=True,
            )
            st.markdown("### 🛠️ Detected Tech Stack")
            st.markdown(stack_report)

            with st.expander("🔍 Raw Scraped Content (first 2000 chars)"):
                st.text_area("Scraped content:", value=raw_content[:2000], disabled=True, height=150)

# =============================================================================
# TAB 5 — CODE GENERATOR FROM DOCS
# =============================================================================
with tab5:
    st.subheader("⚙️ Code Generator from Live Docs")
    st.caption("Paste any documentation URL — ZeravaneAI scrapes it live and generates production-ready code based on it.")

    st.markdown("""
    <div class='scraper-banner'>
        <span style='color:#00D9FF; font-weight:700;'>🤖 Live Docs → Production Code</span>
        <span style='color:#aaa; font-size:12px; margin-left:12px;'>
            ScraperAPI fetches live docs · RAG indexes content · Gemini generates boilerplate
        </span>
    </div>
    """, unsafe_allow_html=True)

    codegen_url = st.text_input(
        "Documentation URL",
        placeholder="https://docs.stripe.com/api or https://docs.fastapi.tiangolo.com",
        key="codegen_url",
    )

    codegen_request = st.text_area(
        "💬 What code do you want generated?",
        placeholder="Create a complete REST API with CRUD operations and JWT authentication...",
        height=80,
        key="codegen_request",
    )

    codegen_language = st.selectbox(
        "Target Language",
        ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C#", "PHP", "Ruby"],
        key="codegen_lang",
    )

    if st.button("⚙️ Generate Code from Live Docs", use_container_width=True, key="codegen_execute"):
        if not codegen_url.strip():
            st.error("Please enter a documentation URL.")
        elif not codegen_request.strip():
            st.error("Please describe what code you want generated.")
        else:
            with st.spinner(f"🌐 Scraping docs + generating {codegen_language} code..."):
                generated_code, scrape_method, model_used = engine.generate_code_from_docs(
                    docs_url=codegen_url.strip(),
                    generation_request=codegen_request.strip(),
                    language=codegen_language,
                )

            st.markdown(
                f"<small style='color:#555;'>Docs Source: <b style='color:#00D9FF;'>{scrape_method}</b> | "
                f"<span class='model-tag'>{model_used}</span></small>",
                unsafe_allow_html=True,
            )
            st.markdown(f"### ⚙️ Generated {codegen_language} Code")
            st.markdown(generated_code)

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.markdown("""
<p style='text-align:center; font-size:11px; color:#333;'>
ZeravaneAI · ScraperAPI × Gemini 2.5 Flash × Groq × AI/ML API
</p>
""", unsafe_allow_html=True)
