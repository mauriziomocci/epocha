"""Tests for multi-format document text extraction."""
import tempfile

import pytest

from epocha.apps.world.document_parser import extract_text


class TestExtractText:
    def test_extract_from_txt(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("A medieval village with 30 people and a corrupt priest.")
            f.flush()
            result = extract_text(f.name)
        assert "medieval village" in result

    def test_extract_from_md(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# World Setup\n\nA futuristic city with AI governance.")
            f.flush()
            result = extract_text(f.name)
        assert "futuristic city" in result

    def test_extract_from_pdf(self):
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "The Roman Empire in 100 AD under Trajan.")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            doc.save(f.name)
            doc.close()
            result = extract_text(f.name)
        assert "Roman Empire" in result

    def test_extract_from_docx(self):
        from docx import Document

        doc = Document()
        doc.add_paragraph("An island nation discovers a massive energy source.")
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            doc.save(f.name)
            result = extract_text(f.name)
        assert "island nation" in result

    def test_unsupported_format_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"some data")
            f.flush()
            with pytest.raises(ValueError, match="Unsupported"):
                extract_text(f.name)

    def test_empty_txt_returns_empty_string(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("")
            f.flush()
            result = extract_text(f.name)
        assert result == ""
