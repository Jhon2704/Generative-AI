"""
Componente de chat para CONSTELLATION.
Muestra el historial de mensajes con streaming, selector de modelo
y toggle de privacidad.
"""
from __future__ import annotations

import reflex as rx

from ..state.app_state import AppState
from ..state.auth_state import AuthState


def _model_badge(model_id: str) -> rx.Component:
    """Badge pequeño que indica el modelo usado en un mensaje."""
    labels = {
        "claude-sonnet-4-6":        "Sonnet 4",
        "claude-haiku-4-5-20251001": "Haiku",
        "mistral":                   "Mistral",
        "llama3":                    "Llama 3",
    }
    label = labels.get(model_id, model_id)
    return rx.badge(
        label,
        size="1",
        variant="outline",
        color_scheme="gray",
        font_family="DM Mono, monospace",
        font_size="10px",
    )


def _message_bubble(msg: dict) -> rx.Component:
    """
    Burbuja de mensaje individual.

    Args:
        msg: Dict con role, content y opcionalmente streaming.
    """
    is_user = msg.get("role") == "user"
    is_streaming = msg.get("streaming", False)

    return rx.box(
        rx.vstack(
            # ── Contenido del mensaje ──────────────────────────
            rx.box(
                rx.markdown(
                    msg["content"],
                    component_map={
                        "code": lambda text, **props: rx.code(
                            text,
                            font_family="DM Mono, monospace",
                            font_size="12px",
                            background="#1a1a1a",
                            color="#e5e5e5",
                            padding="1px 6px",
                            border_radius="3px",
                        ),
                        "pre": lambda children, **props: rx.box(
                            children,
                            background="#111111",
                            border="1px solid #1e1e1e",
                            border_radius="8px",
                            padding="16px",
                            overflow_x="auto",
                            font_family="DM Mono, monospace",
                            font_size="12px",
                            margin_y="8px",
                        ),
                    },
                    color="#e5e5e5",
                    font_size="14px",
                    line_height="1.6",
                    font_family="Barlow, sans-serif",
                ),
                padding="12px 16px",
                background=rx.cond(
                    is_user,
                    "#E2001A",
                    "#111111",
                ),
                border_radius=rx.cond(
                    is_user,
                    "18px 18px 4px 18px",
                    "18px 18px 18px 4px",
                ),
                border=rx.cond(
                    is_user,
                    "none",
                    "1px solid #1e1e1e",
                ),
                max_width="680px",
            ),

            # ── Cursor parpadeante si está en streaming ────────
            rx.cond(
                is_streaming,
                rx.box(
                    width="8px",
                    height="16px",
                    background="#E2001A",
                    border_radius="2px",
                    animation="blink 1s step-end infinite",
                    margin_top="-4px",
                ),
                rx.box(),
            ),

            spacing="1",
            align_items=rx.cond(is_user, "flex-end", "flex-start"),
        ),
        display="flex",
        justify_content=rx.cond(is_user, "flex-end", "flex-start"),
        width="100%",
        padding_x="24px",
        padding_y="4px",
    )


def _model_selector() -> rx.Component:
    """
    Selector de modelo de IA con soporte para Claude y Ollama.
    Solo muestra los modelos disponibles según el entorno.
    """
    return rx.select.root(
        rx.select.trigger(
            placeholder="Modelo",
            background="transparent",
            border="1px solid #1e1e1e",
            color="#888888",
            font_size="12px",
            font_family="DM Mono, monospace",
            height="32px",
            _hover={"border_color": "#333333"},
            _focus={"border_color": "#E2001A", "outline": "none"},
            border_radius="6px",
            padding_x="8px",
            min_width="160px",
        ),
        rx.select.content(
            rx.foreach(
                AppState.available_models,
                lambda m: rx.select.item(
                    rx.text(m["label"], font_size="12px", font_family="Barlow, sans-serif"),
                    value=m["id"],
                ),
            ),
            background="#111111",
            border="1px solid #1e1e1e",
        ),
        value=AppState.active_model,
        on_change=AppState.set_active_model,
    )


def _privacy_toggle() -> rx.Component:
    """Toggle público/privado para la conversación activa."""
    return rx.button(
        rx.cond(
            AppState.is_private,
            rx.hstack(
                rx.icon("lock", size=13, color="#888888"),
                rx.text("Privado", font_size="12px", color="#888888"),
                spacing="1",
                align="center",
            ),
            rx.hstack(
                rx.icon("globe", size=13, color="#22c55e"),
                rx.text("Público", font_size="12px", color="#22c55e"),
                spacing="1",
                align="center",
            ),
        ),
        on_click=AppState.toggle_privacy,
        background="transparent",
        border="1px solid #1e1e1e",
        border_radius="6px",
        height="32px",
        padding_x="10px",
        cursor="pointer",
        _hover={"background": "#111111"},
        font_family="Barlow, sans-serif",
        display=rx.cond(
            AppState.current_conversation_id != "",
            "flex",
            "none",
        ),
    )


def _empty_state() -> rx.Component:
    """Pantalla vacía cuando no hay conversación seleccionada."""
    return rx.center(
        rx.vstack(
            rx.text(
                "✦",
                font_size="48px",
                color="#E2001A",
            ),
            rx.text(
                "CONSTELLATION",
                font_size="28px",
                font_weight="700",
                font_family="Barlow Condensed, sans-serif",
                color="#e5e5e5",
                letter_spacing="0.2em",
            ),
            rx.text(
                "Constellation Guide · Knowledge Graph",
                font_size="13px",
                color="#555555",
                font_family="Barlow, sans-serif",
            ),
            rx.button(
                rx.icon("plus", size=14),
                "Iniciar conversación",
                on_click=AppState.new_conversation,
                background="#E2001A",
                color="white",
                _hover={"background": "#c00015"},
                border_radius="8px",
                font_family="Barlow Condensed, sans-serif",
                font_weight="600",
                letter_spacing="0.05em",
                padding="0 20px",
                height="40px",
                margin_top="24px",
                gap="8px",
                cursor="pointer",
            ),
            spacing="2",
            align="center",
        ),
        height="100%",
        width="100%",
    )


def chat_panel() -> rx.Component:
    """
    Panel principal de chat.
    Incluye historial de mensajes, barra de herramientas superior e input.
    """
    return rx.vstack(
        # ── Toolbar superior ──────────────────────────────────
        rx.hstack(
            # Título de la conversación activa
            rx.cond(
                AppState.current_conversation_id != "",
                rx.text(
                    AppState.current_conv_title,
                    font_size="14px",
                    font_weight="600",
                    color="#e5e5e5",
                    font_family="Barlow Condensed, sans-serif",
                    letter_spacing="0.03em",
                    no_of_lines=1,
                    flex="1",
                ),
                rx.text(
                    "CONSTELLATION",
                    font_size="14px",
                    font_weight="600",
                    color="#444444",
                    font_family="Barlow Condensed, sans-serif",
                    letter_spacing="0.1em",
                    flex="1",
                ),
            ),
            _privacy_toggle(),
            _model_selector(),
            padding="12px 20px",
            border_bottom="1px solid #1a1a1a",
            background="#0a0a0a",
            align="center",
            width="100%",
            flex_shrink="0",
        ),

        # ── Área de mensajes ──────────────────────────────────
        rx.cond(
            AppState.current_conversation_id == "",
            _empty_state(),
            rx.scroll_area(
                rx.vstack(
                    rx.foreach(
                        AppState.chat_messages,
                        _message_bubble,
                    ),
                    padding_y="16px",
                    width="100%",
                    spacing="0",
                    min_height="100%",
                    justify="end",
                ),
                type="scroll",
                flex="1",
                width="100%",
                height="calc(100vh - 130px)",
                scrollbars="vertical",
            ),
        ),

        # ── Input de mensaje ──────────────────────────────────
        rx.box(
            rx.vstack(
                # Chip del archivo adjunto (visible solo cuando hay adjunto)
                rx.cond(
                    AppState.attached_file_name != "",
                    rx.hstack(
                        rx.icon("file-text", size=13, color="#aaaaaa"),
                        rx.text(
                            AppState.attached_file_name,
                            font_size="12px",
                            color="#aaaaaa",
                            font_family="DM Mono, monospace",
                            max_width="300px",
                            no_of_lines=1,
                        ),
                        rx.icon_button(
                            rx.icon("x", size=11),
                            on_click=AppState.clear_attachment,
                            background="transparent",
                            color="#666666",
                            size="1",
                            cursor="pointer",
                            _hover={"color": "#e5e5e5"},
                            padding="0",
                            height="18px",
                            width="18px",
                            border_radius="4px",
                        ),
                        background="#1a1a1a",
                        border="1px solid #2a2a2a",
                        border_radius="6px",
                        padding="4px 8px",
                        align="center",
                        spacing="1",
                    ),
                    rx.box(),
                ),
                # Fila de input
                rx.hstack(
                    # Botón de adjuntar archivo
                    rx.upload(
                        rx.icon_button(
                            rx.icon("paperclip", size=15),
                            background="transparent",
                            color="#555555",
                            border="1px solid #1e1e1e",
                            border_radius="10px",
                            size="3",
                            cursor="pointer",
                            _hover={"color": "#aaaaaa", "border_color": "#333333"},
                            flex_shrink="0",
                        ),
                        id="file_upload",
                        on_drop=AppState.handle_upload(rx.upload_files(upload_id="file_upload")),
                        accept={
                            "application/pdf": [".pdf"],
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
                            "text/plain": [".txt"],
                        },
                        max_files=1,
                        border="none",
                        padding="0",
                    ),
                    rx.text_area(
                        placeholder="Escribe tu mensaje... (Enter para enviar, Shift+Enter para salto de línea)",
                        value=AppState.chat_input,
                        on_change=AppState.set_chat_input,
                        on_key_down=AppState.handle_key_down,
                        resize="none",
                        rows="1",
                        max_rows="6",
                        background="#111111",
                        border="1px solid #1e1e1e",
                        color="#e5e5e5",
                        _placeholder={"color": "#444444", "font_size": "13px"},
                        _focus={
                            "border_color": "#E2001A",
                            "outline": "none",
                            "box_shadow": "none",
                        },
                        border_radius="10px",
                        font_family="Barlow, sans-serif",
                        font_size="14px",
                        padding="10px 14px",
                        flex="1",
                        min_height="42px",
                    ),
                    rx.icon_button(
                        rx.cond(
                            AppState.is_streaming,
                            rx.spinner(size="2"),
                            rx.icon("arrow-up", size=16),
                        ),
                        on_click=AppState.send_message,
                        disabled=AppState.is_streaming,
                        background=rx.cond(
                            AppState.is_streaming,
                            "#1e1e1e",
                            "#E2001A",
                        ),
                        color="white",
                        border_radius="10px",
                        size="3",
                        cursor="pointer",
                        _hover=rx.cond(
                            AppState.is_streaming,
                            {},
                            {"background": "#c00015"},
                        ),
                        flex_shrink="0",
                    ),
                    spacing="2",
                    align="end",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            padding="12px 20px 16px",
            border_top="1px solid #1a1a1a",
            background="#0a0a0a",
            flex_shrink="0",
            display=rx.cond(
                AppState.current_conversation_id != "",
                "block",
                "none",
            ),
        ),

        spacing="0",
        height="100%",
        flex="1",
        overflow="hidden",
        background="#0a0a0a",
    )
