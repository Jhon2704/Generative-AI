"""
Sidebar de conversaciones para CONSTELLATION.
Agrupa los chats por proyecto con secciones desplegables.
"""
from __future__ import annotations

import reflex as rx

from ..state.app_state import AppState
from ..models import SidebarItem


def _project_header(item: SidebarItem) -> rx.Component:
    """Cabecera de sección de proyecto — clicable para colapsar/expandir."""
    return rx.box(
        rx.hstack(
            # Pastilla de color del proyecto
            rx.box(
                width="3px",
                height="14px",
                background=item.project_color,
                border_radius="2px",
                flex_shrink="0",
            ),
            # Emoji + nombre
            rx.text(
                rx.cond(
                    item.project_emoji != "",
                    item.project_emoji + " " + item.project_name,
                    item.project_name,
                ),
                font_size="10px",
                font_weight="700",
                color="#666666",
                text_transform="uppercase",
                letter_spacing="0.09em",
                font_family="Barlow Condensed, sans-serif",
                flex="1",
                no_of_lines=1,
            ),
            # Contador
            rx.box(
                rx.text(
                    item.conv_count,
                    font_size="10px",
                    color="#555555",
                    font_family="Barlow, sans-serif",
                    line_height="1",
                ),
                background="#161616",
                border="1px solid #1e1e1e",
                border_radius="10px",
                padding="1px 7px",
            ),
            # Chevron
            rx.cond(
                item.is_collapsed,
                rx.icon("chevron-right", size=11, color="#444444"),
                rx.icon("chevron-down", size=11, color="#444444"),
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        on_click=AppState.toggle_project_collapse(item.project_id),
        padding="10px 10px 5px",
        margin_top="2px",
        cursor="pointer",
        border_radius="4px",
        _hover={"background": "rgba(255,255,255,0.025)"},
        transition="background 0.1s",
        width="100%",
    )


def _conv_item(item: SidebarItem) -> rx.Component:
    """Ítem de conversación dentro de un grupo de proyecto."""
    is_active = AppState.current_conversation_id == item.id
    return rx.box(
        rx.hstack(
            # Línea vertical del color del proyecto
            rx.box(
                width="2px",
                height="32px",
                background=rx.cond(
                    is_active,
                    "#E2001A",
                    item.project_color,
                ),
                border_radius="1px",
                flex_shrink="0",
                opacity=rx.cond(is_active, "1", "0.35"),
            ),
            # Título + icono privacidad
            rx.text(
                item.title,
                font_size="12px",
                font_weight=rx.cond(is_active, "500", "400"),
                color=rx.cond(is_active, "#f0f0f0", "#b0b0b0"),
                no_of_lines=1,
                flex="1",
                font_family="Barlow, sans-serif",
            ),
            rx.cond(
                item.privacy == "public",
                rx.icon("eye", size=11, color="#555555"),
                rx.box(),
            ),
            # Botón eliminar
            rx.box(
                rx.icon_button(
                    rx.icon("trash-2", size=11),
                    size="1",
                    variant="ghost",
                    color_scheme="gray",
                    on_click=AppState.delete_conversation(item.id),
                    _hover={"color": "#E2001A", "background": "transparent"},
                ),
                on_click=rx.stop_propagation,
            ),
            spacing="2",
            align="center",
            width="100%",
            padding="4px 8px 4px 6px",
        ),
        on_click=AppState.select_conversation(item.id),
        cursor="pointer",
        border_radius="5px",
        background=rx.cond(is_active, "#161616", "transparent"),
        _hover={"background": "#111111"},
        transition="all 0.1s ease",
        width="100%",
        margin_left="10px",
        margin_right="4px",
    )


def _sidebar_row(item: SidebarItem) -> rx.Component:
    """Renderiza header o conversación según item_type."""
    return rx.cond(
        item.item_type == "header",
        _project_header(item),
        _conv_item(item),
    )


def sidebar() -> rx.Component:
    """Panel lateral con conversaciones agrupadas por proyecto."""
    return rx.box(
        rx.vstack(
            # ── Header ────────────────────────────────────────
            rx.hstack(
                rx.text(
                    "Chats",
                    font_size="11px",
                    font_weight="600",
                    color="#555555",
                    text_transform="uppercase",
                    letter_spacing="0.1em",
                    font_family="Barlow Condensed, sans-serif",
                ),
                rx.spacer(),
                rx.icon_button(
                    rx.icon("pencil", size=14),
                    size="1",
                    variant="ghost",
                    color_scheme="gray",
                    on_click=AppState.new_conversation,
                    _hover={"color": "#E2001A"},
                    title="Nueva conversación",
                ),
                width="100%",
                align="center",
                padding="14px 14px 8px",
            ),

            # ── Buscador ──────────────────────────────────────
            rx.box(
                rx.input(
                    placeholder="Buscar...",
                    value=AppState.search_query,
                    on_change=AppState.set_search_query,
                    size="1",
                    background="#111111",
                    border="1px solid #1e1e1e",
                    color="#e5e5e5",
                    _placeholder={"color": "#444444"},
                    _focus={"border_color": "#E2001A", "outline": "none"},
                    border_radius="6px",
                    font_family="Barlow, sans-serif",
                    font_size="13px",
                ),
                padding="0 10px 8px",
                width="100%",
            ),

            # ── Lista agrupada ─────────────────────────────────
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        AppState.loading_conversations,
                        # Skeleton de carga
                        rx.vstack(
                            *[
                                rx.box(
                                    height="36px",
                                    background="#111111",
                                    border_radius="6px",
                                    width="100%",
                                )
                                for _ in range(5)
                            ],
                            spacing="2",
                            padding="0 8px",
                            width="100%",
                        ),
                        rx.cond(
                            AppState.sidebar_items,
                            rx.foreach(AppState.sidebar_items, _sidebar_row),
                            # Estado vacío
                            rx.center(
                                rx.vstack(
                                    rx.icon("message-square", size=24, color="#2a2a2a"),
                                    rx.text(
                                        "Sin conversaciones",
                                        font_size="12px",
                                        color="#333333",
                                        font_family="Barlow, sans-serif",
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                                padding_top="40px",
                                width="100%",
                            ),
                        ),
                    ),
                    spacing="0",
                    padding="0 4px 80px",
                    width="100%",
                ),
                type="scroll",
                height="calc(100vh - 120px)",
                scrollbars="vertical",
            ),

            spacing="0",
            width="100%",
        ),

        # ── Botón Nueva ────────────────────────────────────────
        rx.box(
            rx.button(
                rx.icon("plus", size=14),
                "Nueva",
                on_click=AppState.new_conversation,
                background="#E2001A",
                color="white",
                _hover={"background": "#c00015"},
                border_radius="6px",
                font_size="12px",
                font_family="Barlow Condensed, sans-serif",
                font_weight="600",
                height="30px",
                padding_x="10px",
                gap="5px",
                cursor="pointer",
            ),
            position="absolute",
            bottom="14px",
            left="50%",
            transform="translateX(-50%)",
            z_index="10",
        ),

        width="240px",
        min_width="240px",
        height="100vh",
        background="#0d0d0d",
        border_right="1px solid #1e1e1e",
        position="relative",
        overflow="hidden",
    )
