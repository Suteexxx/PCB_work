"""
Centralized application configuration.

All tunable parameters (model names, scraping limits, paths, thresholds)
live here so the rest of the codebase never hardcodes magic values.
Values can be overridden via environment variables or a .env file.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]  # backend/
DATA_DIR = BACKEND_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PCB_", extra="ignore")

    # --- App metadata ---
    app_name: str = "PCB Research Agent"
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]

    # --- Paths ---
    data_dir: Path = DATA_DIR
    chroma_kb_dir: Path = DATA_DIR / "chroma_kb"
    sample_datasheets_dir: Path = DATA_DIR / "sample_datasheets"
    cache_dir: Path = DATA_DIR / "cache"

    # --- Embedding model (shared by KB + web agent for consistent vector space) ---
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"

    # --- Keyword extraction ---
    keybert_top_n: int = 12
    keyword_ngram_range: tuple[int, int] = (1, 3)

    # --- Web search agent ---
    search_max_results: int = 10
    search_region: str = "wt-wt"
    search_safesearch: str = "moderate"
    scrape_timeout_seconds: float = 12.0
    scrape_max_concurrent: int = 6
    scrape_min_text_chars: int = 200
    scrape_max_chars_per_page: int = 20000
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 PCBResearchAgent/0.1"
    )

    # --- Sentence ranking / extractive summary ---
    top_sentences_per_source: int = 5
    max_sources_in_summary: int = 6
    sentence_min_words: int = 6
    similarity_threshold: float = 0.18  # cosine similarity floor to keep a sentence

    # --- Knowledge base (ChromaDB) ---
    kb_collection_name: str = "datasheet_kb"
    kb_chunk_size_words: int = 180
    kb_chunk_overlap_words: int = 30
    kb_top_k: int = 6

    # --- Web agent result cache ---
    cache_ttl_seconds: int = 60 * 60 * 6  # 6 hours

    # --- Component knowledge domains (used to expand/augment raw user queries) ---
    component_hint_terms: list[str] = [
        "datasheet",
        "application note",
        "design guide",
        "noise specifications",
        "circuit topology",
    ]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
