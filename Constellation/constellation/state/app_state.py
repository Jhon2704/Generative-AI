"""
Estado principal de CONSTELLATION.
Regla: métodos con `yield` = event handlers.
       métodos sin `yield` = helpers async (await-ables).
"""
from __future__ import annotations

import asyncio
from typing import Optional

import reflex as rx

from ..services import supabase_service as sb
from ..services import ai_service
from ..services.meta_extractor import extract_metadata, format_conversation_for_extraction
from ..services.file_extractor import extract_text
from ..models import ConvItem, SidebarItem, conv_from_dict
from ..utils.similarity import calculate_connections_for_node
from .auth_state import AuthState
from .graph_state import GraphState


class AppState(rx.State):

    conversations: list[ConvItem] = []
    current_conversation_id: str = ""
    current_messages: list[dict] = []

    chat_input: str = ""
    is_streaming: bool = False
    streaming_content: str = ""

    show_intro: bool = False
    intro_title: str = ""
    intro_project_id: str = ""
    intro_privacy: str = "private"

    active_model: str = "claude-haiku-4-5-20251001"
    available_models: list[dict] = []

    search_query: str = ""
    active_view: str = "chat"
    collapsed_projects: list[str] = []
    loading_conversations: bool = False

    # ── Adjunto de archivo ────────────────────────────────────────
    attached_file_name: str = ""
    attached_file_content: str = ""

    # ── Computed vars ────────────────────────────────────────────

    @rx.var
    def filtered_conversations(self) -> list[ConvItem]:
        if not self.search_query.strip():
            return self.conversations
        q = self.search_query.lower()
        return [c for c in self.conversations if q in c.title.lower()]

    @rx.var
    def sidebar_items(self) -> list[SidebarItem]:
        """Lista plana: headers de proyecto + conversaciones, para el sidebar agrupado."""
        project_order: list[str] = []
        project_groups: dict[str, list[ConvItem]] = {}
        no_project: list[ConvItem] = []

        for conv in self.filtered_conversations:
            if conv.project_id:
                if conv.project_id not in project_groups:
                    project_groups[conv.project_id] = []
                    project_order.append(conv.project_id)
                project_groups[conv.project_id].append(conv)
            else:
                no_project.append(conv)

        items: list[SidebarItem] = []

        for pid in project_order:
            convs = project_groups[pid]
            is_collapsed = pid in self.collapsed_projects
            proj = convs[0].projects

            items.append(SidebarItem(
                item_type="header",
                project_id=pid,
                project_name=proj.name if proj else "Proyecto",
                project_emoji=proj.emoji if proj else "📁",
                project_color=proj.color if proj else "#4f8ef7",
                conv_count=len(convs),
                is_collapsed=is_collapsed,
            ))
            if not is_collapsed:
                for conv in convs:
                    items.append(SidebarItem(
                        item_type="conv",
                        project_id=pid,
                        project_color=proj.color if proj else "#4f8ef7",
                        id=conv.id,
                        title=conv.title,
                        privacy=conv.privacy,
                    ))

        if no_project:
            is_collapsed = "__none__" in self.collapsed_projects
            items.append(SidebarItem(
                item_type="header",
                project_id="__none__",
                project_name="Sin proyecto",
                project_emoji="",
                project_color="#444444",
                conv_count=len(no_project),
                is_collapsed=is_collapsed,
            ))
            if not is_collapsed:
                for conv in no_project:
                    items.append(SidebarItem(
                        item_type="conv",
                        project_id="",
                        project_color="#333333",
                        id=conv.id,
                        title=conv.title,
                        privacy=conv.privacy,
                    ))

        return items

    @rx.var
    def current_conversation(self) -> Optional[ConvItem]:
        if not self.current_conversation_id:
            return None
        for c in self.conversations:
            if c.id == self.current_conversation_id:
                return c
        return None

    @rx.var
    def chat_messages(self) -> list[dict]:
        if self.is_streaming and self.streaming_content:
            return [
                *self.current_messages,
                {"role": "assistant", "content": self.streaming_content, "streaming": True},
            ]
        return self.current_messages

    @rx.var
    def is_private(self) -> bool:
        if not self.current_conversation:
            return True
        return self.current_conversation.privacy == "private"

    @rx.var
    def current_conv_title(self) -> str:
        if not self.current_conversation:
            return ""
        return self.current_conversation.title

    # ── on_load: lee auth (ya restaurado) y carga datos ──────────

    async def on_load(self):
        """
        Llamado DESPUÉS de AuthState.restore_session en on_load de add_page.
        Solo lee el estado de auth — no llama métodos de AuthState.
        """
        auth = await self.get_state(AuthState)
        if not auth.is_authenticated:
            return  # restore_session ya habrá redirigido a /auth

        self.active_model = auth.preferred_model
        self.loading_conversations = True
        yield

        # Cargar conversaciones y modelos disponibles en paralelo
        raw_convs, models = await asyncio.gather(
            sb.get_conversations(auth.user_id, auth.workspace_id),
            ai_service.get_available_models(),
        )
        self.conversations = [conv_from_dict(d) for d in raw_convs]
        self.available_models = models
        if self.current_conversation_id and not any(c.id == self.current_conversation_id for c in self.conversations):
            self.current_conversation_id = ""
            self.current_messages = []
        self.loading_conversations = False

        if not self.current_conversation_id:
            self.show_intro = True
        yield

    # ── Conversaciones ────────────────────────────────────────────

    async def load_conversations(self):
        """Recarga la lista (llamado desde UI cuando sea necesario)."""
        self.loading_conversations = True
        yield
        auth = await self.get_state(AuthState)
        if auth.user_id:
            raw = await sb.get_conversations(auth.user_id, auth.workspace_id)
            self.conversations = [conv_from_dict(d) for d in raw]
            if self.current_conversation_id and not any(c.id == self.current_conversation_id for c in self.conversations):
                self.current_conversation_id = ""
                self.current_messages = []
                self.show_intro = True
        self.loading_conversations = False

    async def select_conversation(self, conversation_id: str):
        self.current_conversation_id = conversation_id
        self.show_intro = False
        self.active_view = "chat"
        self.streaming_content = ""
        yield
        auth = await self.get_state(AuthState)
        msgs = await sb.get_messages(conversation_id, user_id=auth.user_id, workspace_id=auth.workspace_id)
        self.current_messages = msgs
        for c in self.conversations:
            if c.id == conversation_id:
                self.active_model = c.model_used or self.active_model
                break

    async def new_conversation(self):
        self.show_intro = True
        self.active_view = "chat"
        self.current_conversation_id = ""
        self.current_messages = []
        self.intro_title = ""
        self.intro_project_id = ""
        self.intro_privacy = "private"
        yield

    async def start_conversation(self):
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            return

        title = self.intro_title.strip() or "Nueva conversación"
        proj_id = self.intro_project_id if self.intro_project_id not in ("", "__none__") else None

        raw = await sb.create_conversation(
            title=title,
            owner_id=auth.user_id,
            privacy=self.intro_privacy,
            project_id=proj_id,
            model_used=self.active_model,
            workspace_id=auth.workspace_id,
        )
        if raw:
            new_conv = conv_from_dict(raw)
            self.conversations = [new_conv, *self.conversations]
            self.current_conversation_id = new_conv.id
            self.current_messages = []
            self.show_intro = False

    async def delete_conversation(self, conversation_id: str):
        await sb.delete_conversation(conversation_id)
        self.conversations = [c for c in self.conversations if c.id != conversation_id]
        if self.current_conversation_id == conversation_id:
            self.current_conversation_id = ""
            self.current_messages = []
            self.show_intro = True

    async def toggle_privacy(self):
        if not self.current_conversation_id:
            return
        new_privacy = "public" if self.is_private else "private"
        await sb.update_conversation(self.current_conversation_id, {"privacy": new_privacy})
        self.conversations = [
            ConvItem(id=c.id, title=c.title, privacy=new_privacy,
                     project_id=c.project_id, owner_id=c.owner_id,
                     model_used=c.model_used, updated_at=c.updated_at,
                     projects=c.projects)
            if c.id == self.current_conversation_id else c
            for c in self.conversations
        ]

    # ── Chat y streaming ──────────────────────────────────────────

    async def send_message(self):
        if not self.chat_input.strip() or self.is_streaming:
            return

        if not self.current_conversation_id:
            await self.start_conversation()

        user_text = self.chat_input.strip()
        # Si hay archivo adjunto, prepend su contenido al mensaje
        if self.attached_file_content:
            user_content = (
                f"[Archivo adjunto: {self.attached_file_name}]\n"
                f"{self.attached_file_content}\n\n"
                f"---\n{user_text}"
            )
        else:
            user_content = user_text
        self.chat_input = ""
        self.attached_file_name = ""
        self.attached_file_content = ""
        self.is_streaming = True
        self.streaming_content = ""
        yield

        user_msg = await sb.add_message(
            conversation_id=self.current_conversation_id,
            role="user", content=user_content,
        )
        if user_msg:
            self.current_messages = [*self.current_messages, user_msg]
        yield

        history = [{"role": m.get("role"), "content": m.get("content", "")}
                   for m in self.current_messages]

        # ── Memoria de proyecto: contexto de otros chats del mismo proyecto ──
        # Acceso directo a self.conversations (evita problemas con @rx.var en backend)
        project_context = ""
        current_conv = next(
            (c for c in self.conversations if c.id == self.current_conversation_id), None
        )
        _pid = repr(current_conv.project_id) if current_conv else "NO_CONV"
        print(f"[memory] conv_id={self.current_conversation_id!r} project_id={_pid}")

        if current_conv and current_conv.project_id:
            proj_summaries = await sb.get_project_summaries(
                current_conv.project_id,
                exclude_conv_id=self.current_conversation_id,
            )
            print(f"[memory] summaries encontrados: {len(proj_summaries)}")

            if proj_summaries:
                proj_name = (
                    current_conv.projects.name
                    if current_conv.projects and current_conv.projects.name
                    else next(
                        (c.projects.name for c in self.conversations
                         if c.project_id == current_conv.project_id and c.projects),
                        "este proyecto",
                    )
                )
                lines = [
                    f"## Memoria del proyecto «{proj_name}»",
                    "Estas son conversaciones anteriores del mismo proyecto. "
                    "Úsalas como contexto para mantener coherencia y no repetir trabajo:",
                ]
                for s in proj_summaries:
                    entry = f"- **{s['title']}**"
                    if s.get("summary"):
                        entry += f": {s['summary']}"
                    elif s.get("tags"):
                        entry += f" (temas: {', '.join(s['tags'][:4])})"
                    lines.append(entry)
                project_context = "\n".join(lines)
                print(f"[memory] Contexto inyectado para «{proj_name}»:\n{project_context[:300]}")

        assistant_content = ""
        base_prompt = (
            "Eres un asistente de Constellation Guide. Puedes ayudar con cualquier tema que el usuario necesite. "
            "Sé preciso, profesional y conciso en tus respuestas."
        )
        if project_context:
            system_prompt = f"{base_prompt}\n\n{project_context}"
        else:
            system_prompt = (
                f"{base_prompt} "
                "IMPORTANTE: recuerda siempre al usuario que vincule sus conversaciones a un proyecto "
                "para no perder el contexto y mantener el knowledge graph organizado. "
                "Si el usuario no ha mencionado ningún proyecto en la conversación actual, "
                "recuérdale brevemente al final de tu respuesta que puede asignar esta conversación a un proyecto."
            )
        try:
            async for chunk in ai_service.stream_chat(
                model_id=self.active_model,
                messages=history,
                system_prompt=system_prompt,
            ):
                assistant_content += chunk
                self.streaming_content = assistant_content
                yield
        except Exception as e:
            assistant_content = f"*Error: {e}*"
            self.streaming_content = assistant_content
            yield

        assistant_msg = await sb.add_message(
            conversation_id=self.current_conversation_id,
            role="assistant", content=assistant_content,
        )
        if assistant_msg:
            self.current_messages = [*self.current_messages, assistant_msg]

        self.streaming_content = ""
        self.is_streaming = False
        yield

        # Crear nodo en background si es el primer mensaje
        user_count = sum(1 for m in self.current_messages if m.get("role") == "user")
        print(f"[send_message] user_count={user_count}, conv_id={self.current_conversation_id}")
        if user_count == 1:
            print(f"[send_message] Lanzando _create_node_bg...")
            try:
                task = asyncio.create_task(self._create_node_bg(
                    self.current_conversation_id,
                    list(self.current_messages),
                ))
                task.add_done_callback(lambda t: print(f"[node_task] done, exception={t.exception() if not t.cancelled() else 'cancelled'}"))
            except Exception as e:
                print(f"[send_message] create_task ERROR: {e}")

    async def _create_node_bg(self, conversation_id: str, messages: list[dict]):
        """Crea y popula el nodo del grafo en background (solo Supabase, sin yield)."""
        try:
            node = await sb.create_node(conversation_id)
            if not node:
                print(f"[node_bg] ERROR: create_node devolvió None para conv {conversation_id}")
                return
            print(f"[node_bg] Nodo pendiente creado: {node['id']}")

            conv_text = format_conversation_for_extraction(messages)
            meta = await extract_metadata(conv_text, ai_service.MODEL_HAIKU)
            print(f"[node_bg] Metadatos extraídos: {meta.get('title', '?')}")

            # Sincronizar título: priorizar el del chat; si es genérico, usar el de IA
            # y actualizar también la conversación para que sidebar y grafo coincidan
            conv_data = await sb.get_conversation(conversation_id)
            conv_title = (conv_data.get("title", "") if conv_data else "").strip()
            generic_titles = {"nueva conversación", "new conversation", ""}
            ai_title = meta.get("title", "Sin título")

            if conv_title.lower() in generic_titles:
                # Título genérico → usar el de IA y actualizar la conversación
                final_title = ai_title
                await sb.update_conversation(conversation_id, {"title": final_title})
                print(f"[node_bg] Título actualizado en conversación: {final_title}")
            else:
                # El usuario puso un título propio → respetarlo en el nodo
                final_title = conv_title

            updated_data = {
                "title":    final_title,
                "summary":  meta.get("summary", ""),
                "tags":     meta.get("tags", []),
                "semantic": meta.get("semantic", ""),
                "pending":  False,
            }
            await sb.update_node(node["id"], updated_data)
            print(f"[node_bg] Nodo actualizado en Supabase OK")

            # Calcular conexiones para este nodo vs todos los existentes (O(n))
            all_nodes = await sb.get_all_nodes(
                workspace_id=conv_data.get("workspace_id", "") if conv_data else "",
                user_id=conv_data.get("owner_id", "") if conv_data else "",
            )
            new_node_dict = {**node, **updated_data, "conversations": next(
                (n.get("conversations") for n in all_nodes if n["id"] == node["id"]), None
            )}
            new_connections = calculate_connections_for_node(new_node_dict, all_nodes)
            if new_connections:
                await sb.upsert_connections_batch(new_connections)
                print(f"[node_bg] {len(new_connections)} conexiones persistidas en batch")
        except Exception as e:
            print(f"[node_bg] EXCEPCIÓN: {e}")

    # ── UI helpers ────────────────────────────────────────────────

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Lee el primer archivo subido y extrae su texto."""
        if not files:
            return
        file = files[0]
        data = await file.read()
        text = await extract_text(file.filename, data)
        self.attached_file_name = file.filename
        self.attached_file_content = text

    def clear_attachment(self):
        self.attached_file_name = ""
        self.attached_file_content = ""

    def set_show_intro_false(self):
        if self.current_conversation_id:
            self.show_intro = False

    def set_chat_input(self, v: str): self.chat_input = v
    def set_active_model(self, v: str): self.active_model = v
    def set_search_query(self, v: str): self.search_query = v
    def set_active_view(self, v: str): self.active_view = v
    def set_intro_title(self, v: str): self.intro_title = v
    def set_intro_project_id(self, v: str): self.intro_project_id = v
    def set_intro_privacy(self, v: str): self.intro_privacy = v

    def toggle_project_collapse(self, project_id: str):
        if project_id in self.collapsed_projects:
            self.collapsed_projects = [p for p in self.collapsed_projects if p != project_id]
        else:
            self.collapsed_projects = [*self.collapsed_projects, project_id]

    async def handle_key_down(self, key: str):
        if key == "Enter":
            async for _ in self.send_message():
                yield
