"""
Página de autenticación de CONSTELLATION.
Layout producto: columna izquierda (branding) + columna derecha (formulario).
"""
from __future__ import annotations

import reflex as rx

from ..state.auth_state import AuthState


def _input_field(
    label: str,
    placeholder: str,
    value: str,
    on_change,
    input_type: str = "text",
) -> rx.Component:
    return rx.vstack(
        rx.text(
            label,
            font_size="11px",
            font_weight="600",
            color="#555555",
            text_transform="uppercase",
            letter_spacing="0.1em",
            font_family="Barlow Condensed, sans-serif",
        ),
        rx.input(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            type=input_type,
            background="rgba(255,255,255,0.04)",
            border="1px solid rgba(255,255,255,0.08)",
            color="#e5e5e5",
            _placeholder={"color": "#3a3a3a"},
            _focus={
                "border_color": "#E2001A",
                "outline": "none",
                "box_shadow": "0 0 0 3px rgba(226,0,26,0.12)",
                "background": "rgba(255,255,255,0.06)",
            },
            border_radius="10px",
            font_family="Barlow, sans-serif",
            font_size="14px",
            height="46px",
            width="100%",
            padding_x="16px",
        ),
        spacing="1",
        width="100%",
        align_items="flex-start",
    )


def _login_form() -> rx.Component:
    return rx.vstack(
        _input_field("Email", "tu@email.com", AuthState.login_email, AuthState.set_login_email),
        _input_field("Contraseña", "••••••••", AuthState.login_password, AuthState.set_login_password, input_type="password"),

        rx.cond(
            AuthState.auth_error != "",
            rx.hstack(
                rx.icon("circle-alert", size=14, color="#E2001A"),
                rx.text(AuthState.auth_error, font_size="12px", color="#E2001A", font_family="Barlow, sans-serif"),
                spacing="2", align="center",
                padding="10px 14px",
                background="rgba(226,0,26,0.08)",
                border="1px solid rgba(226,0,26,0.2)",
                border_radius="8px",
                width="100%",
            ),
            rx.box(),
        ),

        rx.button(
            rx.cond(
                AuthState.auth_loading,
                rx.hstack(rx.spinner(size="2"), rx.text("Iniciando sesión...", font_size="14px"), spacing="2", align="center"),
                rx.text("Iniciar sesión", font_size="14px"),
            ),
            on_click=AuthState.login,
            disabled=AuthState.auth_loading,
            background="linear-gradient(135deg, #E2001A 0%, #a80012 100%)",
            color="white",
            _hover={"background": "linear-gradient(135deg, #ff1a33 0%, #cc0016 100%)", "transform": "translateY(-1px)", "box_shadow": "0 4px 20px rgba(226,0,26,0.35)"},
            _disabled={"opacity": "0.5", "cursor": "not-allowed"},
            _active={"transform": "translateY(0)"},
            border_radius="10px",
            height="46px",
            width="100%",
            font_family="Barlow Condensed, sans-serif",
            font_weight="700",
            letter_spacing="0.08em",
            font_size="15px",
            cursor="pointer",
            transition="all 0.15s ease",
        ),

        rx.hstack(
            rx.text("¿No tienes cuenta?", font_size="13px", color="#555555", font_family="Barlow, sans-serif"),
            rx.button(
                "Crear cuenta",
                on_click=AuthState.toggle_auth_mode,
                background="transparent", color="#E2001A", border="none",
                font_size="13px", font_family="Barlow, sans-serif",
                cursor="pointer", _hover={"color": "#ff1a33"}, padding="0",
            ),
            spacing="1", justify="center", width="100%",
        ),

        spacing="4", width="100%",
    )


def _register_form() -> rx.Component:
    return rx.vstack(
        _input_field("Nombre completo", "Ana García", AuthState.register_name, AuthState.set_register_name),
        _input_field("Email", "tu@email.com", AuthState.register_email, AuthState.set_register_email),
        _input_field("Contraseña", "Mínimo 8 caracteres", AuthState.register_password, AuthState.set_register_password, input_type="password"),
        _input_field("Confirmar contraseña", "Repite tu contraseña", AuthState.register_password_confirm, AuthState.set_register_password_confirm, input_type="password"),

        rx.cond(
            AuthState.auth_error != "",
            rx.hstack(
                rx.icon("circle-alert", size=14, color="#E2001A"),
                rx.text(AuthState.auth_error, font_size="12px", color="#E2001A", font_family="Barlow, sans-serif"),
                spacing="2", align="center",
                padding="10px 14px",
                background="rgba(226,0,26,0.08)",
                border="1px solid rgba(226,0,26,0.2)",
                border_radius="8px",
                width="100%",
            ),
            rx.box(),
        ),

        rx.button(
            rx.cond(
                AuthState.auth_loading,
                rx.hstack(rx.spinner(size="2"), rx.text("Creando cuenta...", font_size="14px"), spacing="2", align="center"),
                rx.text("Crear cuenta", font_size="14px"),
            ),
            on_click=AuthState.register,
            disabled=AuthState.auth_loading,
            background="linear-gradient(135deg, #E2001A 0%, #a80012 100%)",
            color="white",
            _hover={"background": "linear-gradient(135deg, #ff1a33 0%, #cc0016 100%)", "transform": "translateY(-1px)", "box_shadow": "0 4px 20px rgba(226,0,26,0.35)"},
            _disabled={"opacity": "0.5", "cursor": "not-allowed"},
            border_radius="10px",
            height="46px",
            width="100%",
            font_family="Barlow Condensed, sans-serif",
            font_weight="700",
            letter_spacing="0.08em",
            font_size="15px",
            cursor="pointer",
            transition="all 0.15s ease",
        ),

        rx.hstack(
            rx.text("¿Ya tienes cuenta?", font_size="13px", color="#555555", font_family="Barlow, sans-serif"),
            rx.button(
                "Iniciar sesión",
                on_click=AuthState.toggle_auth_mode,
                background="transparent", color="#E2001A", border="none",
                font_size="13px", font_family="Barlow, sans-serif",
                cursor="pointer", _hover={"color": "#ff1a33"}, padding="0",
            ),
            spacing="1", justify="center", width="100%",
        ),

        spacing="4", width="100%",
    )


def _feature_item(icon_name: str, title: str, desc: str) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon(icon_name, size=16, color="#E2001A"),
            width="36px", height="36px",
            background="rgba(226,0,26,0.1)",
            border="1px solid rgba(226,0,26,0.2)",
            border_radius="8px",
            display="flex", align_items="center", justify_content="center",
            flex_shrink="0",
        ),
        rx.vstack(
            rx.text(title, font_size="14px", font_weight="600", color="#e5e5e5", font_family="Barlow, sans-serif"),
            rx.text(desc, font_size="12px", color="#555555", font_family="Barlow, sans-serif", line_height="1.5"),
            spacing="0", align_items="flex-start",
        ),
        spacing="3", align="start", width="100%",
    )


def _left_panel() -> rx.Component:
    """Panel izquierdo de branding — solo visible en desktop."""
    return rx.box(
        rx.vstack(
            # Logo + nombre
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.text("CG", font_size="16px", font_weight="900", color="#E2001A",
                                font_family="Barlow Condensed, sans-serif", letter_spacing="0.05em"),
                        width="42px", height="42px",
                        background="rgba(226,0,26,0.1)",
                        border="1.5px solid rgba(226,0,26,0.4)",
                        border_radius="10px",
                        display="flex", align_items="center", justify_content="center",
                    ),
                    rx.vstack(
                        rx.text("CONSTELLATION", font_size="16px", font_weight="800", color="#e5e5e5",
                                font_family="Barlow Condensed, sans-serif", letter_spacing="0.2em"),
                        rx.text("GUIDE", font_size="10px", font_weight="600", color="#444444",
                                font_family="Barlow Condensed, sans-serif", letter_spacing="0.35em"),
                        spacing="0", align_items="flex-start",
                    ),
                    spacing="3", align="center",
                ),
                spacing="2",
            ),

            rx.box(height="32px"),

            # Tagline
            rx.vstack(
                rx.text(
                    "Tu conocimiento,",
                    font_size="38px", font_weight="800", color="#e5e5e5",
                    font_family="Barlow Condensed, sans-serif",
                    letter_spacing="0.02em", line_height="1.1",
                ),
                rx.text(
                    "conectado.",
                    font_size="38px", font_weight="800",
                    font_family="Barlow Condensed, sans-serif",
                    letter_spacing="0.02em", line_height="1.1",
                    background="linear-gradient(90deg, #E2001A, #ff4d63)",
                    background_clip="text",
                    _webkit_background_clip="text",
                    color="transparent",
                ),
                rx.text(
                    "Convierte tus conversaciones con IA en un grafo de conocimiento vivo.",
                    font_size="15px", color="#555555",
                    font_family="Barlow, sans-serif",
                    line_height="1.6",
                    margin_top="12px",
                    max_width="340px",
                ),
                spacing="0", align_items="flex-start",
            ),

            rx.box(height="40px"),

            # Features
            rx.vstack(
                _feature_item("network", "Knowledge Graph", "Cada chat se convierte en un nodo. Visualiza las conexiones entre ideas."),
                _feature_item("bot", "IA integrada", "Claude y modelos locales (Ollama) disponibles en cada conversación."),
                _feature_item("layers", "Proyectos", "Organiza el conocimiento por áreas. Filtra y navega con rapidez."),
                spacing="5", width="100%",
            ),

            rx.spacer(),

            # Footer
            rx.text(
                "Constellation Guide · Knowledge Graph",
                font_size="11px", color="#2a2a2a",
                font_family="DM Mono, monospace",
            ),

            spacing="0",
            align_items="flex-start",
            height="100%",
            padding="52px 48px",
            width="100%",
        ),

        # Línea separadora derecha con glow
        border_right="1px solid rgba(255,255,255,0.04)",
        box_shadow="inset -1px 0 40px rgba(226,0,26,0.03)",
        background="rgba(255,255,255,0.01)",
        height="100vh",
        width="50%",
        min_width="420px",
        display=["none", "none", "none", "flex"],  # oculto en mobile/tablet
        flex_direction="column",
        position="relative",
    )


def _right_panel() -> rx.Component:
    """Panel derecho con el formulario."""
    return rx.center(
        rx.vstack(
            # Logo (visible en mobile donde el panel izquierdo está oculto)
            rx.box(
                rx.hstack(
                    rx.box(
                        rx.text("CG", font_size="14px", font_weight="900", color="#E2001A",
                                font_family="Barlow Condensed, sans-serif", letter_spacing="0.05em"),
                        width="36px", height="36px",
                        background="rgba(226,0,26,0.1)",
                        border="1.5px solid rgba(226,0,26,0.35)",
                        border_radius="8px",
                        display="flex", align_items="center", justify_content="center",
                    ),
                    rx.text("CONSTELLATION", font_size="15px", font_weight="800", color="#e5e5e5",
                            font_family="Barlow Condensed, sans-serif", letter_spacing="0.18em"),
                    spacing="2", align="center",
                ),
                margin_bottom="32px",
                display=["flex", "flex", "flex", "none"],  # solo en mobile
            ),

            # Título del formulario
            rx.vstack(
                rx.cond(
                    AuthState.show_register,
                    rx.text("Crear cuenta", font_size="26px", font_weight="700", color="#e5e5e5",
                            font_family="Barlow Condensed, sans-serif", letter_spacing="0.04em"),
                    rx.text("Bienvenido de nuevo", font_size="26px", font_weight="700", color="#e5e5e5",
                            font_family="Barlow Condensed, sans-serif", letter_spacing="0.04em"),
                ),
                rx.cond(
                    AuthState.show_register,
                    rx.text("Empieza a construir tu knowledge graph.", font_size="13px", color="#555555",
                            font_family="Barlow, sans-serif"),
                    rx.text("Accede a tu knowledge graph.", font_size="13px", color="#555555",
                            font_family="Barlow, sans-serif"),
                ),
                spacing="1", align_items="flex-start", margin_bottom="28px",
            ),

            # Formulario
            rx.cond(AuthState.show_register, _register_form(), _login_form()),

            spacing="0",
            width="100%",
            max_width="380px",
            padding_x="16px",
        ),
        flex="1",
        height="100vh",
        background="transparent",
    )


def auth_page() -> rx.Component:
    return rx.box(
        rx.hstack(
            _left_panel(),
            _right_panel(),
            spacing="0",
            height="100vh",
            width="100vw",
            overflow="hidden",
        ),

        rx.html("""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
          * { box-sizing: border-box; margin: 0; }
          body {
            background-color: #03040a;
            background-image:
              radial-gradient(ellipse at 25% 25%, rgba(28,12,80,0.3) 0%, transparent 55%),
              radial-gradient(ellipse at 75% 75%, rgba(80,8,18,0.2) 0%, transparent 55%);
          }
          @keyframes starDrift {
            from { transform: translateY(0px); }
            to   { transform: translateY(-2000px); }
          }
          .star-layer { position:fixed; top:0; left:0; border-radius:50%;
                        pointer-events:none; z-index:0; background:transparent; }
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
    )


def auth() -> rx.Component:
    """Ruta /auth — página pública de autenticación."""
    return auth_page()
