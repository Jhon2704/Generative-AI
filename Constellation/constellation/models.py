"""
Modelos de datos tipados para CONSTELLATION.
Usa dataclasses — compatible con Reflex >= 0.8.15 para rx.foreach.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProjectData:
    """Datos de un proyecto corporativo."""
    id: str = ""
    name: str = ""
    emoji: str = ""
    color: str = "#4f8ef7"
    shape: str = "circle"  # circle | square | diamond | hexagon | star


@dataclass
class ConvItem:
    """Conversación para mostrar en el sidebar."""
    id: str = ""
    title: str = ""
    privacy: str = "private"
    project_id: str = ""
    owner_id: str = ""
    model_used: str = ""
    updated_at: str = ""
    created_at: str = ""
    projects: Optional[ProjectData] = None


@dataclass
class SidebarItem:
    """Ítem plano para el sidebar agrupado. item_type: 'header' | 'conv'"""
    item_type: str = "conv"
    # Datos del proyecto (ambos tipos)
    project_id: str = ""
    project_name: str = ""
    project_emoji: str = ""
    project_color: str = "#333333"
    # Solo para headers
    conv_count: int = 0
    is_collapsed: bool = False
    # Solo para conversaciones
    id: str = ""
    title: str = ""
    privacy: str = "private"


@dataclass
class ConvData:
    """Datos mínimos de conversación anidados en un nodo."""
    id: str = ""
    title: str = ""
    privacy: str = "private"
    project_id: str = ""
    owner_id: str = ""
    projects: Optional[ProjectData] = None


@dataclass
class NodeItem:
    """Nodo del knowledge graph."""
    id: str = ""
    conversation_id: str = ""
    title: str = ""
    summary: str = ""
    tags: list = field(default_factory=list)
    semantic: str = ""
    pending: bool = True
    pos_x: float = 0.0
    pos_y: float = 0.0
    conversations: Optional[ConvData] = None


# ── Funciones de conversión ────────────────────────────────────

def conv_from_dict(d: dict) -> ConvItem:
    """Convierte un dict de Supabase en ConvItem."""
    proj = d.get("projects")
    return ConvItem(
        id=str(d.get("id", "")),
        title=str(d.get("title", "")),
        privacy=str(d.get("privacy", "private")),
        project_id=str(d.get("project_id") or ""),
        owner_id=str(d.get("owner_id", "")),
        model_used=str(d.get("model_used", "")),
        updated_at=str(d.get("updated_at", "")),
        created_at=str(d.get("created_at", "")),
        projects=ProjectData(
            id=str(proj.get("id", "")),
            name=str(proj.get("name", "")),
            emoji=str(proj.get("emoji", "")),
            color=str(proj.get("color", "#4f8ef7")),
            shape=str(proj.get("shape", "circle")),
        ) if isinstance(proj, dict) else None,
    )


def node_from_dict(d: dict) -> NodeItem:
    """Convierte un dict de Supabase en NodeItem."""
    conv = d.get("conversations")
    conv_data = None
    if isinstance(conv, dict):
        proj = conv.get("projects")
        conv_data = ConvData(
            id=str(conv.get("id", "")),
            title=str(conv.get("title", "")),
            privacy=str(conv.get("privacy", "private")),
            project_id=str(conv.get("project_id") or ""),
            owner_id=str(conv.get("owner_id", "")),
            projects=ProjectData(
                id=str(proj.get("id", "")),
                name=str(proj.get("name", "")),
                emoji=str(proj.get("emoji", "")),
                color=str(proj.get("color", "#4f8ef7")),
                shape=str(proj.get("shape", "circle")),
            ) if isinstance(proj, dict) else None,
        )

    raw_tags = d.get("tags", [])
    if isinstance(raw_tags, str):
        try:
            raw_tags = json.loads(raw_tags)
        except Exception:
            raw_tags = []
    tags = [str(t) for t in (raw_tags or [])]

    return NodeItem(
        id=str(d.get("id", "")),
        conversation_id=str(d.get("conversation_id", "")),
        title=str(d.get("title", "")),
        summary=str(d.get("summary", "")),
        tags=tags,
        semantic=str(d.get("semantic", "")),
        pending=bool(d.get("pending", True)),
        pos_x=float(d.get("pos_x") or 0),
        pos_y=float(d.get("pos_y") or 0),
        conversations=conv_data,
    )


def project_from_dict(d: dict) -> ProjectData:
    """Convierte un dict de Supabase en ProjectData."""
    return ProjectData(
        id=str(d.get("id", "")),
        name=str(d.get("name", "")),
        emoji=str(d.get("emoji", "📁")),
        color=str(d.get("color", "#4f8ef7")),
        shape=str(d.get("shape", "circle")),
    )
