from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extrair_texto_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def extrair_texto_docx(path: Path) -> str:
    document = Document(str(path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return "\n".join(paragraphs).strip()


def extrair_texto(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extrair_texto_pdf(path)
    if suffix == ".docx":
        return extrair_texto_docx(path)
    raise ValueError("Formato nao suportado. Envie PDF ou DOCX.")
