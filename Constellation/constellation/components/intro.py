"""
Pantalla de introducción para nueva conversación en CONSTELLATION.
Permite configurar título, proyecto y privacidad antes de chatear.
"""
from __future__ import annotations

import reflex as rx

from ..state.app_state import AppState
from ..state.graph_state import GraphState


def _privacy_card(
    label: str,
    description: str,
    icon: str,
    value: str,
    color: str,
) -> rx.Component:
    """
    Tarjeta grande de selección de privacidad.

    Args:
        label: Texto principal ('Público' / 'Privado').
        description: Descripción breve de la opción.
        icon: Nombre del icono de Lucide.
        value: Valor ('public' / 'private').
        color: Color del acento cuando está seleccionado.
    """
    is_selected = AppState.intro_privacy == value

    return rx.box(
        rx.vstack(
            rx.icon(
                icon,
                size=28,
                color=rx.cond(is_selected, color, "#555555"),
            ),
            rx.text(
                label,
                font_size="16px",
                font_weight="700",
                color=rx.cond(is_selected, "#e5e5e5", "#777777"),
                font_family="Barlow Condensed, sans-serif",
                letter_spacing="0.05em",
            ),
            rx.text(
                description,
                font_size="12px",
                color=rx.cond(is_selected, "#aaaaaa", "#555555"),
                text_align="center",
                font_family="Barlow, sans-serif",
            ),
            spacing="2",
            align="center",
            padding="20px 16px",
        ),
        on_click=lambda: AppState.set_intro_privacy(value),
        width="100%",
        flex="1",
        border_radius="10px",
        border=rx.cond(
            is_selected,
            f"2px solid {color}",
            "2px solid #1e1e1e",
        ),
        background=rx.cond(
            is_selected,
            "#111111",
            "#0d0d0d",
        ),
        cursor="pointer",
        _hover={"border_color": color, "background": "#111111"},
        transition="all 0.15s",
    )


def intro_screen() -> rx.Component:
    """
    Pantalla de configuración inicial de conversación.
    Se muestra al crear una nueva conversación antes del primer mensaje.
    """
    return rx.cond(
        AppState.show_intro,
        rx.center(
            rx.vstack(
                # ── Icono y título ─────────────────────────────
                rx.vstack(
                    rx.text(
                        "✦",
                        font_size="32px",
                        color="#E2001A",
                    ),
                    rx.text(
                        "Nueva conversación",
                        font_size="24px",
                        font_weight="700",
                        color="#e5e5e5",
                        font_family="Barlow Condensed, sans-serif",
                        letter_spacing="0.1em",
                    ),
                    rx.text(
                        "Esta conversación generará un nodo en el knowledge graph.",
                        font_size="13px",
                        color="#555555",
                        font_family="Barlow, sans-serif",
                    ),
                    spacing="2",
                    align="center",
                ),

                # ── Formulario ─────────────────────────────────
                rx.vstack(
                    # Título
                    rx.vstack(
                        rx.text(
                            "Título",
                            font_size="11px",
                            font_weight="600",
                            color="#666666",
                            text_transform="uppercase",
                            letter_spacing="0.08em",
                            font_family="Barlow Condensed, sans-serif",
                        ),
                        rx.input(
                            placeholder="¿Sobre qué es esta conversación?",
                            value=AppState.intro_title,
                            on_change=AppState.set_intro_title,
                            background="#111111",
                            border="1px solid #1e1e1e",
                            color="#e5e5e5",
                            _placeholder={"color": "#444444"},
                            _focus={
                                "border_color": "#E2001A",
                                "outline": "none",
                                "box_shadow": "none",
                            },
                            border_radius="8px",
                            font_family="Barlow, sans-serif",
                            font_size="14px",
                            height="42px",
                            width="100%",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="flex-start",
                    ),

                    # Proyecto
                    rx.vstack(
                        rx.text(
                            "Proyecto",
                            font_size="11px",
                            font_weight="600",
                            color="#666666",
                            text_transform="uppercase",
                            letter_spacing="0.08em",
                            font_family="Barlow Condensed, sans-serif",
                        ),
                        rx.select.root(
                            rx.select.trigger(
                                placeholder="Sin proyecto asignado",
                                background="#111111",
                                border="1px solid #1e1e1e",
                                color="#e5e5e5",
                                _placeholder={"color": "#444444"},
                                _focus={
                                    "border_color": "#E2001A",
                                    "outline": "none",
                                },
                                border_radius="8px",
                                height="42px",
                                font_family="Barlow, sans-serif",
                                font_size="14px",
                                width="100%",
                            ),
                            rx.select.content(
                                rx.select.item("Sin proyecto", value="__none__"),
                                rx.select.separator(),
                                rx.foreach(
                                    GraphState.projects,
                                    lambda p: rx.select.item(
                                        rx.hstack(
                                            rx.text(p.emoji),
                                            rx.text(p.name, font_family="Barlow, sans-serif"),
                                            spacing="2",
                                        ),
                                        value=p.id,
                                    ),
                                ),
                                background="#111111",
                                border="1px solid #1e1e1e",
                            ),
                            value=AppState.intro_project_id,
                            on_change=AppState.set_intro_project_id,
                            width="100%",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="flex-start",
                    ),

                    # Privacidad
                    rx.vstack(
                        rx.text(
                            "Visibilidad",
                            font_size="11px",
                            font_weight="600",
                            color="#666666",
                            text_transform="uppercase",
                            letter_spacing="0.08em",
                            font_family="Barlow Condensed, sans-serif",
                        ),
                        rx.hstack(
                            _privacy_card(
                                label="Privado",
                                description="Solo tú puedes ver esta conversación",
                                icon="lock",
                                value="private",
                                color="#888888",
                            ),
                            _privacy_card(
                                label="Público",
                                description="Todo el equipo puede verlo en el grafo",
                                icon="globe",
                                value="public",
                                color="#22c55e",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        spacing="1",
                        width="100%",
                        align_items="flex-start",
                    ),

                    spacing="4",
                    width="100%",
                ),

                # ── Botones de acción ──────────────────────────
                rx.hstack(
                    rx.button(
                        "Cancelar",
                        on_click=AppState.set_show_intro_false,
                        background="transparent",
                        color="#666666",
                        border="1px solid #1e1e1e",
                        border_radius="8px",
                        height="42px",
                        padding_x="20px",
                        cursor="pointer",
                        _hover={"border_color": "#333333", "color": "#e5e5e5"},
                        font_family="Barlow, sans-serif",
                    ),
                    rx.button(
                        rx.icon("arrow-right", size=14),
                        "Comenzar conversación",
                        on_click=AppState.start_conversation,
                        background="#E2001A",
                        color="white",
                        _hover={"background": "#c00015"},
                        border_radius="8px",
                        height="42px",
                        padding_x="20px",
                        gap="8px",
                        cursor="pointer",
                        font_family="Barlow Condensed, sans-serif",
                        font_weight="600",
                        letter_spacing="0.05em",
                        flex="1",
                    ),
                    spacing="3",
                    width="100%",
                    justify="end",
                ),

                spacing="6",
                max_width="480px",
                width="100%",
                padding="32px",
                background="#0d0d0d",
                border="1px solid #1e1e1e",
                border_radius="16px",
            ),
            height="100%",
            width="100%",
            background="#0a0a0a",
        ),
        rx.box(),  # Nada si no se muestra la pantalla intro
    )
