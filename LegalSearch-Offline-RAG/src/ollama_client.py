from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

from logging_setup import get_logger


logger = get_logger("ollama_client")


def _list_model_names(payload: dict[str, Any]) -> set[str]:
    models = payload.get("models", []) if isinstance(payload, dict) else []
    names: set[str] = set()
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if name:
            names.add(name)
            names.add(name.split(":")[0])
    return names


def check_ollama(ollama_url: str) -> tuple[bool, str]:
    base_url = ollama_url.rstrip("/")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
        return True, f"Ollama OK en {base_url}"
    except requests.RequestException as exc:
        logger.error("check_ollama failed url=%s error=%s", base_url, exc)
        return (
            False,
            f"No se pudo conectar con Ollama en {base_url}. Inicia Ollama y verifica http://localhost:11434.",
        )


def start_ollama_windows(ollama_url: str = "http://localhost:11434") -> tuple[bool, str]:
    base_url = ollama_url.rstrip("/")

    if check_ollama(base_url)[0]:
        return True, "Ollama ya estaba ejecutandose."

    # 1) Intentar localizar CLI aunque no esté en PATH
    candidates = [
        shutil.which("ollama"),
        str(Path.home() / "AppData/Local/Programs/Ollama/ollama.exe"),
        "C:/Program Files/Ollama/ollama.exe",
    ]
    ollama_cli = next((c for c in candidates if c and Path(c).exists()), None)

    creationflags = 0
    if hasattr(subprocess, "CREATE_NEW_CONSOLE"):
        creationflags = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]

    # 2) Si encontramos CLI, levantamos serve
    if ollama_cli:
        try:
            subprocess.Popen(
                [ollama_cli, "serve"],
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.5)
            ok, _ = check_ollama(base_url)
            if ok:
                return True, "Ollama iniciado automaticamente (ollama serve)."
        except Exception:
            pass

    # 3) Fallback: abrir la app (por si el CLI no está accesible)
    app_candidates = [
        Path.home() / "AppData/Local/Programs/Ollama/Ollama app.exe",
        Path("C:/Program Files/Ollama/Ollama app.exe"),
    ]
    for app_path in app_candidates:
        if app_path.exists():
            try:
                subprocess.Popen([str(app_path)], creationflags=creationflags)
                time.sleep(2.0)
                ok, _ = check_ollama(base_url)
                if ok:
                    return True, "Ollama iniciado automaticamente (app)."
            except Exception:
                pass

    return (
        False,
        "No se pudo iniciar Ollama automaticamente. Ejecuta 'ollama serve' y verifica http://localhost:11434.",
    )


def _model_exists(ollama_url: str, model: str) -> tuple[bool, list[str]]:
    try:
        response = requests.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=6)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"No se pudo verificar modelos en {ollama_url}. Inicia Ollama y verifica http://localhost:11434."
        ) from exc
    payload = response.json()
    names = _list_model_names(payload if isinstance(payload, dict) else {})
    available = sorted([n for n in names if ":" in n])
    return model in names, available


def generate(
    ollama_url: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    base_url = ollama_url.rstrip("/")
    try:
        exists, available = _model_exists(base_url, model)
        if not exists:
            listed = ", ".join(available[:8]) if available else "ninguno"
            raise RuntimeError(
                f"Modelo no encontrado: {model}. Ejecuta: ollama pull {model}. Modelos detectados: {listed}"
            )

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": float(temperature),
                "num_predict": int(max_tokens),
            },
        }
        response = requests.post(f"{base_url}/api/generate", json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        text = str(data.get("response", "")).strip()
        if not text:
            raise RuntimeError("Ollama devolvio una respuesta vacia.")
        return text
    except requests.RequestException as exc:
        logger.error("generate request failed model=%s url=%s error=%s", model, base_url, exc)
        raise RuntimeError(
            f"Error al consultar Ollama en {base_url}. Inicia Ollama y verifica http://localhost:11434."
        ) from exc
