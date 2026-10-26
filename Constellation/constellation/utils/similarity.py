"""
Cálculo de similitud semántica entre nodos del knowledge graph.
Usa similitud de Jaccard sobre sets de palabras clave.
No requiere modelos de embeddings externos.
"""
from __future__ import annotations

import re
import json
from typing import Optional


# ── Stopwords en español e inglés para filtrar ────────────────
STOPWORDS: set[str] = {
    # Español
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "en", "a", "y", "o", "que", "por", "para",
    "con", "se", "su", "sus", "es", "son", "fue", "ser",
    "como", "más", "pero", "si", "no", "este", "esta", "esto",
    "muy", "al", "le", "lo", "ya", "también", "sobre", "entre",
    # Inglés
    "the", "a", "an", "of", "in", "to", "and", "or", "for",
    "with", "on", "at", "by", "from", "as", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "may",
    "might", "it", "its", "this", "that", "these", "those",
    "we", "you", "he", "she", "they", "i", "my", "our",
}

# Mínima similitud Jaccard para crear una conexión "weak"
JACCARD_THRESHOLD = 0.15


def tokenize(text: str) -> set[str]:
    """
    Tokeniza un texto en un set de palabras normalizadas.
    Elimina puntuación, convierte a minúsculas y filtra stopwords.

    Args:
        text: Texto libre (semantic field del nodo, tags concatenados, etc.).

    Returns:
        Set de tokens relevantes.
    """
    if not text:
        return set()

    # Normalizar: minúsculas, quitar puntuación excepto guiones
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)

    tokens = set(text.split())
    # Filtrar stopwords y tokens muy cortos
    return {t for t in tokens if t not in STOPWORDS and len(t) > 2}


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """
    Calcula la similitud de Jaccard entre dos sets de tokens.

    J(A, B) = |A ∩ B| / |A ∪ B|

    Args:
        set_a: Set de tokens del nodo A.
        set_b: Set de tokens del nodo B.

    Returns:
        Puntuación en [0.0, 1.0]. 0 = sin similitud, 1 = idénticos.
    """
    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return intersection / union if union > 0 else 0.0


def node_tokens(node: dict) -> set[str]:
    """
    Extrae todos los tokens relevantes de un nodo del grafo.
    Combina campo semantic, title y tags para maximizar señal.

    Args:
        node: Diccionario del nodo con campos title, summary, tags, semantic.

    Returns:
        Set combinado de tokens.
    """
    parts: list[str] = []

    # Campo semántico (mayor peso conceptual)
    if node.get("semantic"):
        parts.append(str(node["semantic"]))

    # Título (alta relevancia)
    if node.get("title"):
        parts.append(str(node["title"]))
        # Añadir el título dos veces para darle más peso
        parts.append(str(node["title"]))

    # Tags (términos técnicos precisos)
    tags = node.get("tags", [])
    if isinstance(tags, str):
        # A veces llega como JSON string desde Supabase
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    if tags:
        # Añadir los tags dos veces por precisión
        tags_text = " ".join(str(t) for t in tags)
        parts.append(tags_text)
        parts.append(tags_text)

    combined = " ".join(parts)
    return tokenize(combined)


def calculate_connections(
    nodes: list[dict],
) -> list[dict[str, object]]:
    """
    Calcula todas las conexiones entre nodos del grafo.

    Genera:
    - Conexiones 'strong': entre nodos del mismo proyecto (score=1.0).
    - Conexiones 'weak': similitud Jaccard ≥ JACCARD_THRESHOLD.

    Args:
        nodes: Lista de nodos con campos id, conversation_id, title,
               summary, tags, semantic, y conversations.project_id.

    Returns:
        Lista de dicts con source_id, target_id, strength, score.
    """
    connections: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()  # Para evitar duplicados

    # Pre-calcular tokens de cada nodo
    tokens_map: dict[str, set[str]] = {
        node["id"]: node_tokens(node) for node in nodes
    }

    def get_project_id(node: dict) -> Optional[str]:
        """Extrae project_id de la relación anidada conversations."""
        conv = node.get("conversations") or {}
        return conv.get("project_id")

    for i, node_a in enumerate(nodes):
        for node_b in nodes[i + 1 :]:
            id_a = node_a["id"]
            id_b = node_b["id"]

            # Evitar duplicados bidireccionales
            key = tuple(sorted([id_a, id_b]))
            if key in seen:
                continue
            seen.add(key)

            proj_a = get_project_id(node_a)
            proj_b = get_project_id(node_b)

            # ── Conexión fuerte: mismo proyecto ───────────────
            if proj_a and proj_b and proj_a == proj_b:
                connections.append({
                    "source_id": id_a,
                    "target_id": id_b,
                    "strength": "strong",
                    "score": 1.0,
                })
                continue  # No calcular Jaccard si ya hay conexión strong

            # ── Conexión débil: similitud Jaccard ─────────────
            tokens_a = tokens_map.get(id_a, set())
            tokens_b = tokens_map.get(id_b, set())
            score = jaccard_similarity(tokens_a, tokens_b)

            if score >= JACCARD_THRESHOLD:
                connections.append({
                    "source_id": id_a,
                    "target_id": id_b,
                    "strength": "weak",
                    "score": round(score, 4),
                })

    return connections


def calculate_connections_for_node(
    new_node: dict,
    existing_nodes: list[dict],
) -> list[dict]:
    """
    Calcula conexiones de UN nodo nuevo vs todos los existentes.
    O(n) en lugar de O(n²) — para uso en background al crear un nodo.

    Args:
        new_node: El nodo recién creado/actualizado.
        existing_nodes: Todos los nodos ya en el grafo (puede incluir el nuevo).

    Returns:
        Lista de conexiones con source_id, target_id, strength, score.
    """
    connections: list[dict] = []
    new_id = new_node["id"]
    new_tokens = node_tokens(new_node)
    new_proj = (new_node.get("conversations") or {}).get("project_id")

    for node in existing_nodes:
        if node["id"] == new_id:
            continue

        node_proj = (node.get("conversations") or {}).get("project_id")

        if new_proj and node_proj and new_proj == node_proj:
            connections.append({
                "source_id": new_id,
                "target_id": node["id"],
                "strength": "strong",
                "score": 1.0,
            })
        else:
            score = jaccard_similarity(new_tokens, node_tokens(node))
            if score >= JACCARD_THRESHOLD:
                connections.append({
                    "source_id": new_id,
                    "target_id": node["id"],
                    "strength": "weak",
                    "score": round(score, 4),
                })

    return connections


def find_related_nodes(
    target_node: dict,
    all_nodes: list[dict],
    top_k: int = 5,
    min_score: float = JACCARD_THRESHOLD,
) -> list[dict[str, object]]:
    """
    Encuentra los nodos más relacionados con un nodo dado.

    Útil para el panel lateral "Conexiones relacionadas".

    Args:
        target_node: Nodo de referencia.
        all_nodes: Todos los nodos visibles.
        top_k: Número máximo de nodos a devolver.
        min_score: Puntuación mínima de similitud.

    Returns:
        Lista de dicts con 'node' y 'score', ordenados por similitud descendente.
    """
    target_tokens = node_tokens(target_node)
    target_id = target_node.get("id")

    scored: list[tuple[float, dict]] = []

    for node in all_nodes:
        if node.get("id") == target_id:
            continue  # Excluir el nodo de referencia

        score = jaccard_similarity(target_tokens, node_tokens(node))
        if score >= min_score:
            scored.append((score, node))

    # Ordenar por score descendente
    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {"node": node, "score": round(score, 4)}
        for score, node in scored[:top_k]
    ]
