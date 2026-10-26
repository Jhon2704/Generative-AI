"""
Extractor de texto para archivos PDF, Word y TXT.
Funciona completamente en local — no requiere APIs externas.
Compatible con Ollama/Mistral y cualquier LLM local.
"""
from __future__ import annotations

import io


# Límite de caracteres para no saturar el contexto de modelos locales
MAX_CHARS = 12_000


async def extract_text(filename: str, data: bytes) -> str:
    """
    Extrae el texto de un archivo según su extensión.
    Devuelve string vacío si el formato no es soportado.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        if ext == "pdf":
            return _extract_pdf(data)
        elif ext in ("docx",):
            return _extract_docx(data)
        elif ext in ("doc",):
            return "[Formato .doc antiguo no soportado. Convierte a .docx primero.]"
        elif ext == "txt":
            return data.decode("utf-8", errors="replace")[:MAX_CHARS]
        else:
            return f"[Formato .{ext} no soportado. Usa PDF, DOCX o TXT.]"
    except ImportError as e:
        pkg = str(e).split("'")[1] if "'" in str(e) else str(e)
        return f"[Falta instalar: pip install {pkg}]"
    except Exception as e:
        return f"[Error extrayendo texto: {e}]"


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Página {i+1}]\n{text.strip()}")

    full = "\n\n".join(pages)
    if len(full) > MAX_CHARS:
        full = full[:MAX_CHARS] + f"\n\n[... texto truncado — {len(pages)} páginas en total]"
    return full or "[El PDF no contiene texto extraíble (puede ser un PDF escaneado).]"


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full = "\n".join(paragraphs)
    if len(full) > MAX_CHARS:
        full = full[:MAX_CHARS] + "\n\n[... texto truncado]"
    return full or "[El documento no contiene texto.]"
