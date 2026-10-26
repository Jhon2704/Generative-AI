"""
Página principal de CONSTELLATION.
Layout: Rail izquierdo (logo + nav) + Sidebar (conversaciones) + Chat + Grafo + Panel nodo.
Responsive: desktop con 4 zonas, móvil con bottom tabs.
"""
from __future__ import annotations

import reflex as rx

from ..state.app_state import AppState
from ..state.auth_state import AuthState
from ..state.graph_state import GraphState
from ..components.sidebar import sidebar
from ..components.chat import chat_panel
from ..components.graph import graph_canvas
from ..components.node_panel import node_panel
from ..components.intro import intro_screen


# ══════════════════════════════════════════════════════════════
# RAIL IZQUIERDO — Logo + Navegación vertical
# ══════════════════════════════════════════════════════════════

def _left_rail() -> rx.Component:
    """
    Rail izquierdo fijo con logo CG, iconos de navegación y perfil.
    Ancho: 56px. Siempre visible en desktop.
    """
    return rx.vstack(
        # ── Logo CG ─────────────────────────────────────────
        rx.box(
            rx.text(
                "CG",
                font_size="14px",
                font_weight="900",
                color="#E2001A",
                font_family="Barlow Condensed, sans-serif",
                line_height="1",
                letter_spacing="0.05em",
            ),
            width="40px",
            height="40px",
            background="#111111",
            border="1px solid #E2001A",
            border_radius="8px",
            display="flex",
            align_items="center",
            justify_content="center",
            margin_x="auto",
            flex_shrink="0",
        ),

        rx.divider(border_color="#1e1e1e", margin_y="4px"),

        # ── Iconos de navegación ────────────────────────────
        rx.tooltip(
            rx.icon_button(
                rx.icon("message-square", size=18),
                size="2",
                variant="ghost",
                color_scheme="gray",
                on_click=lambda: AppState.set_active_view("chat"),
                color=rx.cond(
                    AppState.active_view == "chat",
                    "#E2001A",
                    "#555555",
                ),
                _hover={"color": "#E2001A"},
                background=rx.cond(
                    AppState.active_view == "chat",
                    "#1a0000",
                    "transparent",
                ),
                border_radius="8px",
                width="40px",
                height="40px",
            ),
            content="Chat",
            side="right",
        ),
        rx.tooltip(
            rx.icon_button(
                rx.icon("network", size=18),
                size="2",
                variant="ghost",
                color_scheme="gray",
                on_click=[AppState.set_active_view("graph"), GraphState.reload_graph, rx.call_script("setTimeout(function(){if(window._constellationResize)window._constellationResize();},300);")],
                color=rx.cond(
                    AppState.active_view == "graph",
                    "#E2001A",
                    "#555555",
                ),
                _hover={"color": "#E2001A"},
                background=rx.cond(
                    AppState.active_view == "graph",
                    "#1a0000",
                    "transparent",
                ),
                border_radius="8px",
                width="40px",
                height="40px",
            ),
            content="Knowledge Graph",
            side="right",
        ),
        rx.tooltip(
            rx.icon_button(
                rx.icon("folder", size=18),
                size="2",
                variant="ghost",
                color_scheme="gray",
                on_click=GraphState.toggle_project_admin,
                color=rx.cond(
                    GraphState.show_project_admin,
                    "#E2001A",
                    "#555555",
                ),
                _hover={"color": "#E2001A"},
                background=rx.cond(
                    GraphState.show_project_admin,
                    "#1a0000",
                    "transparent",
                ),
                border_radius="8px",
                width="40px",
                height="40px",
            ),
            content="Proyectos",
            side="right",
        ),
        rx.tooltip(
            rx.icon_button(
                rx.icon("users", size=18),
                size="2",
                variant="ghost",
                color_scheme="gray",
                on_click=AuthState.toggle_workspace_panel,
                color=rx.cond(AuthState.show_workspace_panel, "#E2001A", "#555555"),
                _hover={"color": "#E2001A"},
                background=rx.cond(AuthState.show_workspace_panel, "#1a0000", "transparent"),
                border_radius="8px",
                width="40px",
                height="40px",
            ),
            content="Workspace",
            side="right",
        ),

        rx.spacer(),

        # ── Perfil de usuario ────────────────────────────────
        rx.tooltip(
            rx.box(
                rx.text(
                    AuthState.user_initials,
                    font_size="12px",
                    font_weight="700",
                    color="#e5e5e5",
                    font_family="Barlow Condensed, sans-serif",
                ),
                width="32px",
                height="32px",
                background="#E2001A",
                border_radius="50%",
                display="flex",
                align_items="center",
                justify_content="center",
                cursor="pointer",
                _hover={"background": "#c00015"},
            ),
            content=AuthState.display_name,
            side="right",
        ),
        rx.tooltip(
            rx.icon_button(
                rx.icon("log-out", size=16),
                size="2",
                variant="ghost",
                color_scheme="gray",
                on_click=AuthState.logout,
                color="#555555",
                _hover={"color": "#E2001A"},
                border_radius="8px",
                width="40px",
                height="40px",
            ),
            content="Cerrar sesión",
            side="right",
        ),

        align="center",
        spacing="2",
        padding_y="12px",
        padding_x="8px",
        width="56px",
        min_width="56px",
        height="100vh",
        background="#0d0d0d",
        border_right="1px solid #1e1e1e",
        flex_shrink="0",
    )


# ══════════════════════════════════════════════════════════════
# PANEL ADMIN DE PROYECTOS
# ══════════════════════════════════════════════════════════════

def _project_admin_panel() -> rx.Component:
    """Modal/panel de administración de proyectos."""
    return rx.cond(
        GraphState.show_project_admin,
        rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.text(
                        "Proyectos",
                        font_size="16px",
                        font_weight="700",
                        color="#e5e5e5",
                        font_family="Barlow Condensed, sans-serif",
                        letter_spacing="0.05em",
                    ),
                    rx.spacer(),
                    rx.icon_button(
                        rx.icon("x", size=14),
                        size="1",
                        variant="ghost",
                        color_scheme="gray",
                        on_click=GraphState.toggle_project_admin,
                        _hover={"color": "#E2001A"},
                    ),
                    width="100%",
                    align="center",
                ),

                rx.divider(border_color="#1e1e1e"),

                # Lista de proyectos existentes
                rx.scroll_area(
                    rx.vstack(
                        rx.foreach(
                            GraphState.projects,
                            lambda proj: rx.hstack(
                                rx.box(
                                    width="10px",
                                    height="10px",
                                    border_radius="50%",
                                    background=proj.color,
                                    flex_shrink="0",
                                ),
                                rx.text(
                                    proj.emoji + " " + proj.name,
                                    font_size="13px",
                                    color="#e5e5e5",
                                    font_family="Barlow, sans-serif",
                                    flex="1",
                                ),
                                rx.icon_button(
                                    rx.icon("trash-2", size=12),
                                    size="1",
                                    variant="ghost",
                                    color_scheme="gray",
                                    on_click=GraphState.delete_project(proj.id),
                                    _hover={"color": "#E2001A"},
                                ),
                                spacing="2",
                                align="center",
                                width="100%",
                                padding="6px 0",
                            ),
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    type="scroll",
                    max_height="200px",
                    width="100%",
                ),

                rx.divider(border_color="#1e1e1e"),

                # Formulario nuevo proyecto
                rx.text(
                    "Nuevo proyecto",
                    font_size="11px", font_weight="600", color="#555555",
                    text_transform="uppercase", letter_spacing="0.1em",
                    font_family="Barlow Condensed, sans-serif",
                ),

                # Nombre
                rx.input(
                    placeholder="Nombre del proyecto",
                    value=GraphState.new_project_name,
                    on_change=GraphState.set_new_project_name,
                    width="100%",
                    background="rgba(255,255,255,0.04)",
                    border="1px solid #1e1e1e",
                    color="#e5e5e5",
                    border_radius="8px",
                    font_size="13px",
                    height="36px",
                    _focus={"border_color": "#E2001A", "outline": "none"},
                    font_family="Barlow, sans-serif",
                ),

                # Selector de iconos
                rx.vstack(
                    rx.text("Icono", font_size="10px", color="#444444",
                            font_family="Barlow Condensed, sans-serif", letter_spacing="0.08em"),
                    rx.hstack(
                        *[rx.button(
                            e,
                            on_click=GraphState.set_new_project_emoji(e),
                            font_size="16px",
                            width="34px", height="34px", padding="0",
                            border_radius="6px",
                            background=rx.cond(GraphState.new_project_emoji == e, "rgba(226,0,26,0.2)", "rgba(255,255,255,0.04)"),
                            border=rx.cond(GraphState.new_project_emoji == e, "1px solid #E2001A", "1px solid #1e1e1e"),
                            cursor="pointer",
                            _hover={"border_color": "#E2001A", "background": "rgba(226,0,26,0.1)"},
                        ) for e in ["💡", "🚀", "🔬", "💻", "📊", "☁️"]],
                        spacing="1", wrap="wrap",
                    ),
                    rx.hstack(
                        *[rx.button(
                            e,
                            on_click=GraphState.set_new_project_emoji(e),
                            font_size="16px",
                            width="34px", height="34px", padding="0",
                            border_radius="6px",
                            background=rx.cond(GraphState.new_project_emoji == e, "rgba(226,0,26,0.2)", "rgba(255,255,255,0.04)"),
                            border=rx.cond(GraphState.new_project_emoji == e, "1px solid #E2001A", "1px solid #1e1e1e"),
                            cursor="pointer",
                            _hover={"border_color": "#E2001A", "background": "rgba(226,0,26,0.1)"},
                        ) for e in ["🎯", "🔧", "📚", "🏗️", "🎨", "🔐"]],
                        spacing="1", wrap="wrap",
                    ),
                    rx.hstack(
                        *[rx.button(
                            e,
                            on_click=GraphState.set_new_project_emoji(e),
                            font_size="16px",
                            width="34px", height="34px", padding="0",
                            border_radius="6px",
                            background=rx.cond(GraphState.new_project_emoji == e, "rgba(226,0,26,0.2)", "rgba(255,255,255,0.04)"),
                            border=rx.cond(GraphState.new_project_emoji == e, "1px solid #E2001A", "1px solid #1e1e1e"),
                            cursor="pointer",
                            _hover={"border_color": "#E2001A", "background": "rgba(226,0,26,0.1)"},
                        ) for e in ["🤖", "🌐", "📱", "⚙️", "🏥", "📋"]],
                        spacing="1", wrap="wrap",
                    ),
                    spacing="2", width="100%", align_items="flex-start",
                ),

                # Selector de forma del nodo
                rx.vstack(
                    rx.text("Forma del nodo", font_size="10px", color="#444444",
                            font_family="Barlow Condensed, sans-serif", letter_spacing="0.08em"),
                    rx.hstack(
                        *[rx.button(
                            label,
                            on_click=GraphState.set_new_project_shape(shape),
                            font_size="15px",
                            width="44px", height="34px", padding="0",
                            border_radius="6px",
                            background=rx.cond(GraphState.new_project_shape == shape, "rgba(226,0,26,0.2)", "rgba(255,255,255,0.04)"),
                            border=rx.cond(GraphState.new_project_shape == shape, "1px solid #E2001A", "1px solid #1e1e1e"),
                            color=rx.cond(GraphState.new_project_shape == shape, "#E2001A", "#888888"),
                            cursor="pointer",
                            title=title,
                            _hover={"border_color": "#E2001A", "color": "#E2001A"},
                        ) for shape, label, title in [
                            ("circle",   "●", "Círculo"),
                            ("square",   "■", "Cuadrado"),
                            ("diamond",  "◆", "Diamante"),
                            ("hexagon",  "⬡", "Hexágono"),
                            ("star",     "★", "Estrella"),
                            ("triangle", "▲", "Triángulo"),
                        ]],
                        spacing="1",
                    ),
                    spacing="2", width="100%", align_items="flex-start",
                ),

                # Color
                rx.hstack(
                    rx.text("Color", font_size="10px", color="#444444",
                            font_family="Barlow Condensed, sans-serif", letter_spacing="0.08em"),
                    rx.input(
                        type="color",
                        value=GraphState.new_project_color,
                        on_change=GraphState.set_new_project_color,
                        width="48px", height="30px",
                        background="transparent",
                        border="1px solid #1e1e1e",
                        border_radius="6px",
                        padding="2px",
                        cursor="pointer",
                    ),
                    spacing="3", align="center",
                ),

                rx.button(
                    rx.icon("plus", size=13),
                    "Crear proyecto",
                    on_click=GraphState.create_project,
                    background="#E2001A",
                    color="white",
                    _hover={"background": "#c00015"},
                    border_radius="6px",
                    font_size="12px",
                    font_family="Barlow Condensed, sans-serif",
                    font_weight="600",
                    height="36px",
                    padding_x="14px",
                    gap="6px",
                    cursor="pointer",
                    width="100%",
                ),

                spacing="3",
                width="100%",
            ),
            padding="20px",
            background="#0d0d0d",
            border="1px solid #1e1e1e",
            border_radius="12px",
            width="360px",
            max_height="85vh",
            overflow_y="auto",
            position="absolute",
            top="60px",
            left="64px",
            z_index="100",
            box_shadow="0 8px 40px rgba(0,0,0,0.7)",
        ),
        rx.box(),
    )


# ══════════════════════════════════════════════════════════════
# PANEL WORKSPACE
# ══════════════════════════════════════════════════════════════

def _workspace_panel() -> rx.Component:
    """Panel de gestión del workspace actual."""
    return rx.cond(
        AuthState.show_workspace_panel,
        rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.vstack(
                        rx.text(
                            "Workspace",
                            font_size="16px", font_weight="700", color="#e5e5e5",
                            font_family="Barlow Condensed, sans-serif", letter_spacing="0.05em",
                        ),
                        rx.text(
                            AuthState.workspace_name,
                            font_size="12px", color="#666666",
                            font_family="Barlow, sans-serif",
                        ),
                        spacing="0",
                    ),
                    rx.spacer(),
                    rx.icon_button(
                        rx.icon("x", size=14), size="1", variant="ghost",
                        color_scheme="gray", on_click=AuthState.toggle_workspace_panel,
                        _hover={"color": "#E2001A"},
                    ),
                    width="100%", align="start",
                ),

                rx.divider(border_color="#1e1e1e"),

                # Código de invitación (solo si workspace activo)
                rx.cond(
                    AuthState.workspace_id != "",
                    rx.vstack(
                        rx.text("Código de invitación", font_size="10px", color="#555555",
                                text_transform="uppercase", letter_spacing="0.1em",
                                font_family="Barlow Condensed, sans-serif", font_weight="600"),
                        rx.hstack(
                            rx.box(
                                rx.text(
                                    AuthState.workspace_invite_code,
                                    font_size="20px", font_weight="700", color="#E2001A",
                                    font_family="DM Mono, monospace", letter_spacing="0.15em",
                                ),
                                background="#0a0a0a",
                                border="1px solid #1e1e1e",
                                border_radius="8px",
                                padding="8px 16px",
                                flex="1",
                                text_align="center",
                            ),
                            rx.tooltip(
                                rx.icon_button(
                                    rx.icon("copy", size=14), size="2", variant="ghost",
                                    color_scheme="gray",
                                    on_click=rx.set_clipboard(AuthState.workspace_invite_code),
                                    _hover={"color": "#E2001A"},
                                ),
                                content="Copiar",
                            ),
                            rx.cond(
                                AuthState.workspace_is_owner,
                                rx.tooltip(
                                    rx.icon_button(
                                        rx.icon("refresh-cw", size=14), size="2", variant="ghost",
                                        color_scheme="gray",
                                        on_click=AuthState.regenerate_invite_code,
                                        _hover={"color": "#E2001A"},
                                    ),
                                    content="Regenerar código",
                                ),
                                rx.box(),
                            ),
                            spacing="2", align="center", width="100%",
                        ),
                        rx.text(
                            "Comparte este código para invitar a otros al workspace",
                            font_size="11px", color="#444444",
                            font_family="Barlow, sans-serif", text_align="center",
                        ),
                        spacing="2", width="100%", align_items="flex-start",
                    ),
                    # Sin workspace: aviso de migración pendiente
                    rx.vstack(
                        rx.hstack(
                            rx.icon("alert-triangle", size=14, color="#f59e0b"),
                            rx.text(
                                "Migración pendiente",
                                font_size="12px", font_weight="600", color="#f59e0b",
                                font_family="Barlow Condensed, sans-serif",
                            ),
                            spacing="2", align="center",
                        ),
                        rx.text(
                            "Para activar workspaces ejecuta workspace_migration.sql en el SQL Editor de Supabase.",
                            font_size="12px", color="#666666",
                            font_family="Barlow, sans-serif", line_height="1.5",
                        ),
                        spacing="2", width="100%",
                    ),
                ),

                rx.divider(border_color="#1e1e1e"),

                # Miembros del workspace
                rx.cond(
                    AuthState.workspace_id != "",
                    rx.vstack(
                        rx.hstack(
                            rx.text("Miembros", font_size="10px", color="#555555",
                                    text_transform="uppercase", letter_spacing="0.1em",
                                    font_family="Barlow Condensed, sans-serif", font_weight="600"),
                            rx.spacer(),
                            rx.icon_button(
                                rx.icon("refresh-cw", size=12),
                                size="1", variant="ghost", color_scheme="gray",
                                on_click=AuthState.refresh_workspace_members,
                                _hover={"color": "#E2001A"},
                            ),
                            width="100%", align="center",
                        ),
                        rx.scroll_area(
                            rx.vstack(
                                rx.foreach(
                                    AuthState.workspace_members,
                                    lambda m: rx.hstack(
                                        rx.vstack(
                                            rx.text(
                                                m["user_name"],
                                                font_size="12px", color="#e5e5e5",
                                                font_family="Barlow, sans-serif",
                                                no_of_lines=1,
                                            ),
                                            rx.text(
                                                m["user_email"],
                                                font_size="10px", color="#555555",
                                                font_family="Barlow, sans-serif",
                                                no_of_lines=1,
                                            ),
                                            spacing="0", align_items="flex-start", flex="1",
                                        ),
                                        rx.badge(
                                            m["role"],
                                            size="1", variant="soft",
                                            color_scheme=rx.cond(m["role"] == "owner", "red", "gray"),
                                        ),
                                        rx.cond(
                                            AuthState.workspace_is_owner & (m["user_id"] != AuthState.user_id),
                                            rx.button(
                                                rx.icon("user-minus", size=12),
                                                "Quitar",
                                                size="1",
                                                variant="soft",
                                                color_scheme="red",
                                                on_click=AuthState.remove_member_from_workspace(m["user_id"]),
                                                title="Quitar acceso",
                                                border_radius="6px",
                                                font_size="11px",
                                                font_family="Barlow Condensed, sans-serif",
                                                font_weight="600",
                                                cursor="pointer",
                                                flex_shrink="0",
                                            ),
                                            rx.box(),
                                        ),
                                        spacing="2", align="center", width="100%", padding="6px 0",
                                    ),
                                ),
                                spacing="1", width="100%",
                            ),
                            max_height="130px", type="scroll", width="100%",
                        ),
                        rx.cond(
                            AuthState.workspace_is_owner,
                            rx.text("El owner puede quitar miembros del workspace.",
                                    font_size="11px", color="#444444", font_family="Barlow, sans-serif"),
                            rx.text("Puedes salir desde la lista de tus workspaces.",
                                    font_size="11px", color="#444444", font_family="Barlow, sans-serif"),
                        ),
                        spacing="2", width="100%", align_items="flex-start",
                    ),
                    rx.box(),
                ),

                rx.divider(border_color="#1e1e1e"),

                # Unirse a otro workspace (solo si migración activa)
                rx.cond(
                    AuthState.workspace_id != "",
                    rx.vstack(
                    rx.text("Unirse a workspace", font_size="10px", color="#555555",
                            text_transform="uppercase", letter_spacing="0.1em",
                            font_family="Barlow Condensed, sans-serif", font_weight="600"),
                    rx.hstack(
                        rx.input(
                            placeholder="Código XXXXXXXX",
                            value=AuthState.workspace_join_code,
                            on_change=AuthState.set_workspace_join_code,
                            background="rgba(255,255,255,0.04)",
                            border="1px solid #1e1e1e",
                            color="#e5e5e5",
                            border_radius="8px",
                            font_size="13px",
                            font_family="DM Mono, monospace",
                            height="36px",
                            flex="1",
                            _focus={"border_color": "#E2001A", "outline": "none"},
                            _placeholder={"color": "#333333"},
                            text_transform="uppercase",
                        ),
                        rx.button(
                            "Unirse",
                            on_click=AuthState.join_workspace,
                            background="#E2001A", color="white",
                            _hover={"background": "#c00015"},
                            border_radius="8px", font_size="12px",
                            font_family="Barlow Condensed, sans-serif", font_weight="600",
                            height="36px", padding_x="12px", cursor="pointer",
                        ),
                        spacing="2", width="100%",
                    ),
                    rx.cond(
                        AuthState.workspace_join_error != "",
                        rx.text(AuthState.workspace_join_error, font_size="11px",
                                color="#E2001A", font_family="Barlow, sans-serif"),
                        rx.box(),
                    ),
                    rx.cond(
                        AuthState.workspace_join_success != "",
                        rx.text(AuthState.workspace_join_success, font_size="11px",
                                color="#4caf50", font_family="Barlow, sans-serif"),
                        rx.box(),
                    ),
                    spacing="2", width="100%", align_items="flex-start",
                    ),
                    rx.box(),
                ),

                rx.divider(border_color="#1e1e1e"),

                # Mis workspaces
                rx.vstack(
                    rx.text("Mis workspaces", font_size="10px", color="#555555",
                            text_transform="uppercase", letter_spacing="0.1em",
                            font_family="Barlow Condensed, sans-serif", font_weight="600"),
                    rx.scroll_area(
                        rx.vstack(
                            rx.foreach(
                                AuthState.available_workspaces,
                                lambda w: rx.hstack(
                                    rx.box(
                                        width="8px", height="8px", border_radius="50%",
                                        background=rx.cond(
                                            AuthState.workspace_id == w["id"],
                                            "#E2001A", "#333333",
                                        ),
                                        flex_shrink="0",
                                    ),
                                    rx.text(
                                        w["name"],
                                        font_size="13px", color=rx.cond(
                                            AuthState.workspace_id == w["id"],
                                            "#e5e5e5", "#888888",
                                        ),
                                        font_family="Barlow, sans-serif", flex="1",
                                        cursor="pointer",
                                        on_click=AuthState.switch_workspace(w["id"]),
                                        _hover={"color": "#e5e5e5"},
                                    ),
                                    rx.badge(
                                        w["role"],
                                        size="1", variant="soft",
                                        color_scheme=rx.cond(w["role"] == "owner", "red", "gray"),
                                    ),
                                    rx.cond(
                                        w["role"] != "owner",
                                        rx.box(
                                            rx.icon_button(
                                                rx.icon("log-out", size=12),
                                                size="1", variant="ghost",
                                                color_scheme="gray",
                                                on_click=AuthState.leave_workspace(w["id"]),
                                                title="Dejar de ver este workspace",
                                                _hover={"color": "#E2001A"},
                                            ),
                                            on_click=rx.stop_propagation,
                                        ),
                                        rx.box(),
                                    ),
                                    spacing="2", align="center", width="100%", padding="4px 0",
                                ),
                            ),
                            spacing="1", width="100%",
                        ),
                        max_height="150px", type="scroll", width="100%",
                    ),
                    spacing="2", width="100%", align_items="flex-start",
                ),

                spacing="3", width="100%",
            ),
            padding="20px",
            background="#0d0d0d",
            border="1px solid #1e1e1e",
            border_radius="12px",
            width="360px",
            max_height="85vh",
            overflow_y="auto",
            position="absolute",
            top="60px",
            left="64px",
            z_index="100",
            box_shadow="0 8px 40px rgba(0,0,0,0.7)",
        ),
        rx.box(),
    )


# ══════════════════════════════════════════════════════════════
# BOTTOM TABS — Solo en móvil
# ══════════════════════════════════════════════════════════════

def _bottom_tabs() -> rx.Component:
    """Navegación inferior para dispositivos móviles."""
    def tab_item(icon_name: str, label: str, view: str) -> rx.Component:
        is_active = AppState.active_view == view
        return rx.button(
            rx.vstack(
                rx.icon(
                    icon_name,
                    size=20,
                    color=rx.cond(is_active, "#E2001A", "#666666"),
                ),
                rx.text(
                    label,
                    font_size="10px",
                    color=rx.cond(is_active, "#E2001A", "#666666"),
                    font_family="Barlow, sans-serif",
                ),
                spacing="1",
                align="center",
            ),
            on_click=lambda: AppState.set_active_view(view),
            background="transparent",
            border="none",
            cursor="pointer",
            flex="1",
            height="56px",
            padding="0",
        )

    return rx.hstack(
        tab_item("message-square", "Chat", "chat"),
        tab_item("network", "Grafo", "graph"),
        tab_item("folder", "Proyectos", "projects"),
        width="100%",
        border_top="1px solid #1e1e1e",
        background="#0d0d0d",
        spacing="0",
        display=["flex", "flex", "none"],  # Solo en xs y sm
    )


# ══════════════════════════════════════════════════════════════
# LAYOUT DESKTOP
# ══════════════════════════════════════════════════════════════

def _desktop_layout() -> rx.Component:
    """Layout completo de escritorio: 4 columnas."""
    return rx.hstack(
        # Rail izquierdo: 56px
        _left_rail(),

        # Sidebar conversaciones: 240px
        sidebar(),

        # Chat o intro: flex-1
        rx.box(
            rx.cond(
                AppState.show_intro,
                intro_screen(),
                chat_panel(),
            ),
            flex="1",
            height="100vh",
            overflow="hidden",
            display=rx.cond(
                AppState.active_view == "chat",
                "flex",
                "none",
            ),
        ),

        # Grafo: fijo o flex
        rx.box(
            graph_canvas(),
            width=rx.cond(
                AppState.active_view == "graph",
                "100%",
                "420px",
            ),
            min_width=rx.cond(
                AppState.active_view == "graph",
                "100%",
                "420px",
            ),
            height="100vh",
            border_left="1px solid #1e1e1e",
            flex_shrink="0",
        ),

        # Panel lateral del nodo
        node_panel(),

        spacing="0",
        height="100vh",
        width="100vw",
        overflow="hidden",
        background="#0a0a0a",
        position="relative",
    )


# ══════════════════════════════════════════════════════════════
# PÁGINA INDEX
# ══════════════════════════════════════════════════════════════

def index() -> rx.Component:
    """
    Página principal protegida.
    on_load verifica la sesión y carga los datos iniciales.
    """
    return rx.box(
        # ── Contenido principal ───────────────────────────────
        _desktop_layout(),

        # ── Overlay admin proyectos ───────────────────────────
        _project_admin_panel(),

        # ── Panel workspace ───────────────────────────────────
        _workspace_panel(),

        # ── Bottom tabs móvil ─────────────────────────────────
        _bottom_tabs(),

        # ── CSS global ────────────────────────────────────────
        rx.html("""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;900&family=Barlow:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body {
            background-color: #03040a;
            background-image:
              radial-gradient(ellipse at 30% 20%, rgba(28,12,80,0.28) 0%, transparent 52%),
              radial-gradient(ellipse at 72% 78%, rgba(80,8,18,0.18) 0%, transparent 52%);
            overflow: hidden;
          }
          @keyframes starDrift {
            from { transform: translateY(0px); }
            to   { transform: translateY(-2000px); }
          }
          .star-layer { position:fixed; top:0; left:0; border-radius:50%;
                        pointer-events:none; z-index:0; background:transparent; }
          ::-webkit-scrollbar { width: 4px; height: 4px; }
          ::-webkit-scrollbar-track { background: transparent; }
          ::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 4px; }
          ::-webkit-scrollbar-thumb:hover { background: #E2001A; }

          @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
          }
          @keyframes pulse {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 0.8; }
          }
          @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to   { transform: translateX(0);   opacity: 1; }
          }

          /* Markdown en mensajes del chat */
          .chat-message p { margin-bottom: 8px; }
          .chat-message p:last-child { margin-bottom: 0; }
          .chat-message ul, .chat-message ol { margin-left: 20px; margin-bottom: 8px; }
          .chat-message h1, .chat-message h2, .chat-message h3 {
            font-family: 'Barlow Condensed', sans-serif;
            margin-bottom: 6px;
            color: #e5e5e5;
          }

          /* Responsive móvil */
          @media (max-width: 768px) {
            body { overflow: auto; }
          }
        </style>
        <script>
        (function(){
          if (document.getElementById('star-layer-1')) return;
          function rnd(n) { return Math.random() * n | 0; }
          function makeBoxShadow(count) {
            var s = [];
            for (var i = 0; i < count; i++) {
              s.push((rnd(3000)-500)+'px '+(rnd(3000)-500)+'px #fff');
            }
            return s.join(',');
          }
          var style = document.createElement('style');
          style.textContent =
            '#star-layer-1{width:1px;height:1px;box-shadow:'+makeBoxShadow(700)+
              ';animation:starDrift 150s linear infinite;opacity:0.55;}' +
            '#star-layer-2{width:2px;height:2px;box-shadow:'+makeBoxShadow(220)+
              ';animation:starDrift 220s linear infinite;opacity:0.45;}' +
            '#star-layer-3{width:3px;height:3px;box-shadow:'+makeBoxShadow(90)+
              ';animation:starDrift 300s linear infinite;opacity:0.35;}';
          document.head.appendChild(style);
          ['star-layer-1','star-layer-2','star-layer-3'].forEach(function(id){
            var el = document.createElement('div');
            el.id = id; el.className = 'star-layer';
            document.body.appendChild(el);
          });
        })();
        </script>
        """),


        min_height="100vh",
        background="transparent",
    )
