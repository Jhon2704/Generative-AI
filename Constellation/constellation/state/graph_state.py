"""
Estado del knowledge graph para CONSTELLATION.
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

import reflex as rx

from ..services import supabase_service as sb
from ..models import NodeItem, ProjectData, node_from_dict, project_from_dict
from ..utils.similarity import calculate_connections, find_related_nodes


class GraphState(rx.State):

    nodes: list[NodeItem] = []
    connections: list[dict] = []
    projects: list[ProjectData] = []
    current_user_id: str = ""

    selected_node_id: str = ""
    selected_tab: str = "summary"
    panel_open: bool = False

    active_filter: str = "all"
    loading: bool = False
    show_project_admin: bool = False

    new_project_name: str = ""
    new_project_emoji: str = "💡"
    new_project_color: str = "#4f8ef7"
    new_project_shape: str = "circle"

    @rx.var
    def filtered_nodes(self) -> list[NodeItem]:
        f = self.active_filter
        if f == "all":
            return self.nodes
        elif f == "mine":
            return [n for n in self.nodes if n.conversations and n.conversations.owner_id == self.current_user_id]
        elif f == "public":
            return [n for n in self.nodes if n.conversations and n.conversations.privacy == "public"]
        else:
            return [n for n in self.nodes if n.conversations and n.conversations.project_id == f]

    @rx.var
    def selected_node(self) -> Optional[NodeItem]:
        if not self.selected_node_id:
            return None
        for n in self.nodes:
            if n.id == self.selected_node_id:
                return n
        return None

    @rx.var
    def related_nodes(self) -> list[NodeItem]:
        if not self.selected_node:
            return []
        target = _node_to_dict(self.selected_node)
        all_dicts = [_node_to_dict(n) for n in self.nodes]
        related = find_related_nodes(target, all_dicts, top_k=5)
        related_ids = {r["node"]["id"] for r in related}
        return [n for n in self.nodes if n.id in related_ids]

    @rx.var
    def graph_data_json(self) -> str:
        node_ids = {n.id for n in self.filtered_nodes}
        graph_nodes = []
        for n in self.filtered_nodes:
            color = "#4f8ef7"
            shape = "circle"
            emoji = ""
            if n.conversations and n.conversations.projects:
                color = n.conversations.projects.color
                shape = n.conversations.projects.shape or "circle"
                emoji = n.conversations.projects.emoji or ""
            graph_nodes.append({
                "id": n.id, "label": n.title or "Sin título",
                "color": color, "pending": n.pending,
                "posX": n.pos_x, "posY": n.pos_y,
                "shape": shape, "emoji": emoji,
                "conversationId": n.conversation_id or "",
            })
        graph_links = []
        for c in self.connections:
            s, t = c.get("source_id", ""), c.get("target_id", "")
            if s in node_ids and t in node_ids:
                graph_links.append({"source": s, "target": t,
                                    "strength": c.get("strength", "weak"),
                                    "score": c.get("score", 0.0)})
        return json.dumps({"nodes": graph_nodes, "links": graph_links})

    # ── Event handlers (yield → solo desde UI o on_load list) ────

    async def load_graph(self, user_id: str = "", workspace_id: str = ""):
        """
        Carga nodos y proyectos en la fase 1 (rápida), luego conexiones en la fase 2.
        Los nodos aparecen en pantalla antes de que estén listas las conexiones.
        """
        if not user_id or not workspace_id:
            from .auth_state import AuthState
            auth = await self.get_state(AuthState)
            user_id = user_id or auth.user_id
            workspace_id = workspace_id or auth.workspace_id

        if not user_id:
            self.nodes = []
            self.projects = []
            self.connections = []
            self.loading = False
            return

        self.loading = True
        self.current_user_id = user_id
        yield

        # ── Fase 1: nodos + proyectos en paralelo (rápido) ───────────
        raw_nodes, raw_projects = await asyncio.gather(
            sb.get_all_nodes(workspace_id=workspace_id, user_id=user_id),
            sb.get_projects(workspace_id=workspace_id, user_id=user_id),
        )
        print(f"[load_graph] fase1: {len(raw_nodes)} nodos, {len(raw_projects)} proyectos")
        self.nodes    = [node_from_dict(d)    for d in raw_nodes]
        self.projects = [project_from_dict(d) for d in raw_projects]
        self.loading  = False
        project_ids = {p.id for p in self.projects}
        if self.active_filter not in ("all", "mine", "public") and self.active_filter not in project_ids:
            self.active_filter = "all"

        node_count = len(self.nodes)
        graph_json = self.graph_data_json
        yield  # → nodos visibles inmediatamente, sin esperar conexiones

        yield rx.call_script(_push_graph_js(graph_json))

        # ── Fase 2: conexiones (puede ser lento la primera vez) ───────
        if node_count < 2:
            return  # Con 0-1 nodos no hay conexiones posibles

        raw_connections = await sb.get_connections()
        print(f"[load_graph] fase2: {len(raw_connections)} conexiones")

        if raw_connections:
            self.connections = raw_connections
        else:
            # Primera vez: calcular en hilo aparte para no bloquear el event loop
            print("[load_graph] node_connections vacío, calculando en background thread...")
            self.connections = await asyncio.to_thread(
                calculate_connections, [_node_to_dict(n) for n in self.nodes]
            )
            asyncio.create_task(sb.upsert_connections_batch(self.connections))
            print(f"[load_graph] {len(self.connections)} conexiones calculadas, persistiendo async")

        # Actualizar grafo con las conexiones añadidas
        graph_json = self.graph_data_json
        yield
        yield rx.call_script(_push_graph_js(graph_json))

    async def reload_graph(self):
        """Recarga el grafo sin cambiar user_id."""
        from .auth_state import AuthState
        auth = await self.get_state(AuthState)
        async for _ in self.load_graph(user_id=auth.user_id or self.current_user_id, workspace_id=auth.workspace_id):
            yield

    # ── Acciones de nodos ────────────────────────────────────────

    def select_node(self, node_id: str):
        self.selected_node_id = node_id
        self.selected_tab = "summary"
        self.panel_open = True

    async def open_conversation(self, conversation_id: str):
        """Doble clic en nodo → ir al chat de esa conversación."""
        if not conversation_id:
            return
        from ..state.app_state import AppState
        app = await self.get_state(AppState)
        async for _ in app.select_conversation(conversation_id):
            yield
        app.active_view = "chat"

    def close_panel(self):
        self.panel_open = False
        self.selected_node_id = ""

    def set_selected_tab(self, tab: str):
        self.selected_tab = tab

    async def set_filter(self, value: str):
        self.active_filter = value
        yield rx.call_script(_push_graph_js(self.graph_data_json))

    def toggle_project_admin(self):
        self.show_project_admin = not self.show_project_admin

    # ── Proyectos ────────────────────────────────────────────────

    async def create_project(self):
        from .auth_state import AuthState
        auth = await self.get_state(AuthState)
        if not self.new_project_name.strip() or not auth.user_id:
            return
        raw = await sb.create_project(
            name=self.new_project_name.strip(),
            emoji=self.new_project_emoji,
            color=self.new_project_color,
            shape=self.new_project_shape,
            user_id=auth.user_id,
            workspace_id=auth.workspace_id,
        )
        if raw:
            self.projects = [*self.projects, project_from_dict(raw)]
            self.new_project_name = ""
            self.new_project_emoji = "📁"
            self.new_project_color = "#4f8ef7"

    async def delete_project(self, project_id: str):
        # Obtener IDs de conversaciones antes de borrarlas
        conv_ids = set(await sb.get_conversation_ids_by_project(project_id))

        # Borrar conversaciones + nodos/mensajes en cascada
        await sb.delete_conversations_by_project(project_id)

        # Borrar el proyecto
        await sb.delete_project(project_id)

        # Actualizar estado local del grafo
        self.projects = [p for p in self.projects if p.id != project_id]
        self.nodes = [n for n in self.nodes if not (
            n.conversations and n.conversations.project_id == project_id
        )]
        # Si el filtro activo era el proyecto eliminado, volver a "todo"
        if self.active_filter == project_id:
            self.active_filter = "all"

        # Actualizar estado del chat (AppState)
        from .app_state import AppState
        app = await self.get_state(AppState)
        app.conversations = [c for c in app.conversations if c.id not in conv_ids]
        if app.current_conversation_id in conv_ids:
            app.current_conversation_id = ""
            app.current_messages = []
            app.show_intro = True

        # Refrescar grafo
        yield rx.call_script(_push_graph_js(self.graph_data_json))

    async def save_node_position(self, node_id: str, x: float, y: float):
        await sb.update_node_position(node_id, x, y)
        self.nodes = [
            NodeItem(id=n.id, conversation_id=n.conversation_id, title=n.title,
                     summary=n.summary, tags=n.tags, semantic=n.semantic,
                     pending=n.pending, pos_x=x, pos_y=y, conversations=n.conversations)
            if n.id == node_id else n
            for n in self.nodes
        ]

    def set_new_project_name(self, v: str): self.new_project_name = v
    def set_new_project_emoji(self, v: str): self.new_project_emoji = v
    def set_new_project_color(self, v: str): self.new_project_color = v
    def set_new_project_shape(self, v: str): self.new_project_shape = v


# ── Helpers de módulo (sin yield, puros) ─────────────────────────

def _push_graph_js(graph_json: str) -> str:
    """Genera el JS para empujar datos al grafo con retry automático."""
    return (
        "(function(){"
        f"var d={graph_json};"
        "var tries=0;"
        "function t(){"
        "  tries++;"
        "  if(window._constellationGraph){"
        "    window._constellationGraph.setData(d);"
        "    if(window._constellationResize) window._constellationResize();"
        "    console.log('[Constellation] setData OK (' + (d.nodes||[]).length + ' nodos, tries='+tries+')');"
        "  } else if(tries<50){ setTimeout(t,100); }"
        "  else{ console.warn('[Constellation] grafo no disponible tras 5s'); }"
        "}"
        "t();"
        "})();"
    )


def _node_to_dict(node: NodeItem) -> dict:
    conv_dict = None
    if node.conversations:
        proj_dict = None
        if node.conversations.projects:
            proj_dict = {
                "id": node.conversations.projects.id,
                "name": node.conversations.projects.name,
                "color": node.conversations.projects.color,
            }
        conv_dict = {
            "id": node.conversations.id,
            "privacy": node.conversations.privacy,
            "project_id": node.conversations.project_id,
            "owner_id": node.conversations.owner_id,
            "projects": proj_dict,
        }
    return {
        "id": node.id, "conversation_id": node.conversation_id,
        "title": node.title, "summary": node.summary,
        "tags": node.tags, "semantic": node.semantic,
        "pending": node.pending, "pos_x": node.pos_x, "pos_y": node.pos_y,
        "conversations": conv_dict,
    }
