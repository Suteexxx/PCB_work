"""
CLI entrypoint for ingesting PDF datasheets into the local ChromaDB
knowledge base.

Usage:
    python scripts/ingest_datasheets.py                  # ingest default dir
    python scripts/ingest_datasheets.py --reset           # wipe + re-ingest
    python scripts/ingest_datasheets.py --dir /path/to/pdfs

Run this any time you drop new datasheet PDFs into
backend/data/sample_datasheets/ (or your own custom directory).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable

from app.services.knowledge_base.ingestion import ingest_directory  # noqa: E402
from app.services.knowledge_base.vector_store import reset_kb  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Ingest PDF datasheets into the knowledge base.")
    parser.add_argument("--dir", type=str, default=None, help="Directory of PDFs to ingest")
    parser.add_argument("--reset", action="store_true", help="Wipe the KB collection before ingesting")
    args = parser.parse_args()

    if args.reset:
        print("Resetting KB collection...")
        reset_kb()

    pdf_dir = Path(args.dir) if args.dir else None
    result = ingest_directory(pdf_dir)

    print("\n--- Ingestion Summary ---")
    print(f"Files ingested:  {result['files_ingested']}")
    print(f"Chunks indexed:  {result['chunks_indexed']}")
    if result["skipped"]:
        print(f"Skipped ({len(result['skipped'])}):")
        for s in result["skipped"]:
            print(f"  - {s}")


if __name__ == "__main__":
    main()
