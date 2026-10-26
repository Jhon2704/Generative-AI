"""
Extractor de metadatos para nodos del knowledge graph.
Usa Claude Haiku (rápido y económico) para analizar conversaciones
y extraer título, resumen, tags y descripción semántica.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from .ai_service import complete, MODEL_HAIKU


# ── Prompt del sistema para extracción de metadatos ───────────
EXTRACTION_SYSTEM = """Eres un asistente especializado en extraer metadatos de conversaciones
corporativas para un knowledge graph. Debes responder SIEMPRE con JSON válido, sin texto adicional.

Tu respuesta debe seguir exactamente esta estructura:
{
  "title": "Título conciso y descriptivo (máx 60 caracteres)",
  "summary": "Resumen de 2-3 frases que capture el tema principal y las conclusiones clave.",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "semantic": "Texto denso en palabras clave que represente el contenido semántico para calcular similitud con otras conversaciones. Incluye conceptos, tecnologías, metodologías y dominio."
}

Reglas:
- El título debe ser específico, no genérico (no "Conversación sobre X")
- Los tags deben ser términos técnicos o de dominio en minúsculas, sin espacios (usa guiones)
- El campo semantic es para búsqueda de similitud: incluye sinónimos y términos relacionados
- Si la conversación es sobre código, incluye el lenguaje y frameworks en los tags
- Responde siempre en español, excepto para tags técnicos que deben estar en inglés
"""


async def extract_metadata(
    conversation_text: str,
    model_id: str = MODEL_HAIKU,
) -> dict[str, object]:
    """
    Extrae metadatos de una conversación completa.

    Analiza el texto de la conversación y devuelve un diccionario
    con título, resumen, tags y descripción semántica listos para
    guardar en la tabla `nodes` de Supabase.

    Args:
        conversation_text: Texto completo de la conversación (todos los mensajes).
        model_id: Modelo a usar para la extracción (por defecto Haiku por velocidad).

    Returns:
        Diccionario con:
            - title (str): Título de máx 60 caracteres.
            - summary (str): Resumen de 2-3 frases.
            - tags (list[str]): Lista de 3-7 tags técnicos.
            - semantic (str): Texto semántico para calcular similitud.
            - error (Optional[str]): Mensaje de error si falló la extracción.
    """
    # Truncar si la conversación es muy larga (limite ~3000 tokens input)
    max_chars = 8000
    if len(conversation_text) > max_chars:
        conversation_text = conversation_text[:max_chars] + "\n...[conversación truncada]"

    prompt = f"""Analiza esta conversación y extrae sus metadatos:

--- CONVERSACIÓN ---
{conversation_text}
--- FIN ---

Responde con el JSON de metadatos:"""

    try:
        response = await complete(
            model_id=model_id,
            prompt=prompt,
            system_prompt=EXTRACTION_SYSTEM,
            max_tokens=512,
        )

        # Intentar parsear el JSON de la respuesta
        metadata = _parse_json_response(response)
        metadata["error"] = None
        return metadata

    except Exception as e:
        # Fallback con metadatos mínimos
        return _fallback_metadata(conversation_text, str(e))


def _parse_json_response(response: str) -> dict[str, object]:
    """
    Parsea la respuesta JSON del modelo, tolerante a markdown code blocks.

    El modelo a veces envuelve el JSON en ```json ... ```, lo limpiamos.
    """
    # Eliminar posibles bloques markdown
    clean = response.strip()
    if clean.startswith("```"):
        # Buscar el JSON entre los backticks
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", clean)
        if match:
            clean = match.group(1)

    # Parsear JSON
    data = json.loads(clean)

    # Normalizar campos
    return {
        "title":    str(data.get("title", "Sin título"))[:60],
        "summary":  str(data.get("summary", "")),
        "tags":     list(data.get("tags", []))[:7],  # Máximo 7 tags
        "semantic": str(data.get("semantic", "")),
    }


def _fallback_metadata(text: str, error: str) -> dict[str, object]:
    """
    Genera metadatos mínimos cuando falla la extracción por IA.
    Usa las primeras palabras del texto como título.
    """
    # Extraer las primeras 60 caracteres como título de emergencia
    words = text.replace("\n", " ").split()
    title = " ".join(words[:8])[:60]
    if len(title) < len(" ".join(words[:8])):
        title += "..."

    return {
        "title":    title or "Conversación sin título",
        "summary":  "Metadatos en proceso de extracción.",
        "tags":     [],
        "semantic": text[:500],  # Primeros 500 chars como semántica de emergencia
        "error":    f"Extracción fallida: {error}",
    }


def format_conversation_for_extraction(
    messages: list[dict[str, str]]
) -> str:
    """
    Convierte la lista de mensajes al formato de texto para el extractor.

    Args:
        messages: Lista de dicts [{"role": "user"|"assistant", "content": "..."}].

    Returns:
        Texto formateado con prefijos de rol.
    """
    lines = []
    for msg in messages:
        role = "Usuario" if msg.get("role") == "user" else "Asistente"
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n\n".join(lines)
