import os
import re
import requests
from bs4 import BeautifulSoup
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


class ZeravaneEngine:
    """
    ZeravaneAI Core Engine
    Features:
    - ScraperAPI integration for bot-resistant, geo-unblocked scraping
    - Resilient 2-tier scraping fallback (ScraperAPI → Standard requests)
    - Enhanced RAG pipeline with ChromaDB persistent vector store
    - Session-aware URL caching (avoids redundant re-scraping)
    - 3-tier LLM fallback: Gemini 2.5 Flash → Groq → AI/ML API
    - Multi-URL scraping — merge multiple sources into unified RAG index
    - GitHub repo analyzer — fetch README + file tree via GitHub API
    - Auto tech stack detection from live scraped content
    - Code generation from live documentation
    """

    SCRAPER_API_BASE = "http://api.scraperapi.com"
    MIN_TEXT_LENGTH = 100

    def __init__(self, chroma_path="./chroma_db"):
        # ── Gemini API key: Streamlit Cloud secrets → local .env fallback ──
        try:
            import streamlit as st
            api_key = (
                st.secrets.get("GEMINI_API_KEY")
                or st.secrets.get("GOOGLE_API_KEY")
                or os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
            )
        except Exception:
            api_key = (
                os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
            )

        if not api_key:
            raise ValueError(
                "Gemini API key not found. "
                "Add GEMINI_API_KEY to Streamlit Cloud secrets or your local .env file."
            )

        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)

        # ── ScraperAPI credentials ──
        try:
            import streamlit as st
            self.scraper_api_key = (
                st.secrets.get("SCRAPER_API_KEY")
                or os.environ.get("SCRAPER_API_KEY", "")
            )
        except Exception:
            self.scraper_api_key = os.environ.get("SCRAPER_API_KEY", "")

        self.scraper_enabled = bool(self.scraper_api_key)

        # ── Groq fallback credentials ──
        try:
            import streamlit as st
            groq_key = (
                st.secrets.get("GROQ_API_KEY")
                or os.environ.get("GROQ_API_KEY", "")
            )
            aiml_key = (
                st.secrets.get("AIML_API_KEY")
                or os.environ.get("AIML_API_KEY", "")
            )
        except Exception:
            groq_key = os.environ.get("GROQ_API_KEY", "")
            aiml_key = os.environ.get("AIML_API_KEY", "")

        self.groq_api_key = groq_key
        self.aiml_api_key = aiml_key
        self.groq_enabled = bool(groq_key)
        self.aiml_enabled = bool(aiml_key)

        # Session cache
        self._cached_url = None
        self._cached_collection = "zeravane_cache"

    # ── Scraping tiers ──────────────────────────────────────────────────────

    def scrape_with_scraper_api(self, url: str) -> str:
        """
        TIER 1: ScraperAPI.
        Handles JS rendering, rotating proxies, CAPTCHAs, and geo-unblocking.
        """
        try:
            params = {
                "api_key": self.scraper_api_key,
                "url": url,
                "render": "true",   # JS rendering
                "country_code": "us",
            }
            response = requests.get(
                self.SCRAPER_API_BASE,
                params=params,
                timeout=60,
                stream=True,
            )
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > 2 * 1024 * 1024:
                    break

            if response.status_code == 200:
                soup = BeautifulSoup(content.decode("utf-8", errors="ignore"), "html.parser")
                for el in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    el.extract()
                text = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
                return text
            return f"Error: ScraperAPI returned status {response.status_code}"
        except Exception as e:
            return f"ScraperAPI_Error: {str(e)}"

    def scrape_fallback(self, url: str) -> str:
        """
        TIER 2: Standard requests fallback (no proxy).
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > 2 * 1024 * 1024:
                    break

            if response.status_code != 200:
                return f"Error: Request failed with status {response.status_code}"

            soup = BeautifulSoup(content.decode("utf-8", errors="ignore"), "html.parser")
            for el in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                el.extract()
            text = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
            return text
        except Exception as e:
            return f"Fallback_Error: {str(e)}"

    def scrape_live_url(self, url: str) -> tuple:
        """
        2-Tier Resilient Scraping:
          1. ScraperAPI (bot-proof, JS rendering, rotating proxies)
          2. Standard requests fallback
        Returns: (scraped_text, method_used)
        """
        _error_prefixes = ("Error:", "ScraperAPI_Error:", "Fallback_Error:")

        if self.scraper_enabled:
            result = self.scrape_with_scraper_api(url)
            if result and not any(result.startswith(p) for p in _error_prefixes):
                return result, "🟢 ScraperAPI (Bot-Proof)"

        result = self.scrape_fallback(url)
        return result, "⚪ Standard Requests (No Proxy)"

    # ── RAG helpers ────────────────────────────────────────────────────────

    def chunk_text(self, text: str, max_chars: int = 3000, overlap: int = 300) -> list:
        """Split text into overlapping chunks for vector indexing."""
        if len(text) <= max_chars:
            return [text]
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start: start + max_chars])
            start += max_chars - overlap
        return chunks

    def refresh_vector_index(self, collection_name: str, text_chunks: list) -> bool:
        """Wipe and rebuild the ChromaDB collection with new chunks."""
        try:
            try:
                self.chroma_client.delete_collection(name=collection_name)
            except Exception:
                pass
            collection = self.chroma_client.create_collection(name=collection_name)
            collection.add(
                documents=text_chunks,
                ids=[f"chunk_{i}" for i in range(len(text_chunks))],
                metadatas=[{"index": i} for i in range(len(text_chunks))],
            )
            return True
        except Exception as e:
            print(f"[ZeravaneEngine] Vector index error: {e}")
            return False

    def query_vector_context(
        self, collection_name: str, query: str, n_results: int = 3
    ) -> str:
        """Retrieve the top-N most relevant chunks from ChromaDB."""
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            available = collection.count()
            if available == 0:
                return ""
            n = min(n_results, available)
            results = collection.query(query_texts=[query], n_results=n)
            docs = []
            if results and "documents" in results:
                for sublist in results["documents"]:
                    docs.extend(sublist)
            return "\n\n".join(docs)
        except Exception as e:
            print(f"[ZeravaneEngine] Vector query error: {e}")
            return ""

    # ── 3-Tier LLM Inference ────────────────────────────────────────────────

    def _infer(self, system_instruction: str, prompt: str) -> tuple:
        """
        3-Tier LLM Fallback:
          Tier 1: Gemini 2.5 Flash (primary)
          Tier 2: Groq llama-3.3-70b (fallback)
          Tier 3: AI/ML API gpt-4o-mini (last resort)
        Returns: (response_text, model_used)
        """
        # Tier 1 — Gemini
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

        # Tier 2 — Groq
        if self.groq_enabled:
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                    },
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
                    headers={
                        "Authorization": f"Bearer {self.aiml_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"], "🔶 AI/ML API (gpt-4o-mini)"
            except Exception:
                pass

        return f"Inference error (all providers failed): {gemini_err}", "❌ All Failed"

    # ── Capability 1: Multi-URL Scraping ────────────────────────────────────

    def scrape_multiple_urls(self, urls: list) -> tuple:
        """
        Scrape multiple URLs and merge into a unified RAG index.
        Returns: (merged_chunks, scrape_summary)
        """
        merged_chunks = []
        summary = []
        collection_id = "zeravane_multi_url"
        _error_prefixes = ("Error:", "ScraperAPI_Error:", "Fallback_Error:")

        for url in urls:
            url = url.strip()
            if not url:
                continue
            raw, method = self.scrape_live_url(url)
            ok = (
                raw
                and len(raw) >= self.MIN_TEXT_LENGTH
                and not any(raw.startswith(p) for p in _error_prefixes)
            )
            if ok:
                labeled = f"[SOURCE: {url}]\n{raw}"
                chunks = self.chunk_text(labeled)
                merged_chunks.extend(chunks)
                summary.append(f"✅ {url} — {method}")
            else:
                summary.append(f"❌ {url} — Failed: {raw[:80]}")

        if merged_chunks:
            self.refresh_vector_index(collection_name=collection_id, text_chunks=merged_chunks)
            self._cached_url = "__multi__"
            self._cached_collection = collection_id

        return merged_chunks, "\n".join(summary)

    # ── Capability 2: GitHub Repo Analyzer ──────────────────────────────────

    def analyze_github_repo(self, github_url: str) -> tuple:
        """
        Analyze a public GitHub repository via the GitHub API.
        Fetches README, file tree, and repo metadata.
        Returns: (repo_content, metadata_dict)
        """
        try:
            match = re.search(r"github\.com/([^/]+)/([^/?\s#]+)", github_url)
            if not match:
                return "Invalid GitHub URL format.", {}

            owner, repo = match.group(1), match.group(2).rstrip("/")
            api_base = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "ZeravaneAI"}

            meta_resp = requests.get(api_base, headers=headers, timeout=15)
            metadata = {}
            if meta_resp.status_code == 200:
                meta = meta_resp.json()
                metadata = {
                    "name": meta.get("full_name", ""),
                    "description": meta.get("description", "No description"),
                    "language": meta.get("language", "Unknown"),
                    "stars": meta.get("stargazers_count", 0),
                    "forks": meta.get("forks_count", 0),
                    "topics": meta.get("topics", []),
                    "default_branch": meta.get("default_branch", "main"),
                }

            branch = metadata.get("default_branch", "main")

            readme_content = ""
            readme_resp = requests.get(
                f"{api_base}/readme",
                headers={**headers, "Accept": "application/vnd.github.v3.raw"},
                timeout=15,
            )
            if readme_resp.status_code == 200:
                readme_content = readme_resp.text[:8000]

            tree_content = ""
            tree_resp = requests.get(
                f"{api_base}/git/trees/{branch}?recursive=0",
                headers=headers,
                timeout=15,
            )
            if tree_resp.status_code == 200:
                tree_data = tree_resp.json().get("tree", [])
                files = [item["path"] for item in tree_data if item["type"] == "blob"][:50]
                tree_content = "\n".join(files)

            combined = (
                f"=== GITHUB REPO: {owner}/{repo} ===\n"
                f"Description: {metadata.get('description', 'N/A')}\n"
                f"Primary Language: {metadata.get('language', 'N/A')}\n"
                f"Stars: {metadata.get('stars', 0)} | Forks: {metadata.get('forks', 0)}\n"
                f"Topics: {', '.join(metadata.get('topics', []))}\n\n"
                f"=== README ===\n{readme_content}\n\n"
                f"=== FILE TREE (top-level) ===\n{tree_content}\n"
            )

            collection_id = "zeravane_github"
            chunks = self.chunk_text(combined)
            self.refresh_vector_index(collection_name=collection_id, text_chunks=chunks)
            self._cached_url = github_url
            self._cached_collection = collection_id

            return combined, metadata

        except Exception as e:
            return f"GitHub_Error: {str(e)}", {}

    # ── Capability 3: Tech Stack Detection ──────────────────────────────────

    def detect_tech_stack(self, scraped_content: str, target_url: str = "") -> str:
        """
        Analyze scraped content to detect the technology stack.
        Returns: formatted tech stack report.
        """
        if not scraped_content or len(scraped_content) < 50:
            return "Insufficient content to detect tech stack."

        system_instruction = (
            "You are ZeravaneAI's tech stack detection engine. "
            "Analyze the provided web content and identify the technology stack. "
            "Look for clues in: meta tags, script imports, CSS class naming conventions, "
            "API response formats, error messages, framework-specific patterns, "
            "CDN URLs, build tool artifacts, and any visible text. "
            "Structure your response as: "
            "Frontend | Backend | Database | Deployment | Language | Styling | Other Tools. "
            "Rate your confidence (High/Medium/Low) for each detected technology. "
            "Be precise — only list what you can confidently infer from the content."
        )

        prompt = (
            f"Target URL: {target_url if target_url else 'Not provided'}\n\n"
            f"=== SCRAPED CONTENT (first 4000 chars) ===\n"
            f"{scraped_content[:4000]}\n\n"
            f"Detect and report the complete technology stack."
        )

        result, _ = self._infer(system_instruction, prompt)
        return result

    # ── Capability 4: Code Generation from Docs ─────────────────────────────

    def generate_code_from_docs(
        self, docs_url: str, generation_request: str, language: str = "Python"
    ) -> tuple:
        """
        Scrape live documentation and generate production-ready boilerplate code.
        Returns: (generated_code, scrape_method, model_used)
        """
        _error_prefixes = ("Error:", "ScraperAPI_Error:", "Fallback_Error:")
        raw_docs, scrape_method = self.scrape_live_url(docs_url)
        scrape_ok = (
            raw_docs
            and len(raw_docs) >= self.MIN_TEXT_LENGTH
            and not any(raw_docs.startswith(p) for p in _error_prefixes)
        )

        if scrape_ok:
            collection_id = "zeravane_codegen"
            chunks = self.chunk_text(raw_docs)
            self.refresh_vector_index(collection_name=collection_id, text_chunks=chunks)
            context = self.query_vector_context(
                collection_name=collection_id, query=generation_request, n_results=4
            )
        else:
            context = f"[Scraping failed: {raw_docs[:100]}]"

        system_instruction = (
            f"You are ZeravaneAI's code generation engine. "
            f"Generate production-ready {language} code based on the provided documentation. "
            f"Follow best practices, include proper error handling, add clear comments, "
            f"and structure the code for real-world use. "
            f"If documentation context is available, base your code strictly on it. "
            f"Return ONLY clean, runnable code with brief inline comments. "
            f"Include a short usage example at the end."
        )

        prompt = (
            f"Documentation Source: {docs_url}\n"
            f"Target Language: {language}\n"
            f"Generation Request: {generation_request}\n\n"
            f"=== LIVE DOCUMENTATION CONTEXT ===\n"
            f"{context}\n\n"
            f"Generate the requested {language} code now."
        )

        code, model_used = self._infer(system_instruction, prompt)
        return code, scrape_method, model_used

    # ── Main RAG pipeline ───────────────────────────────────────────────────

    def execute_live_agent_query(
        self, user_query: str, target_url: str = None, force_rescrape: bool = False
    ) -> tuple:
        """
        Full RAG pipeline with ScraperAPI web intelligence + 3-tier LLM fallback.
        Returns: (response_text, context_payload, scrape_method, model_used)
        """
        context_payload = ""
        collection_id = self._cached_collection
        scrape_method = "N/A"
        _error_prefixes = ("Error:", "ScraperAPI_Error:", "Fallback_Error:")

        if target_url:
            url_changed = target_url != self._cached_url

            if url_changed or force_rescrape:
                raw_web_data, scrape_method = self.scrape_live_url(target_url)
                scrape_ok = (
                    raw_web_data
                    and len(raw_web_data) >= self.MIN_TEXT_LENGTH
                    and not any(raw_web_data.startswith(p) for p in _error_prefixes)
                )

                if scrape_ok:
                    data_chunks = self.chunk_text(raw_web_data)
                    indexed = self.refresh_vector_index(
                        collection_name=collection_id, text_chunks=data_chunks
                    )
                    if indexed:
                        self._cached_url = target_url
                        context_payload = self.query_vector_context(
                            collection_name=collection_id, query=user_query
                        )
                    else:
                        context_payload = "[Indexing Error: Could not build vector index]"
                else:
                    context_payload = f"[Scraping Warning: {raw_web_data}]"
            else:
                scrape_method = "✅ Cache Hit (URL unchanged)"
                context_payload = self.query_vector_context(
                    collection_name=collection_id, query=user_query
                )

        web_context_available = (
            target_url
            and context_payload
            and not context_payload.startswith("[")
        )

        if web_context_available:
            system_instruction = (
                "You are ZeravaneAI, an advanced real-time web-aware developer agent. "
                "Analyze the live web documentation data provided to solve the user's problem "
                "with precision. Prioritize live context over training data. Provide clean, "
                "production-ready code solutions and detailed explanations. "
                "Always cite when your answer draws from the provided documentation."
            )
        elif target_url:
            system_instruction = (
                f"You are ZeravaneAI, an advanced real-time web-aware developer agent. "
                f"The user has provided this URL: {target_url}. "
                f"Live web scraping was attempted but could not retrieve content. "
                f"You are now in Offline Core Mode — answer using your training knowledge "
                f"about this URL, domain, library, or framework if available. "
                f"Be transparent about whether your answer comes from live data or training knowledge."
            )
        else:
            system_instruction = (
                "You are ZeravaneAI, a premium core programming assistant with deep knowledge "
                "across all major languages, frameworks, and architectures. Provide expert-level "
                "solutions, best-practice guidance, and thoroughly tested code patterns."
            )

        fallback_context = (
            f"Scraping unavailable for {target_url}. Answer using training knowledge."
            if target_url else "No web documentation retrieved."
        )
        prompt_structure = (
            f"--- SYSTEM OVERVIEW ---\n"
            f"ScraperAPI Integration: {'Active' if self.scraper_enabled else 'Demo Mode'}\n"
            f"Scrape Method: {scrape_method}\n"
            f"Target URL: {target_url if target_url else 'None'}\n"
            f"Context Available: {'Yes' if web_context_available else 'No'}\n\n"
            f"--- LIVE WEB DOCUMENTATION ---\n"
            f"{context_payload if context_payload else fallback_context}\n\n"
            f"--- DEVELOPER QUERY ---\n"
            f"{user_query}\n"
        )

        response_text, model_used = self._infer(system_instruction, prompt_structure)
        return response_text, context_payload, scrape_method, model_used
