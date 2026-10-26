from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from rag_core import OfflineRAG


def main() -> None:
    rag = OfflineRAG()
    print("Chat RAG offline. Escribe 'salir' para terminar.")
    # Evita iniciar chat si no existe base indexada.
    if not rag.index_exists():
        print("No hay indice disponible. Ejecuta: python src/build_index.py")
        return

    while True:
        question = input("\nTu pregunta: ").strip()
        if question.lower() in {"salir", "exit", "quit"}:
            print("Fin del chat.")
            break
        if not question:
            continue
        try:
            result = rag.ask(question)
            print(f"\nModelo usado: {result['used_model']}")
            print(f"Respuesta:\n{result['answer']}")
            print("\nFuentes:")
            for idx, src in enumerate(result["sources"], start=1):
                print(
                    f"{idx}. {src['file_name']} | pag. {src['page']} | "
                    f"distancia: {src['distance']}"
                )
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()