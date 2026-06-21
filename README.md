# PCB Design Research Agent

A hybrid research backend + frontend for PCB/circuit design automation.

You give it a free-form design prompt — e.g. *"design an ultra low noise
current source for 100mA using Libbrecht-Hall topology, zero-drift opamps,
ultra-precision resistors, single DC supply input, adjustable via
potentiometer"* — and it:

1. **Decomposes the prompt** into the distinct components/topologies it
   actually involves (Howland current pump, zero-drift op-amp, precision
   resistors, LDOs, noise analysis, etc).
2. **Researches each one** against:
   - a **local knowledge base** of your own datasheets (ChromaDB + embeddings), and
   - a **live web research agent** (DuckDuckGo search → scrape → rank → keyword-extract),
3. **Returns a structured, citable answer** — extractive snippets (verbatim
   sentences, never generated/hallucinated) each tagged with its source
   link, plus marked keywords per topic. The "Claude/ChatGPT-style search"
   feel, built entirely from free/local components — **no LLM API calls,
   no API key required.**

This is stage 1 of a larger pipeline. A later "topological engine" stage
(schematic generation) is intentionally out of scope here — this repo
covers prompt → research only, with a clean API boundary for that next
stage to plug into.

---

## Architecture

```
                    ┌─────────────────────┐
                    │   Streamlit (UI)     │
                    │   frontend/app.py    │
                    └──────────┬───────────┘
                               │ POST /api/v1/research
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI (API)      │
                    │   backend/app/main.py│
                    └──────────┬───────────┘
                               ▼
                ┌──────────────────────────────┐
                │   Hybrid Pipeline             │
                │   services/hybrid_pipeline.py │
                └───────┬──────────────┬────────┘
                        ▼              ▼
        ┌───────────────────────┐  ┌───────────────────────────┐
        │  Topic Extraction      │  │  (runs per detected topic) │
        │  (gazetteer + KeyBERT) │  └───────────────────────────┘
        └───────────┬───────────┘
                     │ topics[]
          ┌──────────┴───────────┐
          ▼                      ▼
┌───────────────────┐   ┌──────────────────────┐
│  Web Research Agent │   │  Knowledge Base (KB)  │
│  ─────────────────  │   │  ────────────────────  │
│  DuckDuckGo search   │   │  ChromaDB (persistent) │
│  → async scraping    │   │  PDF datasheets →      │
│    (httpx+trafilatura)│   │  chunked + embedded    │
│  → sentence ranking  │   │  → semantic search      │
│    (embeddings)      │   └──────────────────────┘
│  → KeyBERT keywords  │
│  → disk cache (TTL)  │
└───────────────────┘
          │                      │
          └──────────┬───────────┘
                      ▼
          merged ComponentTopicResult
          per topic (sources + citable
          snippets + keywords)
```

Both the KB and the web agent embed text with the **same**
SentenceTransformer model (`all-MiniLM-L6-v2` by default), so their
relevance scores live in a comparable vector space and can be merged
meaningfully per topic.

Everything is **extractive, not generative** — every sentence returned
is verbatim from a real source with a working link/file reference. There
is no LLM in the loop, so there's nothing to hallucinate.

---

## Folder structure

```
pcb-research-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI app entrypoint, CORS, lifespan
│   │   ├── api/
│   │   │   └── routers/
│   │   │       ├── research.py            # POST /api/v1/research
│   │   │       └── knowledge_base.py      # GET /kb/health, POST /kb/ingest
│   │   ├── core/
│   │   │   ├── config.py                  # Centralized Settings (env-overridable)
│   │   │   ├── logging.py                 # loguru setup
│   │   │   └── embeddings.py              # Shared SentenceTransformer singleton
│   │   ├── models/
│   │   │   └── schemas.py                 # Pydantic request/response contracts
│   │   ├── services/
│   │   │   ├── hybrid_pipeline.py         # Top-level orchestrator (merges KB+web)
│   │   │   ├── web_agent/
│   │   │   │   ├── topic_extraction.py    # Gazetteer + KeyBERT topic detection
│   │   │   │   ├── search_client.py       # DuckDuckGo wrapper (retry/backoff)
│   │   │   │   ├── scraper.py             # Async httpx + trafilatura scraping
│   │   │   │   ├── sentence_ranker.py     # Embedding-based extractive ranking
│   │   │   │   ├── keyword_extractor.py   # KeyBERT keyword marking
│   │   │   │   ├── cache.py               # TTL disk cache for search results
│   │   │   │   └── research_orchestrator.py  # Ties the above together per topic
│   │   │   └── knowledge_base/
│   │   │       ├── pdf_extractor.py       # pypdf text extraction
│   │   │       ├── vector_store.py        # ChromaDB wrapper
│   │   │       ├── ingestion.py           # PDF → chunks → vector store
│   │   │       └── kb_query_service.py    # KB semantic search → schema objects
│   │   └── utils/
│   │       ├── text_processing.py         # sentence split, chunking, cleaning
│   │       └── url_utils.py               # domain extraction, ID hashing
│   ├── data/
│   │   ├── sample_datasheets/             # 3 synthetic test PDFs (generated)
│   │   ├── chroma_kb/                     # ChromaDB persistent storage (gitignored)
│   │   └── cache/                         # Web search TTL cache (gitignored)
│   ├── scripts/
│   │   ├── setup_nltk.py                  # Pre-download sentence tokenizer data
│   │   ├── generate_sample_datasheets.py  # Builds the 3 synthetic test PDFs
│   │   └── ingest_datasheets.py           # CLI: PDF dir → vector store
│   ├── tests/                             # pytest suite (25 tests, see below)
│   ├── requirements.txt
│   ├── setup.sh                           # one-command setup
│   └── .env.example
├── frontend/
│   ├── app.py                             # Streamlit UI
│   ├── config.py                          # Backend URL + example prompt
│   └── requirements.txt
├── .gitignore
└── README.md                              # you are here
```

---

## Setup

### Backend

```bash
cd backend
./setup.sh
```

This creates a venv, installs dependencies, downloads NLTK data, generates
3 synthetic sample datasheets (a zero-drift op-amp, an ultra-precision
resistor, and a low-noise LDO — written for this repo since real
manufacturer datasheets are copyrighted), and ingests them into the local
ChromaDB knowledge base. The **first run downloads the embedding model**
(~80MB, from huggingface.co) — this requires normal internet access.

Then run the API:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs.

### Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Visit `http://localhost:8501`. By default it talks to the backend at
`http://localhost:8000` — override with the `PCB_BACKEND_URL` env var if
your backend runs elsewhere.

### Adding your own datasheets

Drop PDFs into `backend/data/sample_datasheets/` (or point `--dir` at any
folder) and re-run:

```bash
python scripts/ingest_datasheets.py
```

Use `--reset` to wipe and rebuild the collection (e.g. after changing
chunk size in `.env`).

---

## API

### `POST /api/v1/research`

```json
{
  "query": "design an ultra low noise current source for 100mA using Libbrecht-Hall topology...",
  "include_web": true,
  "include_kb": true,
  "max_web_results": 8
}
```

Returns a `ResearchResponse`: detected topics, global keywords, and for
each topic a `ComponentTopicResult` containing ranked keywords, citable
extractive snippets (each with a `relevance_score` and `source_id`), and
the full source list (web URLs and/or local KB filenames). See
`backend/app/models/schemas.py` for the full contract — it's also visible
live at `/docs`.

### `GET /api/v1/kb/health`
Embedding model name + number of documents currently indexed.

### `POST /api/v1/kb/ingest?reset=false`
Re-run ingestion over `data/sample_datasheets/` without restarting the server.

---

## Why this design

- **No LLM API / no API key** — the "marks keywords, delivers output with
  links" behavior is built from KeyBERT (keyword extraction) +
  sentence-embedding cosine-similarity ranking (extractive "summarization")
  rather than text generation. This means **zero hallucination risk** —
  every claim in the output is a verbatim, source-linked sentence — and
  zero per-query API cost.
- **Gazetteer-first topic extraction** — a curated regex gazetteer
  (`topic_extraction.py`) catches known EE components/topologies
  (Howland/Libbrecht-Hall, zero-drift op-amps, LDOs, etc.) with full
  explainability, falling back to KeyBERT noun-phrase extraction for
  anything not in the list. This was validated directly against the exact
  example prompt in this project's spec (see `tests/test_topic_extraction.py`).
- **Shared embedding space** — KB and web-agent results are embedded with
  the same model so their relevance scores can be merged into one ranked
  list per topic, not just concatenated.
- **Layered, swappable services** — `search_client.py`, `scraper.py`, and
  `vector_store.py` are all thin, single-purpose wrappers. Swapping
  DuckDuckGo for a paid SERP API, or Chroma for another vector DB, touches
  one file each.

---

## Testing

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

25 tests covering text processing, the topic-extraction gazetteer (incl. a
regression test against this project's exact example prompt), the hybrid
API contract, and the web research orchestrator (search/scrape mocked so
these run without network access). A couple of orchestrator tests that
specifically exercise live embedding/keyword extraction are marked
`requires_model` and auto-skip if the embedding model isn't downloadable
in your environment.

---

## Known limitations / next steps

- **Scanned/image-only PDFs** aren't OCR'd — `pdf_extractor.py` uses
  `pypdf` text extraction only. Add an OCR fallback (e.g. `pytesseract`)
  if you need to ingest scanned datasheets.
- **DuckDuckGo rate limits** — `search_client.py` retries with backoff,
  but heavy concurrent usage may still get throttled. The TTL disk cache
  (`cache.py`) mitigates repeated identical queries during development.
- **Topology/schematic generation** is explicitly out of scope here —
  this repo's job ends at structured, citable research output per
  component. The next stage (a topological engine that turns these
  research results into an actual schematic) can consume
  `ResearchResponse.results_by_topic` as its input.
