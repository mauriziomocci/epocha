"""Extract text from multiple document formats for Express world generation.

Supports PDF (via PyMuPDF), DOCX (via python-docx), Markdown, and plain text.
Used by the Express endpoint to allow users to upload documents as world seeds.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".doc", ".docx"}


def extract_text(file_path: str) -> str:
    """Extract text content from a document file.

    Args:
        file_path: Absolute path to the document file.

    Returns:
        Extracted text content as a string.

    Raises:
        ValueError: If the file format is not supported.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8")

    if ext == ".pdf":
        return _extract_pdf(path)

    if ext in (".doc", ".docx"):
        return _extract_docx(path)

    raise ValueError(f"Unsupported file format: {ext}")


def _extract_pdf(path: Path) -> str:
    """Extract text from PDF using PyMuPDF (fitz)."""
    import fitz

    doc = fitz.open(str(path))
    text_parts = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(text_parts).strip()


def _extract_docx(path: Path) -> str:
    """Extract text from DOCX using python-docx."""
    from docx import Document

    doc = Document(str(path))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
