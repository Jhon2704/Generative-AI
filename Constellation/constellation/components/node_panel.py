"""
Panel lateral de detalle de nodo para CONSTELLATION.
Muestra 3 tabs: Resumen, Chat completo y Conexiones relacionadas.
Usa NodeItem (rx.Base) para compatibilidad con Reflex.
"""
from __future__ import annotations

import reflex as rx

from ..state.graph_state import GraphState
from ..state.app_state import AppState
from ..models import NodeItem


def _tag_chip(tag: str) -> rx.Component:
    """Chip visual para un tag técnico."""
    return rx.badge(
        "#", tag,
        variant="soft",
        color_scheme="gray",
        font_family="DM Mono, monospace",
        font_size="10px",
        padding="2px 8px",
        border_radius="4px",
        border="1px solid #2a2a2a",
    )


def _tab_button(label: str, tab_id: str, icon_name: str) -> rx.Component:
    """Botón de tab con icono."""
    is_active = GraphState.selected_tab == tab_id
    return rx.button(
        rx.hstack(
            rx.icon(icon_name, size=12),
            rx.text(label, font_size="11px"),
            spacing="1",
            align="center",
        ),
        on_click=GraphState.set_selected_tab(tab_id),
        background=rx.cond(is_active, "#1e1e1e", "transparent"),
        color=rx.cond(is_active, "#e5e5e5", "#666666"),
        border_bottom=rx.cond(is_active, "2px solid #E2001A", "2px solid transparent"),
        border_radius="0",
        font_family="Barlow Condensed, sans-serif",
        font_weight="600",
        letter_spacing="0.04em",
        height="36px",
        padding_x="12px",
        cursor="pointer",
        flex="1",
        _hover={"color": "#e5e5e5", "background": "#111111"},
        transition="all 0.1s",
    )


def _summary_tab() -> rx.Component:
    """Tab de resumen del nodo con atributos de NodeItem."""
    node = GraphState.selected_node
    return rx.vstack(
        # Proyecto
        rx.cond(
            node.conversations != None,
            rx.cond(
                node.conversations.projects != None,
                rx.hstack(
                    rx.text(node.conversations.projects.emoji, font_size="14px"),
                    rx.text(
                        node.conversations.projects.name,
                        font_size="12px",
                        color="#888888",
                        font_family="Barlow, sans-serif",
                    ),
                    rx.badge(
                        rx.cond(
                            node.conversations.privacy == "public",
                            "Público",
                            "Privado",
                        ),
                        size="1",
                        variant="soft",
                        color_scheme=rx.cond(
                            node.conversations.privacy == "public",
                            "green",
                            "gray",
                        ),
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.box(),
            ),
            rx.box(),
        ),

        # Resumen
        rx.text(
            "Resumen",
            font_size="10px", font_weight="600", color="#555555",
            text_transform="uppercase", letter_spacing="0.08em",
            font_family="Barlow Condensed, sans-serif", margin_top="8px",
        ),
        rx.cond(
            node.pending,
            rx.hstack(
                rx.spinner(size="1", color="#E2001A"),
                rx.text("Extrayendo metadatos...", font_size="13px", color="#555555",
                        font_style="italic", font_family="Barlow, sans-serif"),
                spacing="2", align="center",
            ),
            rx.text(
                node.summary,
                font_size="13px", color="#cccccc",
                line_height="1.6", font_family="Barlow, sans-serif",
            ),
        ),

        # Tags
        rx.cond(
            node.tags.length() > 0,
            rx.vstack(
                rx.text(
                    "Tags",
                    font_size="10px", font_weight="600", color="#555555",
                    text_transform="uppercase", letter_spacing="0.08em",
                    font_family="Barlow Condensed, sans-serif", margin_top="8px",
                ),
                rx.flex(
                    rx.foreach(node.tags, _tag_chip),
                    flex_wrap="wrap", gap="4px",
                ),
                spacing="2", align_items="flex-start", width="100%",
            ),
            rx.box(),
        ),

        # Botón abrir en chat
        rx.cond(
            node.conversations != None,
            rx.button(
                rx.icon("message-circle", size=13),
                "Abrir en chat",
                on_click=AppState.select_conversation(node.conversations.id),
                background="#E2001A", color="white",
                _hover={"background": "#c00015"},
                border_radius="6px", font_size="12px",
                font_family="Barlow Condensed, sans-serif", font_weight="600",
                height="32px", padding_x="12px", gap="6px",
                margin_top="12px", cursor="pointer", width="100%",
            ),
            rx.box(),
        ),

        spacing="2", align_items="flex-start", width="100%", padding="16px",
    )


def _related_node_item(node: NodeItem) -> rx.Component:
    """Ítem de nodo relacionado."""
    color = rx.cond(
        node.conversations != None,
        rx.cond(
            node.conversations.projects != None,
            node.conversations.projects.color,
            "#4f8ef7",
        ),
        "#4f8ef7",
    )
    return rx.box(
        rx.hstack(
            rx.box(width="6px", height="6px", border_radius="50%",
                   background=color, flex_shrink="0", margin_top="3px"),
            rx.vstack(
                rx.text(node.title, font_size="12px", font_weight="500",
                        color="#e5e5e5", no_of_lines=2, font_family="Barlow, sans-serif"),
                rx.text(node.summary, font_size="11px", color="#666666",
                        no_of_lines=2, font_family="Barlow, sans-serif"),
                spacing="1", align_items="flex-start", flex="1",
            ),
            spacing="2", align="start", width="100%",
        ),
        on_click=GraphState.select_node(node.id),
        padding="10px 12px", border_radius="6px",
        border="1px solid #1e1e1e", background="#111111",
        cursor="pointer", _hover={"border_color": "#E2001A", "background": "#161616"},
        transition="all 0.15s", width="100%",
    )


def node_panel() -> rx.Component:
    """Panel lateral deslizable de detalle de nodo."""
    return rx.cond(
        GraphState.panel_open & (GraphState.selected_node != None),
        rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.text(
                        GraphState.selected_node.title,
                        font_size="15px", font_weight="700", color="#e5e5e5",
                        font_family="Barlow Condensed, sans-serif",
                        letter_spacing="0.03em", no_of_lines=2,
                        flex="1",
                    ),
                    rx.icon_button(
                        rx.icon("x", size=14), size="1", variant="ghost",
                        color_scheme="gray", on_click=GraphState.close_panel,
                        _hover={"color": "#E2001A"},
                    ),
                    spacing="2", align="start", width="100%",
                    padding="16px 16px 0",
                ),

                # Tabs
                rx.hstack(
                    _tab_button("Resumen", "summary", "file-text"),
                    _tab_button("Chat", "chat", "message-square"),
                    _tab_button("Conexiones", "related", "network"),
                    spacing="0", width="100%",
                    border_bottom="1px solid #1e1e1e",
                ),

                # Contenido
                rx.scroll_area(
                    rx.cond(
                        GraphState.selected_tab == "summary",
                        _summary_tab(),
                        rx.cond(
                            GraphState.selected_tab == "chat",
                            rx.vstack(
                                rx.text("Historial de la conversación.", font_size="12px",
                                        color="#555555", font_style="italic",
                                        font_family="Barlow, sans-serif", padding="16px 16px 0"),
                                rx.cond(
                                    GraphState.selected_node.conversations != None,
                                    rx.button(
                                        "Abrir chat completo →",
                                        on_click=AppState.select_conversation(
                                            GraphState.selected_node.conversations.id
                                        ),
                                        background="transparent", color="#E2001A",
                                        _hover={"color": "#ff1a33"}, border="none",
                                        font_size="13px", font_family="Barlow, sans-serif",
                                        cursor="pointer", padding="8px 16px",
                                        text_decoration="underline",
                                    ),
                                    rx.box(),
                                ),
                                spacing="0", width="100%",
                            ),
                            # Tab relacionados
                            rx.cond(
                                GraphState.related_nodes,
                                rx.vstack(
                                    rx.foreach(GraphState.related_nodes, _related_node_item),
                                    spacing="2", width="100%", padding="16px",
                                ),
                                rx.center(
                                    rx.vstack(
                                        rx.icon("network", size=28, color="#333333"),
                                        rx.text("Sin conexiones semánticas",
                                                font_size="13px", color="#555555",
                                                font_family="Barlow, sans-serif"),
                                        spacing="2", align="center",
                                    ),
                                    padding="32px 16px", width="100%",
                                ),
                            ),
                        ),
                    ),
                    type="scroll", flex="1", width="100%", scrollbars="vertical",
                ),

                spacing="0", height="100%", width="100%",
            ),

            width="300px", min_width="300px", height="100%",
            background="#0d0d0d", border_left="1px solid #1e1e1e",
            z_index="20", animation="slideIn 0.2s ease",
        ),
        rx.box(),
    )
