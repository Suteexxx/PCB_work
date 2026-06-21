"""
Datasheet ingestion pipeline.

Walks a directory of PDFs, extracts text, chunks it, and indexes it into
ChromaDB. Designed to be run via scripts/ingest_datasheets.py, and also
exposed as a service function so the API can offer a re-ingest endpoint.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.knowledge_base.pdf_extractor import extract_pdf_text
from app.services.knowledge_base.vector_store import add_chunks
from app.utils.text_processing import chunk_by_words
from app.utils.url_utils import make_id

log = get_logger("kb_ingestion")


def ingest_directory(pdf_dir: Path | None = None) -> dict:
    """
    Ingest every .pdf file in `pdf_dir` (default: settings.sample_datasheets_dir)
    into the vector store. Returns a summary dict: files_ingested, chunks_indexed, skipped.
    """
    settings = get_settings()
    pdf_dir = pdf_dir or settings.sample_datasheets_dir
    pdf_dir = Path(pdf_dir)

    if not pdf_dir.exists():
        log.warning(f"PDF directory does not exist: {pdf_dir}")
        return {"files_ingested": 0, "chunks_indexed": 0, "skipped": []}

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        log.warning(f"No PDFs found in {pdf_dir}")
        return {"files_ingested": 0, "chunks_indexed": 0, "skipped": []}

    files_ingested = 0
    total_chunks = 0
    skipped = []

    for pdf_path in pdf_files:
        log.info(f"Ingesting {pdf_path.name}...")
        extracted = extract_pdf_text(pdf_path)

        if not extracted.success:
            log.warning(f"Skipping {pdf_path.name}: {extracted.error}")
            skipped.append(f"{pdf_path.name} ({extracted.error})")
            continue

        chunks = chunk_by_words(
            extracted.full_text,
            chunk_size=settings.kb_chunk_size_words,
            overlap=settings.kb_chunk_overlap_words,
        )
        if not chunks:
            skipped.append(f"{pdf_path.name} (no chunks produced)")
            continue

        chunk_ids = [make_id("kb", pdf_path.name, str(i)) for i in range(len(chunks))]
        metadatas = [
            {
                "file_name": extracted.file_name,
                "title": extracted.title,
                "chunk_index": i,
                "page_count": extracted.page_count,
            }
            for i in range(len(chunks))
        ]

        add_chunks(chunk_ids, chunks, metadatas)
        files_ingested += 1
        total_chunks += len(chunks)

    log.info(f"Ingestion complete: {files_ingested} files, {total_chunks} chunks, {len(skipped)} skipped")
    return {
        "files_ingested": files_ingested,
        "chunks_indexed": total_chunks,
        "skipped": skipped,
    }
