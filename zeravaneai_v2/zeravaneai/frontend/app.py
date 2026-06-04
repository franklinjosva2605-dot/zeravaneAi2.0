# =============================================================================
# Platform patches — must run before all other imports
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
st.set_page_config(
    page_title="ZeravaneAI — Intelligent Web Research Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .main { background-color: #0B0F1A; color: #E2E8F0; }
    .block-container { padding-top: 2rem; }

    /* Clean input styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #111827 !important;
        border: 1px solid #1E3A5F !important;
        border-radius: 8px !important;
        color: #E2E8F0 !important;
        font-size: 14px !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
    }

    /* Button */
    .stButton > button {
        background: linear-gradient(135deg, #1D4ED8, #2563EB) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 24px !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563EB, #3B82F6) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(59,130,246,0.35) !important;
    }

    /* Hero section */
    .hero-container {
        background: linear-gradient(135deg, #0F172A 0%, #111827 50%, #0F2444 100%);
        border: 1px solid #1E3A5F;
        border-radius: 16px;
        padding: 40px 48px;
        margin-bottom: 32px;
        text-align: center;
    }
    .hero-logo {
        font-size: 48px;
        font-weight: 800;
        background: linear-gradient(135deg, #3B82F6, #60A5FA, #93C5FD);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
        margin-bottom: 8px;
    }
    .hero-tagline {
        font-size: 17px;
        color: #94A3B8;
        font-weight: 400;
        margin-bottom: 24px;
    }
    .hero-pill {
        display: inline-block;
        background: rgba(59,130,246,0.1);
        border: 1px solid rgba(59,130,246,0.3);
        color: #60A5FA;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 14px;
        border-radius: 20px;
        margin: 3px 4px;
        letter-spacing: 0.5px;
    }

    /* Stat cards */
    .stat-card {
        background: #111827;
        border: 1px solid #1E3A5F;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
    }
    .stat-value {
        font-size: 28px;
        font-weight: 700;
        color: #3B82F6;
        line-height: 1;
        margin-bottom: 6px;
    }
    .stat-label {
        font-size: 12px;
        color: #64748B;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    /* Feature cards */
    .feature-card {
        background: #111827;
        border: 1px solid #1E3A5F;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        transition: border-color 0.2s;
    }
    .feature-card:hover { border-color: #3B82F6; }
    .feature-icon { font-size: 24px; margin-bottom: 10px; }
    .feature-title { font-size: 15px; font-weight: 600; color: #E2E8F0; margin-bottom: 6px; }
    .feature-desc { font-size: 13px; color: #64748B; line-height: 1.5; }

    /* Status badges */
    .status-active {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3);
        color: #10B981; font-size: 12px; font-weight: 600;
        padding: 4px 12px; border-radius: 20px;
    }
    .status-demo {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3);
        color: #F59E0B; font-size: 12px; font-weight: 600;
        padding: 4px 12px; border-radius: 20px;
    }
    .status-offline {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(100,116,139,0.1); border: 1px solid rgba(100,116,139,0.3);
        color: #64748B; font-size: 12px; font-weight: 500;
        padding: 4px 12px; border-radius: 20px;
    }

    /* Model tag */
    .model-tag {
        background: rgba(139,92,246,0.1);
        border: 1px solid rgba(139,92,246,0.3);
        color: #A78BFA;
        font-size: 11px; font-weight: 600;
        padding: 2px 10px; border-radius: 4px;
        margin-left: 8px;
    }

    /* Response container */
    .response-box {
        background: #111827;
        border: 1px solid #1E3A5F;
        border-left: 3px solid #3B82F6;
        border-radius: 8px;
        padding: 20px 24px;
        margin-top: 16px;
    }

    /* Sidebar */
    .sidebar-section {
        background: #111827;
        border: 1px solid #1E3A5F;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
        font-size: 13px;
    }
    .sidebar-label { color: #64748B; font-size: 11px; font-weight: 600; 
                     text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #111827;
        padding: 4px;
        border-radius: 10px;
        border: 1px solid #1E3A5F;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px !important;
        color: #64748B !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }
    .stTabs [aria-selected="true"] {
        background: #1D4ED8 !important;
        color: white !important;
    }

    /* Cache badge */
    .cache-badge {
        background: rgba(16,185,129,0.08);
        border: 1px solid rgba(16,185,129,0.2);
        color: #10B981;
        font-size: 12px; padding: 4px 12px;
        border-radius: 6px; display: inline-block;
    }

    /* Divider */
    hr { border-color: #1E293B !important; }
</style>
""", unsafe_allow_html=True)


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
    st.markdown("""
    <div style='text-align:center; padding: 12px 0 20px;'>
        <div style='font-size:22px; font-weight:800; color:#3B82F6; letter-spacing:-0.5px;'>⚡ ZeravaneAI</div>
        <div style='font-size:11px; color:#475569; margin-top:4px;'>Intelligent Web Research Platform</div>
    </div>
    """, unsafe_allow_html=True)

    # Scraping status
    st.markdown("<div class='sidebar-label'>Scraping Engine</div>", unsafe_allow_html=True)
    if engine.scraper_enabled:
        st.markdown("<span class='status-active'>● ScraperAPI Active</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-demo'>● Demo Mode (Direct HTTP)</span>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # LLM status
    st.markdown("<div class='sidebar-label'>AI Models</div>", unsafe_allow_html=True)
    st.markdown("<span class='status-active'>● Gemini 2.5 Flash</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if engine.groq_enabled:
        st.markdown("<span class='status-active'>● Groq (llama-3.3-70b)</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-offline'>○ Groq — not configured</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if engine.aiml_enabled:
        st.markdown("<span class='status-active'>● AI/ML API (gpt-4o-mini)</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-offline'>○ AI/ML API — not configured</span>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Cache info
    if engine._cached_url:
        st.markdown("<div class='sidebar-label'>Active Cache</div>", unsafe_allow_html=True)
        cached_display = engine._cached_url if engine._cached_url != "__multi__" else "Multi-URL session"
        st.markdown(
            f"<div class='cache-badge'>✓ {cached_display[:40]}{'...' if len(cached_display) > 40 else ''}</div>",
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear Cache & Reset", use_container_width=True):
            try:
                engine.chroma_client.delete_collection(name=engine._cached_collection)
            except Exception:
                pass
            engine._cached_url = None
            st.session_state.last_url = ""
            st.session_state.chat_history = []
            st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style='font-size:11px; color:#334155; text-align:center; line-height:1.8;'>
        <b style='color:#3B82F6;'>Architecture</b><br>
        ScraperAPI → Proxy → Direct<br>
        Gemini → Groq → AI/ML API<br>
        ChromaDB · RAG · 3K chunks<br><br>
        <b style='color:#475569;'>v2.0.0 — Franklin Josva A</b>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# HERO SECTION
# =============================================================================
st.markdown("""
<div class='hero-container'>
    <div class='hero-logo'>ZeravaneAI</div>
    <div class='hero-tagline'>Turn any website into structured intelligence — instantly.</div>
    <div>
        <span class='hero-pill'>Live Web Scraping</span>
        <span class='hero-pill'>RAG Pipeline</span>
        <span class='hero-pill'>3-Tier LLM</span>
        <span class='hero-pill'>GitHub Intelligence</span>
        <span class='hero-pill'>Tech Stack Detection</span>
        <span class='hero-pill'>Code Generation</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Stats row
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("<div class='stat-card'><div class='stat-value'>3×</div><div class='stat-label'>Scraping Fallback Tiers</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='stat-card'><div class='stat-value'>3×</div><div class='stat-label'>LLM Fallback Models</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown("<div class='stat-card'><div class='stat-value'>100%</div><div class='stat-label'>Uptime by Design</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div class='stat-card'><div class='stat-value'>∞</div><div class='stat-label'>URLs Processable</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =============================================================================
# MAIN TABS
# =============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "  🔍 Web Research  ",
    "  🔗 Multi-URL  ",
    "  🐙 GitHub  ",
    "  🛠️ Tech Stack  ",
    "  ⚙️ Code Generator  ",
])


# =============================================================================
# TAB 1 — LIVE WEB RESEARCH
# =============================================================================
with tab1:
    st.markdown("#### Web Research Agent")
    st.caption("Enter any URL and ask questions. ZeravaneAI scrapes it live, indexes it, and answers using RAG.")

    col1, col2 = st.columns([3, 2])
    with col1:
        target_url = st.text_input(
            "Target URL",
            placeholder="https://docs.stripe.com/api",
            value=st.session_state.last_url,
            key="tab1_url",
            label_visibility="collapsed",
        )
    with col2:
        force_rescrape = st.checkbox("Force re-scrape", value=False, key="tab1_force")

    user_query = st.text_area(
        "Your question",
        placeholder="What authentication methods does this API support? How do I get started?",
        height=100,
        key="tab1_query",
        label_visibility="collapsed",
    )

    if st.button("🔍 Research Now", key="tab1_execute", use_container_width=False):
        if not user_query.strip():
            st.error("Please enter a question.")
        else:
            url_to_use = target_url.strip() if target_url and target_url.strip() else None
            msg = "⚡ Scraping live data and running RAG pipeline..." if url_to_use else "🧠 Processing with AI..."
            with st.spinner(msg):
                response_text, context_payload, scrape_method, model_used = engine.execute_live_agent_query(
                    user_query=user_query,
                    target_url=url_to_use,
                    force_rescrape=force_rescrape,
                )
            if url_to_use:
                st.session_state.last_url = url_to_use

            st.session_state.chat_history.append({
                "query": user_query, "response": response_text,
                "scrape_method": scrape_method, "model_used": model_used, "url": url_to_use,
            })

            st.markdown(f"""
            <div style='font-size:12px; color:#475569; margin: 12px 0 4px;'>
                Source: <b style='color:#60A5FA;'>{scrape_method}</b>
                <span class='model-tag'>{model_used}</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(response_text)

            with st.expander("View retrieved context chunks"):
                st.text_area("Context injected into LLM:",
                    value=context_payload or "[No context — running on base model]",
                    disabled=True, height=160)

    if st.session_state.chat_history:
        st.markdown("---")
        with st.expander(f"Session history ({len(st.session_state.chat_history)} queries)"):
            for i, entry in enumerate(reversed(st.session_state.chat_history), 1):
                st.markdown(f"**Q{i}:** {entry['query']}")
                st.markdown(f"<small style='color:#475569;'>{entry['scrape_method']} | {entry['model_used']}</small>", unsafe_allow_html=True)
                preview = entry['response'][:400] + "..." if len(entry['response']) > 400 else entry['response']
                st.markdown(preview)
                st.markdown("---")


# =============================================================================
# TAB 2 — MULTI-URL SCRAPER
# =============================================================================
with tab2:
    st.markdown("#### Multi-URL Research")
    st.caption("Scrape multiple sources simultaneously and query across all of them as a unified knowledge base.")

    multi_urls_input = st.text_area(
        "URLs (one per line)",
        placeholder="https://docs.fastapi.tiangolo.com\nhttps://docs.pydantic.dev\nhttps://www.uvicorn.org",
        height=140,
        key="multi_urls",
    )

    multi_query = st.text_area(
        "Question across all sources",
        placeholder="Compare authentication approaches across these frameworks...",
        height=80,
        key="multi_query",
    )

    if st.button("🔗 Scrape All & Query", use_container_width=False, key="multi_execute"):
        urls = [u.strip() for u in multi_urls_input.strip().splitlines() if u.strip()]
        if not urls:
            st.error("Please enter at least one URL.")
        elif not multi_query.strip():
            st.error("Please enter a question.")
        else:
            with st.spinner(f"Scraping {len(urls)} URLs..."):
                chunks, summary = engine.scrape_multiple_urls(urls)

            st.markdown("**Scrape Results:**")
            for line in summary.splitlines():
                if line.startswith("✅"):
                    st.success(line)
                else:
                    st.error(line)

            if chunks:
                with st.spinner("Querying unified knowledge base..."):
                    response_text, context_payload, scrape_method, model_used = engine.execute_live_agent_query(
                        user_query=multi_query, target_url=None, force_rescrape=False,
                    )
                st.markdown(f"<small style='color:#475569;'>Sources: {len(urls)} URLs merged <span class='model-tag'>{model_used}</span></small>", unsafe_allow_html=True)
                st.markdown(response_text)
            else:
                st.warning("No URLs scraped successfully.")


# =============================================================================
# TAB 3 — GITHUB ANALYZER
# =============================================================================
with tab3:
    st.markdown("#### GitHub Repository Intelligence")
    st.caption("Analyze any public GitHub repository — README, file structure, metadata — then ask questions about it.")

    github_url_input = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/tiangolo/fastapi",
        key="github_url",
    )

    github_query = st.text_area(
        "Your question",
        placeholder="What does this project do? What's the tech stack? How do I get started?",
        height=80,
        key="github_query",
    )

    if st.button("🐙 Analyze Repository", use_container_width=False, key="github_execute"):
        if not github_url_input.strip():
            st.error("Please enter a GitHub URL.")
        elif not github_query.strip():
            st.error("Please enter a question.")
        else:
            with st.spinner("Fetching repository data..."):
                repo_content, metadata = engine.analyze_github_repo(github_url_input.strip())

            if metadata:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("⭐ Stars", f"{metadata.get('stars', 0):,}")
                m2.metric("🍴 Forks", f"{metadata.get('forks', 0):,}")
                m3.metric("💻 Language", metadata.get('language', 'N/A'))
                m4.metric("📦 Repo", metadata.get('name', 'N/A').split('/')[-1])

                if metadata.get('description'):
                    st.info(f"📝 {metadata['description']}")

            if not repo_content.startswith(("GitHub_Error", "Invalid")):
                with st.spinner("Analyzing repository..."):
                    response_text, context_payload, scrape_method, model_used = engine.execute_live_agent_query(
                        user_query=github_query, target_url=None, force_rescrape=False,
                    )
                st.markdown(f"<small style='color:#475569;'>GitHub API <span class='model-tag'>{model_used}</span></small>", unsafe_allow_html=True)
                st.markdown(response_text)

                with st.expander("View raw repository content"):
                    st.text_area("Fetched content:", value=repo_content[:3000], disabled=True, height=200)
            else:
                st.error(f"Failed: {repo_content}")


# =============================================================================
# TAB 4 — TECH STACK DETECTOR
# =============================================================================
with tab4:
    st.markdown("#### Tech Stack Detector")
    st.caption("Enter any website URL — ZeravaneAI scrapes it and identifies the complete technology stack.")

    stack_url = st.text_input(
        "Website URL",
        placeholder="https://vercel.com or https://linear.app",
        key="stack_url",
    )

    if st.button("🛠️ Detect Stack", use_container_width=False, key="stack_execute"):
        if not stack_url.strip():
            st.error("Please enter a URL.")
        else:
            with st.spinner("Scraping and analyzing..."):
                raw_content, scrape_method = engine.scrape_live_url(stack_url.strip())
                stack_report = engine.detect_tech_stack(raw_content, stack_url.strip())

            st.markdown(f"<small style='color:#475569;'>Scraped via: <b style='color:#60A5FA;'>{scrape_method}</b></small>", unsafe_allow_html=True)
            st.markdown("### Detected Stack")
            st.markdown(stack_report)

            with st.expander("View raw scraped content"):
                st.text_area("Content:", value=raw_content[:2000], disabled=True, height=150)


# =============================================================================
# TAB 5 — CODE GENERATOR
# =============================================================================
with tab5:
    st.markdown("#### Code Generator from Live Docs")
    st.caption("Point ZeravaneAI at any documentation URL — it scrapes it live and generates production-ready code.")

    codegen_url = st.text_input(
        "Documentation URL",
        placeholder="https://docs.stripe.com/api or https://docs.fastapi.tiangolo.com",
        key="codegen_url",
    )

    codegen_request = st.text_area(
        "What code do you want?",
        placeholder="Create a complete payment integration with webhook handling and error management...",
        height=80,
        key="codegen_request",
    )

    codegen_language = st.selectbox(
        "Language",
        ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C#", "PHP", "Ruby"],
        key="codegen_lang",
    )

    if st.button("⚙️ Generate Code", use_container_width=False, key="codegen_execute"):
        if not codegen_url.strip():
            st.error("Please enter a documentation URL.")
        elif not codegen_request.strip():
            st.error("Please describe what you want built.")
        else:
            with st.spinner(f"Scraping docs + generating {codegen_language} code..."):
                generated_code, scrape_method, model_used = engine.generate_code_from_docs(
                    docs_url=codegen_url.strip(),
                    generation_request=codegen_request.strip(),
                    language=codegen_language,
                )
            st.markdown(f"<small style='color:#475569;'>Docs: <b style='color:#60A5FA;'>{scrape_method}</b> <span class='model-tag'>{model_used}</span></small>", unsafe_allow_html=True)
            st.markdown(f"### Generated {codegen_language} Code")
            st.markdown(generated_code)


# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.markdown("""
<div style='text-align:center; padding: 16px 0 8px;'>
    <div style='font-size:13px; color:#334155;'>
        <b style='color:#3B82F6;'>ZeravaneAI</b> &nbsp;·&nbsp; 
        Built by <b style='color:#60A5FA;'>Franklin Josva A</b> &nbsp;·&nbsp;
        Team Singleton Vanguard
    </div>
    <div style='font-size:11px; color:#1E293B; margin-top:6px;'>
        ScraperAPI · Gemini 2.5 Flash · Groq · ChromaDB · RAG
    </div>
</div>
""", unsafe_allow_html=True)
