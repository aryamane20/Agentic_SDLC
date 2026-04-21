"""POST /reports/extract-document — file type, size, and content validation."""

from io import BytesIO
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)

_5MB_PLUS_1 = b"x" * (5 * 1024 * 1024 + 1)


def _upload(content: bytes, filename: str, content_type: str = "application/octet-stream"):
    return client.post(
        "/reports/extract-document",
        files={"file": (filename, BytesIO(content), content_type)},
    )


# ---------------------------------------------------------------------------
# Supported plain-text types
# ---------------------------------------------------------------------------

def test_txt_upload_returns_200():
    resp = _upload(b"Hello world project brief.", "brief.txt", "text/plain")
    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello world project brief."


def test_md_upload_returns_200():
    resp = _upload(b"# Brief\nBuild a dashboard.", "brief.md", "text/markdown")
    assert resp.status_code == 200
    assert "Brief" in resp.json()["text"]


# ---------------------------------------------------------------------------
# PDF (mocked)
# ---------------------------------------------------------------------------

def test_pdf_upload_returns_200():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "PDF extracted text"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    # PdfReader is imported inside the endpoint function; patch at the package level.
    with patch("pypdf.PdfReader", return_value=mock_reader):
        resp = _upload(b"%PDF-1.4 fake", "brief.pdf", "application/pdf")

    assert resp.status_code == 200
    assert resp.json()["text"] == "PDF extracted text"


# ---------------------------------------------------------------------------
# DOCX (mocked)
# ---------------------------------------------------------------------------

def test_docx_upload_returns_200():
    mock_para = MagicMock()
    mock_para.text = "DOCX paragraph text"
    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_para]

    # Document is imported inside the endpoint function; patch at the package level.
    with patch("docx.Document", return_value=mock_doc):
        resp = _upload(b"PK\x03\x04fake", "brief.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    assert resp.status_code == 200
    assert resp.json()["text"] == "DOCX paragraph text"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_oversized_file_returns_413():
    resp = _upload(_5MB_PLUS_1, "big.txt", "text/plain")
    assert resp.status_code == 413


def test_empty_file_returns_422():
    resp = _upload(b"", "empty.txt", "text/plain")
    assert resp.status_code == 422


def test_unsupported_extension_returns_400():
    resp = _upload(b"\x7fELF", "malware.exe", "application/octet-stream")
    assert resp.status_code == 400
