"""
PCB Design Research Agent — Streamlit frontend.

Takes a free-form circuit/PCB design prompt, sends it to the FastAPI
backend's hybrid research pipeline (local datasheet KB + live web agent),
and renders the structured, citable results: per-component keywords,
extractive summaries with source links, and a full source list.

Run with:
    streamlit run app.py
(from the frontend/ directory)
"""

from __future__ import annotations

import requests
import streamlit as st

from config import (
    EXAMPLE_QUERY,
    KB_HEALTH_ENDPOINT,
    REQUEST_TIMEOUT_SECONDS,
    RESEARCH_ENDPOINT,
)

st.set_page_config(
    page_title="PCB Design Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------- #
# Minimal custom styling — engineering/lab feel: monospace accents for
# technical values, a calm slate palette, tight info-dense cards rather than
# marketing-style whitespace.
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    .stApp { background-color: #0f1419; }
    .topic-card {
        background-color: #1a2129;
        border: 1px solid #2a3441;
        border-radius: 8px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 1rem;
    }
    .topic-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #7ee7c7;
        margin-bottom: 0.4rem;
        font-family: 'Courier New', monospace;
    }
    .keyword-chip {
        display: inline-block;
        background-color: #233140;
        color: #9fd3ff;
        border-radius: 4px;
        padding: 0.15rem 0.55rem;
        margin: 0.15rem 0.25rem 0.15rem 0;
        font-size: 0.78rem;
        font-family: 'Courier New', monospace;
    }
    .snippet-block {
        border-left: 2px solid #3a4a5a;
        padding-left: 0.8rem;
        margin: 0.6rem 0;
        font-size: 0.92rem;
        color: #d7dde3;
    }
    .source-link {
        font-size: 0.78rem;
        color: #7ee7c7;
    }
    .score-badge {
        font-family: 'Courier New', monospace;
        font-size: 0.72rem;
        color: #6b7785;
    }
    .source-type-kb {
        color: #ffb86c;
        font-size: 0.72rem;
        font-family: 'Courier New', monospace;
    }
    .source-type-web {
        color: #8be9fd;
        font-size: 0.72rem;
        font-family: 'Courier New', monospace;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Sidebar: settings + backend status
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    include_web = st.checkbox("Include live web research", value=True)
    include_kb = st.checkbox("Include local datasheet KB", value=True)
    max_results = st.slider("Max web results per topic", min_value=3, max_value=15, value=8)

    st.markdown("---")
    st.markdown("### 🩺 Backend status")
    try:
        health_resp = requests.get(KB_HEALTH_ENDPOINT, timeout=5)
        if health_resp.ok:
            health = health_resp.json()
            st.success("Backend reachable")
            st.caption(f"Embedding model: `{health['embedding_model']}`")
            st.caption(f"KB documents indexed: **{health['kb_documents_indexed']}**")
            if health["kb_documents_indexed"] == 0:
                st.warning(
                    "Knowledge base is empty. Run:\n\n"
                    "`python scripts/generate_sample_datasheets.py`\n\n"
                    "`python scripts/ingest_datasheets.py`",
                    icon="📂",
                )
        else:
            st.error(f"Backend returned {health_resp.status_code}")
    except requests.exceptions.RequestException:
        st.error("Cannot reach backend. Is it running on port 8000?")
        st.caption("Start it with: `uvicorn app.main:app --reload --port 8000`")

    st.markdown("---")
    st.caption(
        "This tool decomposes your design prompt into component/topology "
        "topics, then researches each one against your local datasheet "
        "library and the live web — fully local, no LLM API calls."
    )


# --------------------------------------------------------------------------- #
# Main: query input
# --------------------------------------------------------------------------- #
st.title("🔬 PCB Design Research Agent")
st.caption(
    "Describe the circuit you want to design. The agent will identify the key "
    "components/topologies involved and gather grounded, source-linked research "
    "on each — the first stage of the design automation pipeline."
)

with st.form("research_form"):
    query = st.text_area(
        "Design prompt",
        value=st.session_state.get("query_text", ""),
        height=150,
        placeholder=EXAMPLE_QUERY,
    )
    col1, col2 = st.columns([1, 5])
    with col1:
        submitted = st.form_submit_button("🔍 Research", use_container_width=True)
    with col2:
        use_example = st.form_submit_button("Use example prompt")

if use_example:
    st.session_state["query_text"] = EXAMPLE_QUERY
    st.rerun()

if submitted:
    if not query or len(query.strip()) < 8:
        st.error("Please enter a more detailed design prompt (at least a sentence).")
    else:
        payload = {
            "query": query.strip(),
            "include_web": include_web,
            "include_kb": include_kb,
            "max_web_results": max_results,
        }
        with st.spinner("Researching components and topologies — this can take 20-90s for web sources..."):
            try:
                resp = requests.post(RESEARCH_ENDPOINT, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {e}")
                resp = None

        if resp is not None:
            if not resp.ok:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                st.error(f"Backend error ({resp.status_code}): {detail}")
            else:
                st.session_state["last_result"] = resp.json()


# --------------------------------------------------------------------------- #
# Results rendering
# --------------------------------------------------------------------------- #
result = st.session_state.get("last_result")

if result:
    st.markdown("---")

    # Warnings banner (e.g. empty KB, web disabled)
    for w in result.get("warnings", []):
        st.info(w, icon="ℹ️")

    # Timing + topic overview
    timing = result.get("timing_ms", {})
    meta_cols = st.columns(4)
    meta_cols[0].metric("Topics detected", len(result["detected_topics"]))
    meta_cols[1].metric("Sources found", len(result["all_sources"]))
    meta_cols[2].metric("Web research time", f"{timing.get('web_research_ms', 0):.0f} ms")
    meta_cols[3].metric("Total time", f"{timing.get('total_ms', 0):.0f} ms")

    # Global keywords
    if result.get("global_keywords"):
        st.markdown("#### 🏷️ Global keywords (from your query)")
        chips = "".join(
            f'<span class="keyword-chip">{kw["keyword"]} ({kw["score"]:.2f})</span>'
            for kw in result["global_keywords"]
        )
        st.markdown(chips, unsafe_allow_html=True)

    st.markdown("#### 📚 Research by component / topic")

    for topic_result in result["results_by_topic"]:
        with st.container():
            st.markdown(
                f'<div class="topic-card"><div class="topic-title">▸ {topic_result["topic"]}</div>',
                unsafe_allow_html=True,
            )

            if topic_result.get("keywords"):
                chips = "".join(
                    f'<span class="keyword-chip">{kw["keyword"]}</span>'
                    for kw in topic_result["keywords"][:10]
                )
                st.markdown(chips, unsafe_allow_html=True)

            # Build a quick source_id -> source lookup for this topic
            src_map = {s["id"]: s for s in topic_result["sources"]}

            if topic_result.get("extractive_summary"):
                st.markdown("**Key findings:**")
                for snippet in topic_result["extractive_summary"][:8]:
                    src = src_map.get(snippet["source_id"])
                    src_label = ""
                    if src:
                        if src["source_type"] == "knowledge_base":
                            src_label = f'<span class="source-type-kb">[KB] {src.get("file_name", "")}</span>'
                        else:
                            src_label = f'<span class="source-type-web">[WEB] <a class="source-link" href="{src.get("url","#")}" target="_blank">{src.get("domain","")}</a></span>'
                    st.markdown(
                        f'<div class="snippet-block">{snippet["text"]} '
                        f'<span class="score-badge">(relevance {snippet["relevance_score"]:.2f})</span><br>{src_label}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No relevant snippets found for this topic.")

            if topic_result.get("sources"):
                with st.expander(f"All {len(topic_result['sources'])} sources for this topic"):
                    for src in topic_result["sources"]:
                        if src["source_type"] == "web":
                            st.markdown(f"- 🌐 [{src['title']}]({src['url']}) — `{src['domain']}`")
                        else:
                            st.markdown(f"- 📄 **{src['title']}** — `{src.get('file_name','')}` (local KB)")

            st.markdown("</div>", unsafe_allow_html=True)

    # Full source bibliography
    with st.expander(f"📎 Full source bibliography ({len(result['all_sources'])} sources)"):
        for src in result["all_sources"]:
            if src["source_type"] == "web":
                st.markdown(f"- 🌐 [{src['title']}]({src['url']}) — `{src['domain']}`")
            else:
                st.markdown(f"- 📄 **{src['title']}** — `{src.get('file_name','')}` (local KB)")

    with st.expander("🔧 Raw JSON response"):
        st.json(result)
else:
    st.info(
        "Enter a design prompt above and click **Research** to get started, "
        "or click **Use example prompt** to try the sample current-source query.",
        icon="👆",
    )
