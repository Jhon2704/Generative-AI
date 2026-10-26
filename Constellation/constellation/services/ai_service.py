"""
Servicio de IA unificado para CONSTELLATION.
Soporta Claude (Anthropic) y modelos locales via Ollama.
Detecta automáticamente si Ollama está disponible.
"""
from __future__ import annotations

import os
import json
import asyncio
from typing import AsyncIterator, Optional
from dotenv import load_dotenv

load_dotenv()

# ── Anthropic ─────────────────────────────────────────────────
import anthropic

# ── Ollama ────────────────────────────────────────────────────
import httpx


# ══════════════════════════════════════════════════════════════
# CONSTANTES DE MODELOS
# ══════════════════════════════════════════════════════════════

# Modelos cloud de Anthropic
MODEL_SONNET = "claude-sonnet-4-6"
MODEL_HAIKU  = "claude-haiku-4-5-20251001"

# Modelos locales via Ollama
MODEL_MISTRAL = "mistral"
MODEL_LLAMA3  = "llama3"

# Mapa: identificador interno → nombre para mostrar al usuario
MODEL_LABELS: dict[str, str] = {
    MODEL_SONNET:  "Claude Sonnet 4 · Cloud Premium",
    MODEL_HAIKU:   "Claude Haiku · Rápido y económico",
    MODEL_MISTRAL: "Mistral 7B · Open Source / On-Premise",
    MODEL_LLAMA3:  "Llama 3 · Open Source Alternativo",
}

# Modelos que requieren Ollama
OLLAMA_MODELS = {MODEL_MISTRAL, MODEL_LLAMA3}

# Aliases cortos → ID completo (para compatibilidad con valores guardados en DB)
MODEL_ALIASES: dict[str, str] = {
    "claude-haiku":  MODEL_HAIKU,
    "claude-sonnet": MODEL_SONNET,
    "claude-sonnet-4": MODEL_SONNET,
}


def resolve_model(model_id: str) -> str:
    """Convierte aliases cortos al ID completo requerido por la API."""
    return MODEL_ALIASES.get(model_id, model_id)

# Configuración por defecto
DEFAULT_MAX_TOKENS = 2048
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


# ══════════════════════════════════════════════════════════════
# DETECCIÓN DE OLLAMA
# ══════════════════════════════════════════════════════════════

async def check_ollama_available() -> bool:
    """
    Verifica si Ollama está corriendo en el endpoint configurado.
    Hace un GET /api/tags con timeout de 2 segundos.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def get_available_models() -> list[dict[str, str]]:
    """
    Devuelve la lista de modelos disponibles según el entorno.
    Si Ollama no está activo, solo devuelve modelos Claude.

    Returns:
        Lista de dicts con 'id', 'label', 'source' ('cloud' u 'local').
    """
    modelos: list[dict[str, str]] = [
        {"id": MODEL_SONNET,  "label": MODEL_LABELS[MODEL_SONNET],  "source": "cloud"},
        {"id": MODEL_HAIKU,   "label": MODEL_LABELS[MODEL_HAIKU],   "source": "cloud"},
    ]

    if await check_ollama_available():
        modelos += [
            {"id": MODEL_MISTRAL, "label": MODEL_LABELS[MODEL_MISTRAL], "source": "local"},
            {"id": MODEL_LLAMA3,  "label": MODEL_LABELS[MODEL_LLAMA3],  "source": "local"},
        ]

    return modelos


# ══════════════════════════════════════════════════════════════
# CLIENTE ANTHROPIC
# ══════════════════════════════════════════════════════════════

def _get_anthropic_client() -> anthropic.Anthropic:
    """Crea el cliente Anthropic con la API key del entorno."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY no está configurada en .env")
    return anthropic.Anthropic(api_key=api_key)


# ══════════════════════════════════════════════════════════════
# STREAMING UNIFICADO
# ══════════════════════════════════════════════════════════════

async def stream_chat(
    model_id: str,
    messages: list[dict[str, str]],
    system_prompt: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> AsyncIterator[str]:
    """
    Genera una respuesta en streaming para el modelo especificado.

    Args:
        model_id: Identificador del modelo (MODEL_SONNET, MODEL_HAIKU, etc.).
        messages: Historial en formato [{"role": "user"|"assistant", "content": "..."}].
        system_prompt: Instrucción de sistema opcional.
        max_tokens: Límite de tokens en la respuesta.

    Yields:
        Fragmentos de texto (chunks) del streaming.
    """
    model_id = resolve_model(model_id)
    if model_id in OLLAMA_MODELS:
        async for chunk in _stream_ollama(model_id, messages, system_prompt, max_tokens):
            yield chunk
    else:
        async for chunk in _stream_anthropic(model_id, messages, system_prompt, max_tokens):
            yield chunk


async def _stream_anthropic(
    model_id: str,
    messages: list[dict[str, str]],
    system_prompt: Optional[str],
    max_tokens: int,
) -> AsyncIterator[str]:
    """Streaming via Anthropic API."""
    client = _get_anthropic_client()
    kwargs: dict = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    # Usamos la API síncrona de Anthropic en un thread para no bloquear el event loop
    loop = asyncio.get_event_loop()

    def _sync_stream():
        chunks = []
        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                chunks.append(text)
        return chunks

    # Ejecutar en thread pool
    chunks = await loop.run_in_executor(None, _sync_stream)
    for chunk in chunks:
        yield chunk


async def _stream_ollama(
    model_id: str,
    messages: list[dict[str, str]],
    system_prompt: Optional[str],
    max_tokens: int,
) -> AsyncIterator[str]:
    """Streaming via Ollama REST API (/api/chat)."""
    payload: dict = {
        "model": model_id,
        "messages": messages,
        "stream": True,
        "options": {"num_predict": max_tokens},
    }
    if system_prompt:
        # Ollama acepta system como primer mensaje o en options
        payload["messages"] = [{"role": "system", "content": system_prompt}] + messages

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    # Ollama devuelve: {"message": {"content": "..."}, "done": false}
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue


# ══════════════════════════════════════════════════════════════
# LLAMADA SIMPLE (sin streaming) — Para extracción de metadatos
# ══════════════════════════════════════════════════════════════

async def complete(
    model_id: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 1024,
) -> str:
    """
    Genera una respuesta completa (sin streaming) para tareas de procesamiento.

    Args:
        model_id: Identificador del modelo.
        prompt: Texto del prompt de usuario.
        system_prompt: Instrucción de sistema.
        max_tokens: Límite de tokens.

    Returns:
        Texto completo de la respuesta.
    """
    messages = [{"role": "user", "content": prompt}]
    result = ""
    async for chunk in stream_chat(model_id, messages, system_prompt, max_tokens):
        result += chunk
    return result
