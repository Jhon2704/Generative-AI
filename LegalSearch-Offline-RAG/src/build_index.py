from __future__ import annotations

import sys
from pathlib import Path

# Asegura que src/ este en el path tanto si se ejecuta desde la raiz
# (python src/build_index.py) como desde dentro de src/ (python build_index.py).
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from rag_core import OfflineRAG


def main() -> None:
    # Script utilitario: reconstruye indice completo desde /data.
    rag = OfflineRAG()
    result = rag.build_index()
    print(
        "Indice reconstruido correctamente. "
        f"PDFs: {result['pdf_count']} | Chunks: {result['chunk_count']}"
    )
    # Mostrar diagnostico final de backend, rutas y modelos activos.
    print(rag.diagnostics())


if __name__ == "__main__":
    main()