"""
PDF text extraction for datasheet ingestion.

Uses pypdf (pure-python, no system deps) to extract per-page text. Good
enough for text-based datasheets; scanned/image-only PDFs would need OCR
(out of scope for v1 -- noted in README as a future extension).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.core.logging import get_logger
from app.utils.text_processing import clean_text

log = get_logger("pdf_extractor")


@dataclass
class ExtractedPdf:
    file_name: str
    title: str
    full_text: str
    page_count: int
    success: bool
    error: str | None = None


def extract_pdf_text(pdf_path: Path) -> ExtractedPdf:
    """Extract and concatenate all page text from a PDF file."""
    try:
        reader = PdfReader(str(pdf_path))
        pages_text = []
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception as page_err:
                log.warning(f"Failed to extract a page from {pdf_path.name}: {page_err}")

        full_text = clean_text("\n".join(pages_text))

        meta_title = None
        try:
            raw_title = reader.metadata.title if reader.metadata else None
            # Some PDF producers (reportlab included) leave literal placeholder
            # strings like "(anonymous)" or "(unspecified)" when no title was
            # explicitly set -- treat those as absent rather than using them.
            if raw_title and not raw_title.strip().startswith("("):
                meta_title = raw_title.strip()
        except Exception:
            pass

        title = meta_title or pdf_path.stem.replace("_", " ").replace("-", " ")

        if not full_text or len(full_text) < 50:
            return ExtractedPdf(pdf_path.name, title, "", len(reader.pages), False, "no extractable text (scanned PDF?)")

        return ExtractedPdf(pdf_path.name, title, full_text, len(reader.pages), True, None)

    except Exception as e:
        log.error(f"Failed to read PDF {pdf_path}: {e}")
        return ExtractedPdf(pdf_path.name, pdf_path.stem, "", 0, False, str(e)[:200])
