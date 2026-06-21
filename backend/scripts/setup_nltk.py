"""
Run once after installing requirements to pre-download NLTK's sentence
tokenizer data (punkt). The app also attempts this lazily on first use,
but running it explicitly avoids a delay/network call during your first
API request.

Usage:
    python scripts/setup_nltk.py
"""

import nltk

if __name__ == "__main__":
    for resource in ("punkt", "punkt_tab"):
        print(f"Downloading NLTK resource: {resource}")
        try:
            nltk.download(resource)
        except Exception as e:
            print(f"  (non-fatal) failed to download {resource}: {e}")
    print("Done.")
