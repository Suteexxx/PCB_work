#!/usr/bin/env bash
# One-command backend setup: venv, deps, NLTK data, sample datasheets, ingestion.
#
# Usage:
#   cd backend
#   ./setup.sh
set -euo pipefail

echo "=== PCB Research Agent — backend setup ==="

if [ ! -d ".venv" ]; then
    echo "[1/6] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/6] Virtual environment already exists, skipping."
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/6] Installing dependencies (this can take a few minutes, sentence-transformers pulls torch)..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "[3/6] Downloading NLTK sentence tokenizer data..."
python3 scripts/setup_nltk.py

echo "[4/6] Generating sample/dummy datasheet PDFs for testing..."
python3 scripts/generate_sample_datasheets.py

echo "[5/6] Ingesting sample datasheets into the knowledge base (downloads the embedding model on first run, ~80MB)..."
python3 scripts/ingest_datasheets.py --reset

echo "[6/6] Done."
echo ""
echo "Start the API server with:"
echo "  source .venv/bin/activate"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "Then in another terminal, start the frontend:"
echo "  cd ../frontend && pip install -r requirements.txt && streamlit run app.py"
