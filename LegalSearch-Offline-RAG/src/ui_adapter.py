from __future__ import annotations

import shutil
import traceback
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from document_manager import ALLOWED_EXTENSIONS, list_documents
from logging_setup import get_logger, setup_logging
from ollama_client import check_ollama as check_ollama_client
from ollama_client import start_ollama_windows
from rag_core import OfflineRAG, ask as rag_ask
from utils import get_app_data_dir, load_config


class _WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class _Worker(QRunnable):
    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.result.emit(self.fn(*self.args, **self.kwargs))
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc(limit=5)
            print(tb)
            self.signals.error.emit(f"{exc}\n{tb}")
        finally:
            self.signals.finished.emit()


class BackendAdapter(QObject):
    error = Signal(str)
    info = Signal(str)
    busy = Signal(bool, str)
    index_status_changed = Signal(str)
    doc_count_changed = Signal(int)
    search_finished = Signal(str, list)
    summary_finished = Signal(str)
    ollama_status_changed = Signal(bool, str)
    db_status_changed = Signal(bool, str)

    documents_listed = Signal(list)
    import_finished = Signal(dict)
    system_status = Signal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        setup_logging()
        self.logger = get_logger("ui_adapter")
        self.thread_pool = QThreadPool.globalInstance()

        try:
            self.thread_pool.setMaxThreadCount(max(4, self.thread_pool.maxThreadCount()))
        except Exception:  # noqa: BLE001
            pass

        self.app_dir = get_app_data_dir("LegalSearchOffline")
        self.documents_dir = self.app_dir / "documents"
        self.chroma_dir = self.app_dir / "chroma_db"

        self.config = load_config()
        self.ollama_ok = False
        self.db_ok = False
        self.index_status = "Sin indice"
        self._active_workers: list[_Worker] = []

    def _run_async(
        self,
        busy_message: str,
        fn: Callable[..., Any],
        on_result: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_finished: Callable[[], None] | None = None,
        *args: Any,
    ) -> None:
        self.busy.emit(True, busy_message)

        worker = _Worker(fn, *args)
        self._active_workers.append(worker)

        if on_result:
            worker.signals.result.connect(on_result)
        if on_error:
            worker.signals.error.connect(on_error)
        else:
            worker.signals.error.connect(self._handle_error)

        def _finished() -> None:
            try:
                self._active_workers.remove(worker)
            except ValueError:
                pass
            if on_finished:
                on_finished()
            self.busy.emit(False, "Listo")

        worker.signals.finished.connect(_finished)
        self.thread_pool.start(worker)

    def _handle_error(self, message: str) -> None:
        clean = str(message).strip()
        print(clean)
        self.logger.error("BackendAdapter error: %s", clean)
        self.error.emit(clean)

    def _create_rag(self) -> OfflineRAG:
        cfg = dict(load_config())
        self.config = cfg
        return OfflineRAG(
            data_dir=str(self.documents_dir),
            persist_dir=str(self.chroma_dir),
            ollama_url=str(cfg.get("ollama_url", "http://localhost:11434")),
            # BUG FIX 1: usar el modelo configurado correctamente para LLM y embed
            llm_models=(str(cfg.get("ollama_model", "phi3:mini")),),
            embed_models=(str(cfg.get("ollama_model", "phi3:mini")),),
            top_k=int(cfg.get("top_k", 5)),
        )

    def _db_has_index(self) -> bool:
        try:
            rag = self._create_rag()
            return rag.index_exists()
        except Exception:  # noqa: BLE001
            return any(self.chroma_dir.glob("*"))

    def _count_documents(self) -> int:
        if not self.documents_dir.exists():
            return 0
        return len(
            [
                p
                for p in self.documents_dir.iterdir()
                if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
            ]
        )

    def initialize(self) -> None:
        print("DEBUG: adapter.initialize called")
        self.logger.info("initialize() start")

        def _impl() -> dict[str, Any]:
            cfg = dict(load_config())
            ollama_url = str(cfg.get("ollama_url", "http://localhost:11434"))
            model = str(cfg.get("ollama_model", "phi3:mini"))

            self.app_dir.mkdir(parents=True, exist_ok=True)
            self.documents_dir.mkdir(parents=True, exist_ok=True)
            self.chroma_dir.mkdir(parents=True, exist_ok=True)

            ollama_ok, ollama_msg = check_ollama_client(ollama_url)
            if not ollama_ok:
                start_ok, start_msg = start_ollama_windows(ollama_url)
                self.logger.info(
                    "initialize() start_ollama_windows ok=%s msg=%s", start_ok, start_msg
                )
                ollama_ok, recheck_msg = check_ollama_client(ollama_url)
                if not ollama_ok:
                    ollama_msg = f"{start_msg} {recheck_msg}".strip()
                else:
                    ollama_msg = start_msg

            has_db_files = self.chroma_dir.exists() and any(self.chroma_dir.iterdir())
            db_ok = has_db_files
            doc_count = self._count_documents()
            index_status = "Listo" if db_ok else "Sin indice"
            return {
                "cfg": cfg,
                "model": model,
                "ollama_ok": ollama_ok,
                "ollama_msg": ollama_msg,
                "db_ok": db_ok,
                "doc_count": doc_count,
                "index_status": index_status,
                "has_db_files": has_db_files,
            }

        def _done(payload: dict[str, Any]) -> None:
            self.config = dict(payload.get("cfg", {}))
            self.ollama_ok = bool(payload.get("ollama_ok", False))
            self.db_ok = bool(payload.get("db_ok", False))
            self.index_status = str(payload.get("index_status", "Sin indice"))

            self.ollama_status_changed.emit(self.ollama_ok, str(payload.get("ollama_msg", "")))
            self.db_status_changed.emit(self.db_ok, "OK" if self.db_ok else "NO")
            self.index_status_changed.emit(self.index_status)
            self.doc_count_changed.emit(int(payload.get("doc_count", 0)))
            self.documents_listed.emit(list_documents())
            self.system_status.emit(
                {
                    "mode": "offline",
                    "db_ok": self.db_ok,
                    "ollama_ok": self.ollama_ok,
                    "model": str(payload.get("model", "phi3:mini")),
                    "ollama_msg": str(payload.get("ollama_msg", "")),
                }
            )

        self._run_async("Iniciando...", _impl, _done)

    def refresh_documents(self) -> None:
        self.logger.info("refresh_documents()")
        docs = list_documents()
        self.documents_listed.emit(docs)
        self.doc_count_changed.emit(self._count_documents())

    def _copy_paths_to_documents(self, paths: list[str]) -> dict[str, int]:
        imported = 0
        failed = 0
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        for raw in paths:
            try:
                src = Path(raw)
                if not src.exists() or not src.is_file():
                    failed += 1
                    continue
                if src.suffix.lower() not in ALLOWED_EXTENSIONS:
                    failed += 1
                    continue
                target = self.documents_dir / src.name
                stem = target.stem
                suffix = target.suffix
                idx = 1
                while target.exists():
                    target = self.documents_dir / f"{stem}_{idx}{suffix}"
                    idx += 1
                shutil.copy2(src, target)
                imported += 1
            except Exception:  # noqa: BLE001
                self.logger.exception("Failed importing file path=%s", raw)
                failed += 1
        return {"imported": imported, "failed": failed}

    def import_files(self, paths: list[str]) -> None:
        print("DEBUG: adapter.import_files called")
        try:
            clean_paths = [str(Path(p)) for p in (paths or []) if str(p).strip()]
            self.logger.info("import_files() start count=%s", len(clean_paths))

            if not clean_paths:
                self.error.emit("No se seleccionaron archivos para importar.")
                return

            def _impl() -> dict[str, int]:
                return self._copy_paths_to_documents(clean_paths)

            def _done(payload: dict[str, int]) -> None:
                imported = int(payload.get("imported", 0))
                failed = int(payload.get("failed", 0))
                self.logger.info("import_files() done imported=%s failed=%s", imported, failed)
                self.import_finished.emit(payload)
                self.doc_count_changed.emit(self._count_documents())
                self.documents_listed.emit(list_documents())
                if imported > 0:
                    self.info.emit(f"Importados {imported} archivos. Reconstruye el indice.")

            self._run_async("Importando archivos...", _impl, _done)
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            print(tb)
            self.logger.error("import_files() failed: %s", tb)
            self.error.emit(str(exc))

    def import_folder(self, folder: str) -> None:
        print("DEBUG: adapter.import_folder called")
        try:
            folder_path = Path(folder) if folder else None
            self.logger.info("import_folder() start folder=%s", folder)

            if folder_path is None or not folder_path.exists() or not folder_path.is_dir():
                self.error.emit("Carpeta invalida para importar.")
                return

            candidates = [
                str(p)
                for p in folder_path.rglob("*")
                if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
            ]

            if not candidates:
                self.error.emit("La carpeta no contiene archivos compatibles (.pdf, .docx, .txt, .md).")
                return

            def _impl() -> dict[str, int]:
                return self._copy_paths_to_documents(candidates)

            def _done(payload: dict[str, int]) -> None:
                imported = int(payload.get("imported", 0))
                failed = int(payload.get("failed", 0))
                self.logger.info("import_folder() done imported=%s failed=%s", imported, failed)
                self.import_finished.emit(payload)
                self.doc_count_changed.emit(self._count_documents())
                self.documents_listed.emit(list_documents())
                if imported > 0:
                    self.info.emit(f"Importados {imported} archivos. Reconstruye el indice.")

            self._run_async("Importando carpeta...", _impl, _done)
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            print(tb)
            self.logger.error("import_folder() failed: %s", tb)
            self.error.emit(str(exc))

    def rebuild_index(self) -> None:
        print("DEBUG: adapter.rebuild_index called")
        try:
            self.logger.info("rebuild_index() start")
            self.documents_dir.mkdir(parents=True, exist_ok=True)
            self.chroma_dir.mkdir(parents=True, exist_ok=True)

            # BUG FIX 2: contar solo PDFs (rag_core solo indexa .pdf)
            pdf_count = len([
                p for p in self.documents_dir.iterdir()
                if p.is_file() and p.suffix.lower() == ".pdf"
            ])

            if pdf_count == 0:
                self.error.emit(
                    "No hay PDFs en la carpeta de documentos. "
                    "Importa al menos un PDF antes de reconstruir el indice."
                )
                return

            # BUG FIX 3: verificar Ollama ANTES de lanzar el hilo
            ollama_url = str(self.config.get("ollama_url", "http://localhost:11434"))
            ollama_ok, ollama_msg = check_ollama_client(ollama_url)
            if not ollama_ok:
                self.error.emit(
                    f"Ollama no esta disponible: {ollama_msg}. "
                    "Inicia Ollama antes de reconstruir el indice."
                )
                return

            self.index_status_changed.emit("Indexando...")

            def _impl() -> dict[str, int]:
                rag = self._create_rag()
                result = rag.build_index()
                return {
                    "pdf_count": int(result.get("pdf_count", 0)),
                    "chunk_count": int(result.get("chunk_count", 0)),
                    "doc_count": int(self._count_documents()),
                }

            def _done(payload: dict[str, int]) -> None:
                self.db_ok = True
                self.index_status = "Listo"
                self.index_status_changed.emit(self.index_status)
                self.db_status_changed.emit(True, "OK")
                self.doc_count_changed.emit(int(payload.get("doc_count", 0)))
                self.documents_listed.emit(list_documents())
                self.info.emit(
                    f"Indice reconstruido. "
                    f"PDFs: {int(payload.get('pdf_count', 0))} | "
                    f"Chunks: {int(payload.get('chunk_count', 0))}"
                )
                self.logger.info(
                    "rebuild_index() done pdf=%s chunks=%s docs=%s",
                    int(payload.get("pdf_count", 0)),
                    int(payload.get("chunk_count", 0)),
                    int(payload.get("doc_count", 0)),
                )

            def _on_error(message: str) -> None:
                self.index_status = "Sin indice"
                self.index_status_changed.emit(self.index_status)
                self.db_ok = self._db_has_index()
                self.db_status_changed.emit(self.db_ok, "OK" if self.db_ok else "NO")
                self._handle_error(message)

            self._run_async("Reconstruyendo indice...", _impl, _done, _on_error)
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            print(tb)
            self.logger.error("rebuild_index() failed: %s", tb)
            self.error.emit(str(exc))

    def run_search(self, query: str) -> None:
        print("DEBUG: adapter.run_search called")
        try:
            question = (query or "").strip()
            self.logger.info("run_search() start query_len=%s", len(question))

            if not question:
                self.error.emit("Introduce una consulta")
                return

            # BUG FIX 4: siempre verificar indice en tiempo real
            self.db_ok = self._db_has_index()
            if not self.db_ok:
                self.error.emit("No hay indice. Importa documentos y reconstruye el indice.")
                self.db_status_changed.emit(False, "NO")
                self.index_status_changed.emit("Sin indice")
                return

            if not self.ollama_ok:
                ollama_url = str(self.config.get("ollama_url", "http://localhost:11434"))
                self.ollama_ok, ollama_msg = check_ollama_client(ollama_url)
                self.ollama_status_changed.emit(self.ollama_ok, ollama_msg)
            if not self.ollama_ok:
                self.error.emit(
                    "Ollama no esta ejecutandose en http://localhost:11434. "
                    "Inicia con: ollama serve"
                )
                return

            def _impl() -> dict[str, Any]:
                answer, sources = rag_ask(question, self.chroma_dir, self.config)
                return {"answer": answer, "sources": sources}

            def _done(payload: dict[str, Any]) -> None:
                answer = str(payload.get("answer", "")).strip()
                sources = list(payload.get("sources", []))
                self.search_finished.emit(answer, sources)
                self.logger.info(
                    "run_search() done answer_len=%s sources=%s",
                    len(answer),
                    len(sources),
                )

            self._run_async("Buscando...", _impl, _done)
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            print(tb)
            self.logger.error("run_search() failed: %s", tb)
            self.error.emit(str(exc))

    def run_summary(self, query: str) -> None:
        print("DEBUG: adapter.run_summary called")
        try:
            question = (query or "").strip()
            self.logger.info("run_summary() start query_len=%s", len(question))

            if not question:
                self.error.emit("Introduce un tema para resumir")
                return

            if not self.db_ok:
                self.db_ok = self._db_has_index()
            if not self.db_ok:
                self.error.emit("No hay indice. Importa documentos y reconstruye el indice.")
                return

            if not self.ollama_ok:
                ollama_url = str(self.config.get("ollama_url", "http://localhost:11434"))
                self.ollama_ok, ollama_msg = check_ollama_client(ollama_url)
                self.ollama_status_changed.emit(self.ollama_ok, ollama_msg)
            if not self.ollama_ok:
                self.error.emit(
                    "Ollama no esta ejecutandose en http://localhost:11434. "
                    "Inicia con: ollama serve"
                )
                return

            prompt = (
                "Genera un resumen juridico breve, claro y accionable usando el contexto recuperado. "
                f"Consulta: {question}"
            )

            def _impl() -> str:
                answer, _sources = rag_ask(prompt, self.chroma_dir, self.config)
                return answer

            def _done(answer: str) -> None:
                clean = str(answer).strip()
                self.summary_finished.emit(clean)
                self.logger.info("run_summary() done answer_len=%s", len(clean))

            self._run_async("Generando resumen...", _impl, _done)
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            print(tb)
            self.logger.error("run_summary() failed: %s", tb)
            self.error.emit(str(exc))

    def delete_document(self, path: str) -> None:
        self.logger.info("delete_document() path=%s", path)
        try:
            target = Path(path)
            if not target.exists() or not target.is_file():
                self.error.emit(f"No se encontro el archivo: {path}")
                return
            target.unlink()
            self.logger.info("delete_document() deleted %s", path)
            self.doc_count_changed.emit(self._count_documents())
            self.documents_listed.emit(list_documents())
            self.info.emit(f"Eliminado: {target.name}")
        except Exception as exc:  # noqa: BLE001
            self.logger.error("delete_document() failed: %s", exc)
            self.error.emit(f"Error al eliminar: {exc}")
