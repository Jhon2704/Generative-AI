from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from pypdf import PdfReader

from ollama_client import generate as ollama_generate
from utils import get_app_data_dir, load_config

try:
    import chromadb  # type: ignore
except ImportError:
    chromadb = None


@dataclass
class SourceChunk:
    """Representa un fragmento recuperado para mostrar citas al usuario."""

    file_name: str
    page: int
    chunk_id: str
    distance: float | None
    preview: str


class LocalPersistentCollection:
    """Fallback local de una coleccion vectorial persistida en JSON.

    Se usa solo cuando `chromadb` no esta disponible en el entorno.
    """

    def __init__(self, storage_file: Path) -> None:
        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        # Cargar registros existentes si ya hay persistencia en disco.
        if self.storage_file.exists():
            with self.storage_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self.records = data.get("records", {})

    def _save(self) -> None:
        # Persistir el estado completo tras cada insercion.
        payload = {"records": self.records}
        with self.storage_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

    def count(self) -> int:
        return len(self.records)

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        # Mantiene la misma firma que `collection.add(...)` de Chroma.
        for i, item_id in enumerate(ids):
            self.records[item_id] = {
                "document": documents[i],
                "metadata": metadatas[i],
                "embedding": embeddings[i],
            }
        self._save()

    @staticmethod
    def _cosine_distance(v1: list[float], v2: list[float]) -> float:
        # Distancia coseno = 1 - similitud coseno.
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = sum(a * a for a in v1) ** 0.5
        n2 = sum(b * b for b in v2) ** 0.5
        if n1 == 0 or n2 == 0:
            return 1.0
        similarity = dot / (n1 * n2)
        return 1.0 - similarity

    def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str] | None = None,  # noqa: ARG002
    ) -> dict[str, list[list[Any]]]:
        # Calcula distancia contra todos los chunks y devuelve los top-N.
        q = query_embeddings[0]
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for item_id, item in self.records.items():
            dist = self._cosine_distance(q, item["embedding"])
            scored.append((dist, item_id, item))
        scored.sort(key=lambda x: x[0])
        top = scored[:n_results]
        return {
            "documents": [[t[2]["document"] for t in top]],
            "metadatas": [[t[2]["metadata"] for t in top]],
            "distances": [[t[0] for t in top]],
            "ids": [[t[1] for t in top]],
        }


class OfflineRAG:
    """Nucleo del sistema RAG offline: indexa PDFs y responde consultas."""

    def __init__(
        self,
        data_dir: str | None = None,
        persist_dir: str | None = None,
        collection_name: str = "pdf_rag",
        ollama_url: str = "http://127.0.0.1:11434",
        llm_models: tuple[str, ...] = ("llama3.2", "phi3:mini"),
        embed_models: tuple[str, ...] = ("llama3.2", "phi3:mini"),
        top_k: int = 4,
    ) -> None:
        base_dir = get_app_data_dir("LegalSearchOffline")
        resolved_data_dir = Path(data_dir) if data_dir else base_dir / "documents"
        resolved_persist_dir = Path(persist_dir) if persist_dir else base_dir / "chroma_db"

        self.data_dir = resolved_data_dir
        self.persist_dir = resolved_persist_dir
        self.collection_name = collection_name
        self.ollama_url = ollama_url.rstrip("/")
        self.llm_models = llm_models
        self.embed_models = embed_models
        self.top_k = top_k
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Preferir Chroma cuando existe la dependencia; usar fallback local si no.
        self.client = None
        if chromadb is not None:
            self.client = chromadb.PersistentClient(path=str(self.persist_dir))
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            self.using_chroma = True
        else:
            storage_file = self.persist_dir / f"{self.collection_name}.json"
            self.collection = LocalPersistentCollection(storage_file=storage_file)
            self.using_chroma = False

    def index_exists(self) -> bool:
        return self.collection.count() > 0

    def indexed_documents_count(self) -> int:
        # Calcula cantidad de archivos unicos presentes en el indice.
        if not self.index_exists():
            return 0

        file_names: set[str] = set()
        if self.using_chroma:
            try:
                all_items = self.collection.get(include=["metadatas"])
                for meta in all_items.get("metadatas", []) or []:
                    if isinstance(meta, dict) and meta.get("file_name"):
                        file_names.add(str(meta["file_name"]))
            except Exception:  # noqa: BLE001
                return 0
        else:
            records = getattr(self.collection, "records", {})
            for record in records.values():
                meta = record.get("metadata", {})
                file_name = meta.get("file_name")
                if file_name:
                    file_names.add(str(file_name))

        return len(file_names)

    def _check_ollama_available(self) -> None:
        # Verificacion temprana para fallar rapido si Ollama no responde.
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"No se pudo conectar con Ollama en {self.ollama_url}. "
                "Asegura que el servicio este ejecutandose."
            ) from exc

    def _list_pdfs(self) -> list[Path]:
        return sorted(self.data_dir.glob("*.pdf"))

    @staticmethod
    def _split_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
        """Divide texto en ventanas solapadas para mejorar recuperacion."""

        clean_text = " ".join(text.split())
        if not clean_text:
            return []
        chunks: list[str] = []
        start = 0
        n = len(clean_text)
        while start < n:
            end = min(start + chunk_size, n)
            chunk = clean_text[start:end]
            chunks.append(chunk)
            if end == n:
                break
            start = max(0, end - overlap)
        return chunks

    @staticmethod
    def _chunk_id(file_name: str, page: int, chunk_idx: int, chunk_text: str) -> str:
        # ID estable por contenido para minimizar colisiones entre reconstrucciones.
        base = f"{file_name}:{page}:{chunk_idx}:{chunk_text[:120]}"
        digest = hashlib.sha1(base.encode("utf-8")).hexdigest()
        return f"{file_name}-{page}-{chunk_idx}-{digest[:12]}"

    def _embed_with_model(self, model: str, texts: list[str]) -> list[list[float]]:
        # Endpoint nuevo de Ollama: /api/embed (batch).
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embed",
                json={"model": model, "input": texts},
                timeout=180,
            )
            if response.ok:
                data = response.json()
                embeddings = data.get("embeddings")
                if isinstance(embeddings, list) and embeddings:
                    return embeddings
        except requests.RequestException:
            pass

        # Fallback compatible con endpoint legacy: /api/embeddings (item por item).
        embeddings: list[list[float]] = []
        for idx, text in enumerate(texts):
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                    timeout=180,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise RuntimeError(
                    f"Error en endpoint legacy /api/embeddings con modelo {model} "
                    f"(chunk {idx + 1}/{len(texts)}): {exc}"
                ) from exc
            data = response.json()
            emb = data.get("embedding")
            if not isinstance(emb, list):
                raise RuntimeError(f"Respuesta invalida de embeddings con modelo {model}: {data}")
            embeddings.append(emb)
        return embeddings

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        # Probar modelos en orden hasta obtener embeddings validos.
        last_error: Exception | None = None
        for model in self.embed_models:
            try:
                return self._embed_with_model(model, texts)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        raise RuntimeError(
            f"No se pudieron generar embeddings con los modelos: {', '.join(self.embed_models)}"
        ) from last_error

    def _generate_answer(self, prompt: str) -> tuple[str, str]:
        # Parametros de inferencia conservadores para respuestas estables.
        payload = {
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        last_error: Exception | None = None
        for model in self.llm_models:
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={**payload, "model": model},
                    timeout=240,
                )
                response.raise_for_status()
                data = response.json()
                answer = data.get("response", "").strip()
                if answer:
                    return answer, model
            except requests.RequestException as exc:
                last_error = exc
        raise RuntimeError(
            f"No se pudo generar respuesta con modelos: {', '.join(self.llm_models)}"
        ) from last_error

    def build_index(self) -> dict[str, Any]:
        """Construye (o reconstruye) el indice vectorial desde PDFs en /data."""

        self._check_ollama_available()
        pdf_paths = self._list_pdfs()
        if not pdf_paths:
            raise RuntimeError(f"No se encontraron PDFs en {self.data_dir.resolve()}")

        # Reset de coleccion para evitar mezclar chunks de ejecuciones previas.
        if self.using_chroma and self.client is not None:
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:  # noqa: BLE001
                pass
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        else:
            storage_file = self.persist_dir / f"{self.collection_name}.json"
            if storage_file.exists():
                storage_file.unlink()
            self.collection = LocalPersistentCollection(storage_file=storage_file)

        ids: list[str] = []
        docs: list[str] = []
        metas: list[dict[str, Any]] = []

        # Extraccion por pagina y chunking por ventana.
        for pdf_path in pdf_paths:
            reader = PdfReader(str(pdf_path))
            for page_idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                chunks = self._split_text(page_text)
                for chunk_idx, chunk_text in enumerate(chunks, start=1):
                    chunk_id = self._chunk_id(pdf_path.name, page_idx, chunk_idx, chunk_text)
                    ids.append(chunk_id)
                    docs.append(chunk_text)
                    metas.append(
                        {
                            "source": str(pdf_path),
                            "file_name": pdf_path.name,
                            "page": page_idx,
                            "chunk_idx": chunk_idx,
                        }
                    )

        if not docs:
            raise RuntimeError("No se pudo extraer texto util de los PDFs.")

        # Insercion en lotes para reducir memoria y llamadas de red por embedding.
        batch_size = 32
        for start in range(0, len(docs), batch_size):
            end = min(start + batch_size, len(docs))
            batch_docs = docs[start:end]
            batch_embeddings = self._embed_texts(batch_docs)
            self.collection.add(
                ids=ids[start:end],
                documents=batch_docs,
                metadatas=metas[start:end],
                embeddings=batch_embeddings,
            )

        return {"pdf_count": len(pdf_paths), "chunk_count": len(docs)}

    def ask(self, question: str, top_k: int | None = None) -> dict[str, Any]:
        """Responde una pregunta usando recuperacion semantica sobre el indice."""

        if not question.strip():
            raise ValueError("La pregunta no puede estar vacia.")
        if not self.index_exists():
            raise RuntimeError("Indice vacio. Reconstruye el indice antes de consultar.")

        k = top_k or self.top_k
        query_embedding = self._embed_texts([question])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # Preparar contexto para el prompt y fuentes para trazabilidad en UI/CLI.
        context_blocks: list[str] = []
        sources: list[SourceChunk] = []
        for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
            file_name = str(meta.get("file_name", "desconocido"))
            page = int(meta.get("page", 0))
            distance = float(distances[i - 1]) if i - 1 < len(distances) else None
            context_blocks.append(
                f"[Fuente {i}] Archivo: {file_name} | Pagina: {page}\n{doc}"
            )
            sources.append(
                SourceChunk(
                    file_name=file_name,
                    page=page,
                    chunk_id=str(meta.get("chunk_idx", i)),
                    distance=distance,
                    preview=(doc[:220] + "...") if len(doc) > 220 else doc,
                )
            )

        context = "\n\n".join(context_blocks)
        prompt = (
            "Eres un asistente que responde usando solo el contexto dado.\n"
            "Si no hay evidencia suficiente en el contexto, dilo claramente.\n"
            "Responde en espanol de forma concreta.\n\n"
            f"Pregunta: {question}\n\n"
            f"Contexto:\n{context}\n\n"
            "Respuesta:"
        )
        answer, used_model = self._generate_answer(prompt)

        return {
            "answer": answer,
            "used_model": used_model,
            "sources": [s.__dict__ for s in sources],
        }

    def retrieve(self, question: str, top_k: int | None = None) -> list[dict[str, Any]]:
        if not question.strip():
            raise ValueError("La consulta no puede estar vacia.")
        if not self.index_exists():
            raise RuntimeError("No hay indice. Importa documentos y reconstruye indice.")

        k = top_k or self.top_k
        query_embedding = self._embed_texts([question])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        sources: list[dict[str, Any]] = []
        for i, (doc, meta) in enumerate(zip(docs, metas)):
            distance = float(distances[i]) if i < len(distances) else 1.0
            source_path = str(meta.get("source", ""))
            file_name = str(meta.get("file_name", Path(source_path).name or "desconocido"))
            sources.append(
                {
                    "text": str(doc),
                    "source": file_name,
                    "path": source_path,
                    "page": int(meta.get("page", 0)),
                    "score": round(max(0.0, min(1.0, 1.0 - distance)), 4),
                }
            )
        return sources

    def diagnostics(self) -> str:
        # Snapshot de configuracion y estado para troubleshooting rapido.
        info = {
            "data_dir": str(self.data_dir.resolve()),
            "persist_dir": str(self.persist_dir.resolve()),
            "collection_name": self.collection_name,
            "chunks_indexed": self.collection.count(),
            "llm_models": list(self.llm_models),
            "embed_models": list(self.embed_models),
            "ollama_url": self.ollama_url,
            "vector_backend": "chroma" if self.using_chroma else "local_fallback",
        }
        return json.dumps(info, indent=2, ensure_ascii=False)


def retrieve(query: str, k: int, chroma_dir: Path) -> list[dict[str, Any]]:
    app_dir = get_app_data_dir("LegalSearchOffline")
    rag = OfflineRAG(data_dir=str(app_dir / "documents"), persist_dir=str(chroma_dir))
    return rag.retrieve(query, top_k=k)


def ask(query: str, chroma_dir: Path, config: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    clean_query = (query or "").strip()
    if not clean_query:
        raise ValueError("La consulta no puede estar vacia.")

    app_dir = get_app_data_dir("LegalSearchOffline")
    cfg = load_config()
    cfg.update(config or {})

    rag = OfflineRAG(
        data_dir=str(app_dir / "documents"),
        persist_dir=str(chroma_dir),
        ollama_url=str(cfg.get("ollama_url", "http://localhost:11434")),
    )
    if not rag.index_exists():
        raise RuntimeError("No hay indice. Importa documentos y reconstruye indice.")

    top_k = int(cfg.get("top_k", 5))
    sources = rag.retrieve(clean_query, top_k=top_k)
    if not sources:
        return "No se encontraron fragmentos relevantes en el indice.", []

    context_parts: list[str] = []
    for idx, item in enumerate(sources, start=1):
        context_parts.append(
            (
                f"[Fuente {idx}] Archivo: {item['source']} | Pagina: {item['page']} | "
                f"Score: {item['score']}\n{item['text']}"
            )
        )

    joined_context = "\n\n".join(context_parts)

    prompt = (
        "Eres un asistente legal. Responde SOLO con base en el contexto proporcionado. "
        "Si no hay evidencia suficiente, dilo explicitamente.\n\n"
        f"Contexto:\n{joined_context}\n\n"
        f"Pregunta del usuario: {clean_query}\n\n"
        "Respuesta:"
    )
    answer = ollama_generate(
        ollama_url=str(cfg.get("ollama_url", "http://localhost:11434")),
        model=str(cfg.get("ollama_model", "phi3:mini")),
        prompt=prompt,
        temperature=float(cfg.get("temperature", 0.2)),
        max_tokens=int(cfg.get("max_tokens", 512)),
    )
    return answer, sources
