from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from utils import get_app_data_dir

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def sanitize_filename(name: str) -> str:
    candidate = Path(name).name.strip()
    candidate = re.sub(r"[^\w\-. ]", "_", candidate, flags=re.UNICODE)
    candidate = re.sub(r"\s+", " ", candidate).strip(" .")
    if not candidate:
        candidate = "documento.pdf"
    if not candidate.lower().endswith(".pdf"):
        candidate = f"{candidate}.pdf"
    return candidate


def _next_available_name(base_name: str, data_dir: Path) -> str:
    stem = Path(base_name).stem
    suffix = Path(base_name).suffix or ".pdf"
    candidate = f"{stem}{suffix}"
    idx = 1
    while (data_dir / candidate).exists():
        candidate = f"{stem}_{idx}{suffix}"
        idx += 1
    return candidate


def list_pdfs(data_dir: str) -> list[str]:
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    return sorted([p.name for p in root.glob("*.pdf")], key=str.lower)


def save_uploaded_pdfs(uploaded_files: Any, data_dir: str) -> list[str]:
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    saved_names: list[str] = []
    for file_obj in uploaded_files or []:
        safe_name = sanitize_filename(getattr(file_obj, "name", "documento.pdf"))
        final_name = _next_available_name(safe_name, root)
        target = root / final_name
        data = file_obj.getbuffer()
        with target.open("wb") as f:
            f.write(data)
        saved_names.append(final_name)
    return saved_names


def delete_pdfs(filenames: list[str], data_dir: str) -> int:
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    deleted = 0
    for name in filenames:
        # Usar solo el nombre base sin alterar la extension (sanitize_filename fuerza .pdf).
        safe_name = Path(name).name.strip()
        if not safe_name:
            continue
        target = root / safe_name
        if target.exists() and target.is_file():
            target.unlink()
            deleted += 1
    return deleted


def copy_pdfs_from_directory(source_dir: str, data_dir: str) -> list[str]:
    source = Path(source_dir)
    if not source.exists():
        return []

    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []

    for source_pdf in sorted(source.glob("*.pdf")):
        safe_name = sanitize_filename(source_pdf.name)
        final_name = _next_available_name(safe_name, root)
        target = root / final_name
        with source_pdf.open("rb") as src, target.open("wb") as dst:
            dst.write(src.read())
        copied.append(final_name)

    return copied


def _next_available_path(target_dir: Path, original_name: str) -> Path:
    base = Path(original_name).stem
    ext = Path(original_name).suffix
    candidate = target_dir / f"{base}{ext}"
    idx = 1
    while candidate.exists():
        candidate = target_dir / f"{base}_{idx}{ext}"
        idx += 1
    return candidate


def _import_paths(file_paths: list[str], documents_dir: Path | None = None) -> tuple[int, int]:
    target_dir = documents_dir or (get_app_data_dir() / "documents")
    target_dir.mkdir(parents=True, exist_ok=True)

    imported = 0
    failed = 0
    for raw_path in file_paths:
        try:
            source = Path(raw_path)
            if not source.exists() or not source.is_file():
                failed += 1
                continue
            if source.suffix.lower() not in ALLOWED_EXTENSIONS:
                failed += 1
                continue

            destination = _next_available_path(target_dir, source.name)
            shutil.copy2(source, destination)
            imported += 1
        except Exception:
            failed += 1
    return imported, failed


def import_files(file_paths: list[str]) -> int:
    imported, _failed = _import_paths(file_paths)
    return imported


def import_files_detailed(file_paths: list[str]) -> dict[str, int]:
    imported, failed = _import_paths(file_paths)
    return {"imported": imported, "failed": failed}


def import_folder(folder_path: str) -> int:
    source_dir = Path(folder_path)
    if not source_dir.exists() or not source_dir.is_dir():
        return 0
    candidates = [
        str(path)
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    imported, _failed = _import_paths(candidates)
    return imported


def import_folder_detailed(folder_path: str) -> dict[str, int]:
    source_dir = Path(folder_path)
    if not source_dir.exists() or not source_dir.is_dir():
        return {"imported": 0, "failed": 0}
    candidates = [str(path) for path in source_dir.iterdir() if path.is_file()]
    imported, failed = _import_paths(candidates)
    return {"imported": imported, "failed": failed}


def list_documents() -> list[dict[str, Any]]:
    documents_dir = get_app_data_dir() / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, Any]] = []
    for path in sorted(documents_dir.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        stat = path.stat()
        items.append(
            {
                "name": path.name,
                "ext": path.suffix.lower(),
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "path": str(path.resolve()),
            }
        )
    return items
