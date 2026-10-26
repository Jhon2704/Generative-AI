"""
Estado de autenticación para CONSTELLATION.
Regla: métodos con `yield` = event handlers (solo llamados desde UI).
       métodos sin `yield` = helpers async (pueden ser await-ados).
"""
from __future__ import annotations

import reflex as rx
from ..services import supabase_service as sb


class AuthState(rx.State):

    user_id: str = ""
    user_name: str = ""
    user_email: str = ""
    user_initials: str = ""
    preferred_model: str = "claude-haiku-4-5-20251001"
    access_token: str = ""
    refresh_token: str = ""

    login_email: str = ""
    login_password: str = ""
    register_name: str = ""
    register_email: str = ""
    register_password: str = ""
    register_password_confirm: str = ""

    auth_error: str = ""
    auth_loading: bool = False
    show_register: bool = False

    # ── Workspace ─────────────────────────────────────────────
    workspace_id: str = ""
    workspace_name: str = ""
    workspace_invite_code: str = ""
    workspace_is_owner: bool = True
    available_workspaces: list[dict] = []
    workspace_members: list[dict] = []

    workspace_join_code: str = ""
    workspace_join_error: str = ""
    workspace_join_success: str = ""
    show_workspace_panel: bool = False

    @rx.var
    def is_authenticated(self) -> bool:
        return bool(self.user_id)

    @rx.var
    def display_name(self) -> str:
        return self.user_name or self.user_email.split("@")[0]

    # ── Event handlers (tienen yield → solo llamados desde UI) ──

    async def login(self):
        self.auth_loading = True
        self.auth_error = ""
        yield

        if not self.login_email or not self.login_password:
            self.auth_error = "Email y contraseña son obligatorios."
            self.auth_loading = False
            return

        result = await sb.sign_in(self.login_email, self.login_password)
        if result["error"]:
            self.auth_error = _translate_auth_error(result["error"])
            self.auth_loading = False
            return

        await self._save_session(result["user"], result["session"])
        self.login_email = ""
        self.login_password = ""
        self.auth_loading = False
        yield rx.redirect("/")

    async def register(self):
        self.auth_loading = True
        self.auth_error = ""
        yield

        if not self.register_name.strip():
            self.auth_error = "El nombre es obligatorio."
            self.auth_loading = False
            return
        if not self.register_email or not self.register_password:
            self.auth_error = "Email y contraseña son obligatorios."
            self.auth_loading = False
            return
        if len(self.register_password) < 8:
            self.auth_error = "La contraseña debe tener mínimo 8 caracteres."
            self.auth_loading = False
            return
        if self.register_password != self.register_password_confirm:
            self.auth_error = "Las contraseñas no coinciden."
            self.auth_loading = False
            return

        result = await sb.sign_up(self.register_email, self.register_password, self.register_name.strip())
        if result["error"]:
            self.auth_error = _translate_auth_error(result["error"])
            self.auth_loading = False
            return

        if result["session"]:
            await self._save_session(result["user"], result["session"])

        self.register_name = ""
        self.register_email = ""
        self.register_password = ""
        self.register_password_confirm = ""
        self.auth_loading = False
        yield rx.redirect("/")

    async def logout(self):
        await sb.sign_out()
        self.user_id = ""
        self.user_name = ""
        self.user_email = ""
        self.user_initials = ""
        self.access_token = ""
        self.refresh_token = ""
        yield rx.redirect("/auth")

    async def restore_session(self):
        """
        Event handler llamado en on_load de /index.
        Restaura sesión desde tokens guardados y redirige si no hay sesión.
        """
        if self.access_token and self.refresh_token:
            sb.set_session_token(self.access_token, self.refresh_token)
            current = sb.get_current_user()
            if current:
                profile = await sb.get_user_profile(current.id)
                if profile:
                    self._load_profile(current.id, current.email or "", profile)
                    if not self.workspace_id:
                        await self._init_workspace()
                    return

        if not self.is_authenticated:
            yield rx.redirect("/auth")

    # ── Helpers internos (sin yield → se pueden await) ───────────

    async def _save_session(self, user, session) -> None:
        if not user:
            return
        self.user_id = user.id
        self.user_email = user.email or ""
        self.access_token = session.access_token if session else ""
        self.refresh_token = session.refresh_token if session else ""

        profile = await sb.get_user_profile(user.id)
        if profile:
            self._load_profile(user.id, user.email or "", profile)
        else:
            name = (user.user_metadata or {}).get("name", "")
            self.user_name = name
            self.user_initials = _get_initials(name or user.email or "")

        await self._init_workspace()

    def _load_profile(self, user_id: str, email: str, profile: dict) -> None:
        self.user_id = user_id
        self.user_email = email or profile.get("email", "")
        self.user_name = profile.get("name", "")
        self.preferred_model = profile.get("preferred_model", "claude-haiku")
        self.user_initials = _get_initials(profile.get("name", "") or profile.get("email", ""))

    # ── Workspace helpers y event handlers ───────────────────────

    async def _init_workspace(self) -> None:
        """Crea o recupera el workspace personal y carga datos de workspace."""
        if not self.user_id:
            return
        try:
            workspace = await sb.get_or_create_personal_workspace(
                self.user_id, self.user_name or self.user_email.split("@")[0]
            )
            if workspace:
                self.workspace_id = workspace["id"]
                self.workspace_name = workspace["name"]
                self.workspace_invite_code = workspace.get("invite_code", "")
                self.workspace_is_owner = workspace.get("owner_id") == self.user_id
            self.available_workspaces = await sb.get_user_workspaces(self.user_id)
            if self.workspace_id:
                self.workspace_members = await sb.get_workspace_members(self.workspace_id)
        except Exception as e:
            print(f"[auth] _init_workspace error (migration pending?): {e}")

    async def refresh_workspace_members(self):
        if self.workspace_id:
            self.workspace_members = await sb.get_workspace_members(self.workspace_id)

    async def join_workspace(self):
        code = self.workspace_join_code.strip()
        if not code:
            self.workspace_join_error = "Introduce un código de invitación."
            return
        self.workspace_join_error = ""
        self.workspace_join_success = ""
        workspace = await sb.join_workspace_by_code(code, self.user_id)
        if not workspace:
            self.workspace_join_error = "Código inválido o expirado."
            return
        self.workspace_join_success = f"¡Te has unido a «{workspace['name']}»!"
        self.workspace_join_code = ""
        self.available_workspaces = await sb.get_user_workspaces(self.user_id)
        self.workspace_id = workspace["id"]
        self.workspace_name = workspace["name"]
        self.workspace_invite_code = workspace.get("invite_code", "")
        self.workspace_is_owner = workspace.get("owner_id") == self.user_id
        self.workspace_members = await sb.get_workspace_members(self.workspace_id)

        from .app_state import AppState
        from .graph_state import GraphState
        app = await self.get_state(AppState)
        graph = await self.get_state(GraphState)
        graph.active_filter = "all"
        graph.selected_node_id = ""
        graph.panel_open = False
        async for _ in app.load_conversations():
            yield
        async for _ in graph.reload_graph():
            yield

    async def switch_workspace(self, workspace_id: str):
        for w in self.available_workspaces:
            if w["id"] == workspace_id:
                self.workspace_id = w["id"]
                self.workspace_name = w["name"]
                self.workspace_invite_code = w.get("invite_code", "")
                self.workspace_is_owner = w.get("owner_id") == self.user_id
                self.workspace_members = await sb.get_workspace_members(self.workspace_id)
                break
        from .app_state import AppState
        from .graph_state import GraphState
        app = await self.get_state(AppState)
        graph = await self.get_state(GraphState)
        graph.active_filter = "all"
        graph.selected_node_id = ""
        graph.panel_open = False
        async for _ in app.load_conversations():
            yield
        async for _ in graph.reload_graph():
            yield

    async def leave_workspace(self, workspace_id: str):
        """Sale de un workspace (solo si no es owner)."""
        target = next((w for w in self.available_workspaces if w["id"] == workspace_id), None)
        if target and target.get("role") == "owner":
            return
        removed = await sb.remove_workspace_member(workspace_id, self.user_id)
        if not removed:
            return
        self.available_workspaces = await sb.get_user_workspaces(self.user_id)
        # Si salimos del workspace activo, volver al personal
        if self.workspace_id == workspace_id:
            await self._init_workspace()
            from .app_state import AppState
            from .graph_state import GraphState
            app = await self.get_state(AppState)
            graph = await self.get_state(GraphState)
            graph.active_filter = "all"
            graph.selected_node_id = ""
            graph.panel_open = False
            async for _ in app.load_conversations():
                yield
            async for _ in graph.reload_graph():
                yield

    async def remove_member_from_workspace(self, user_id: str):
        """El owner elimina a un miembro del workspace activo."""
        if not self.workspace_is_owner or not self.workspace_id or user_id == self.user_id:
            return
        removed = await sb.remove_workspace_member(self.workspace_id, user_id)
        if removed:
            self.workspace_members = await sb.get_workspace_members(self.workspace_id)

    async def regenerate_invite_code(self):
        if not self.workspace_id:
            await self._init_workspace()
        if not self.workspace_is_owner:
            return
        new_code = await sb.regenerate_invite_code(self.workspace_id)
        if new_code:
            self.workspace_invite_code = new_code
            self.available_workspaces = await sb.get_user_workspaces(self.user_id)

    async def toggle_workspace_panel(self):
        self.show_workspace_panel = not self.show_workspace_panel
        if self.show_workspace_panel and self.workspace_id:
            self.workspace_members = await sb.get_workspace_members(self.workspace_id)

    def set_workspace_join_code(self, v: str):
        self.workspace_join_code = v
        self.workspace_join_error = ""
        self.workspace_join_success = ""

    # ── Setters ──────────────────────────────────────────────────

    def toggle_auth_mode(self):
        self.show_register = not self.show_register
        self.auth_error = ""

    def set_login_email(self, v: str): self.login_email = v
    def set_login_password(self, v: str): self.login_password = v
    def set_register_name(self, v: str): self.register_name = v
    def set_register_email(self, v: str): self.register_email = v
    def set_register_password(self, v: str): self.register_password = v
    def set_register_password_confirm(self, v: str): self.register_password_confirm = v


def _get_initials(name: str) -> str:
    if "@" in name:
        name = name.split("@")[0].replace(".", " ").replace("_", " ")
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif parts:
        return parts[0][:2].upper()
    return "??"


def _translate_auth_error(error: str) -> str:
    error_lower = error.lower()
    mapping = {
        "invalid login credentials": "Email o contraseña incorrectos.",
        "email already registered": "Este email ya está registrado.",
        "user already registered": "Este email ya tiene una cuenta.",
        "email not confirmed": "Confirma tu email antes de iniciar sesión.",
        "too many requests": "Demasiados intentos. Espera un momento.",
    }
    for key, msg in mapping.items():
        if key in error_lower:
            return msg
    return f"Error: {error}"
