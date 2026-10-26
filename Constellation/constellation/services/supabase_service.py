"""
Servicio de Supabase para CONSTELLATION.
El cliente se crea con el token del usuario en cada operación autenticada
para que el RLS funcione correctamente.
"""
from __future__ import annotations

import os
import random as _random
import string as _string
from typing import Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ── Credenciales del entorno ──────────────────────────────────
_SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
_SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")
_SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

# ── Sesión activa (access token del usuario logueado) ─────────
_current_access_token: str = ""
_current_refresh_token: str = ""

# ── Cliente cacheado (evita crear conexión nueva en cada query) ─
_client: Optional[Client] = None
_cached_token: str = ""


def get_supabase_admin() -> Client:
    """
    Cliente con service role key — bypasea RLS para operaciones admin.
    Usa SUPABASE_SERVICE_KEY; si no está configurado, cae al cliente anon.
    """
    key = _SUPABASE_SERVICE_KEY or _SUPABASE_ANON_KEY
    if not _SUPABASE_URL or not key:
        raise EnvironmentError("Configura SUPABASE_URL y SUPABASE_SERVICE_KEY en el archivo .env")
    return create_client(_SUPABASE_URL, key)


def get_supabase(access_token: str = "") -> Client:
    """
    Devuelve el cliente Supabase cacheado, re-autenticando solo si el token cambia.
    """
    global _client, _cached_token
    if not _SUPABASE_URL or not _SUPABASE_ANON_KEY:
        raise EnvironmentError(
            "Configura SUPABASE_URL y SUPABASE_ANON_KEY en el archivo .env"
        )
    token = access_token or _current_access_token
    if _client is None:
        _client = create_client(_SUPABASE_URL, _SUPABASE_ANON_KEY)
        _cached_token = ""
    if token != _cached_token:
        _client.postgrest.auth(token)
        _cached_token = token
    return _client


def set_session_token(access_token: str, refresh_token: str) -> None:
    """Guarda los tokens de sesión globalmente para usarlos en cada llamada."""
    global _current_access_token, _current_refresh_token
    _current_access_token = access_token
    _current_refresh_token = refresh_token


def _generate_invite_code() -> str:
    chars = _string.ascii_uppercase + _string.digits
    return ''.join(_random.choices(chars, k=8))


def _is_workspace_member(admin: Client, workspace_id: str, user_id: str) -> bool:
    """Comprueba membresÃ­a antes de usar el cliente admin para datos de workspace."""
    if not workspace_id or not user_id:
        return False
    try:
        resp = (
            admin.table("workspace_members")
            .select("workspace_id")
            .eq("workspace_id", workspace_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return bool(resp.data)
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# WORKSPACES
# ══════════════════════════════════════════════════════════════

async def get_or_create_personal_workspace(user_id: str, display_name: str = "Mi espacio") -> Optional[dict[str, Any]]:
    """Crea o devuelve el workspace personal del usuario. Migra datos sin workspace."""
    try:
        admin = get_supabase_admin()
        # Buscar workspace donde el usuario es owner
        resp = admin.table("workspaces").select("*").eq("owner_id", user_id).execute()
        workspace = resp.data[0] if resp.data else None

        if not workspace:
            resp = admin.table("workspaces").insert({
                "name": display_name or "Mi espacio",
                "owner_id": user_id,
                "invite_code": _generate_invite_code(),
            }).execute()
            workspace = resp.data[0] if resp.data else None

        if workspace:
            wid = workspace["id"]
            # Asegurar entrada en workspace_members como owner
            admin.table("workspace_members").upsert(
                {"workspace_id": wid, "user_id": user_id, "role": "owner"},
                on_conflict="workspace_id,user_id",
            ).execute()
            # Migrar datos huérfanos (sin workspace_id)
            admin.table("conversations").update({"workspace_id": wid}) \
                .eq("owner_id", user_id).is_("workspace_id", "null").execute()
            admin.table("projects").update({"workspace_id": wid}) \
                .eq("created_by", user_id).is_("workspace_id", "null").execute()

        return workspace
    except Exception as e:
        print(f"[supabase] get_or_create_personal_workspace error: {e}")
        return None


async def get_user_workspaces(user_id: str) -> list[dict[str, Any]]:
    """Todos los workspaces a los que pertenece el usuario."""
    try:
        resp = (
            get_supabase_admin().table("workspace_members")
            .select("role, workspaces(id, name, owner_id, invite_code)")
            .eq("user_id", user_id).execute()
        )
        result = []
        for row in (resp.data or []):
            w = row.get("workspaces")
            if w:
                w["role"] = row.get("role", "member")
                result.append(w)
        return result
    except Exception as e:
        print(f"[supabase] get_user_workspaces error: {e}")
        return []


async def join_workspace_by_code(invite_code: str, user_id: str) -> Optional[dict[str, Any]]:
    """Une al usuario a un workspace por su código de invitación."""
    try:
        admin = get_supabase_admin()
        resp = admin.table("workspaces").select("*").eq("invite_code", invite_code.upper().strip()).execute()
        if not resp.data:
            return None
        workspace = resp.data[0]
        admin.table("workspace_members").upsert(
            {"workspace_id": workspace["id"], "user_id": user_id, "role": "member"},
            on_conflict="workspace_id,user_id",
        ).execute()
        return workspace
    except Exception as e:
        print(f"[supabase] join_workspace_by_code error: {e}")
        return None


async def regenerate_invite_code(workspace_id: str) -> Optional[str]:
    """Genera un nuevo código de invitación para el workspace."""
    try:
        new_code = _generate_invite_code()
        get_supabase_admin().table("workspaces").update({"invite_code": new_code}).eq("id", workspace_id).execute()
        return new_code
    except Exception as e:
        print(f"[supabase] regenerate_invite_code error: {e}")
        return None


async def get_workspace_members(workspace_id: str) -> list[dict[str, Any]]:
    """Lista de miembros del workspace con nombre y email."""
    try:
        admin = get_supabase_admin()
        resp = (
            admin.table("workspace_members")
            .select("user_id, role, joined_at")
            .eq("workspace_id", workspace_id)
            .execute()
        )
        rows = resp.data or []
        user_ids = [row.get("user_id") for row in rows if row.get("user_id")]

        profiles_by_id: dict[str, dict[str, Any]] = {}
        if user_ids:
            profiles_resp = (
                admin.table("users")
                .select("id, name, email")
                .in_("id", user_ids)
                .execute()
            )
            profiles_by_id = {
                str(profile.get("id", "")): profile
                for profile in (profiles_resp.data or [])
            }

        members = []
        for row in rows:
            user_id = str(row.get("user_id", ""))
            user = profiles_by_id.get(user_id, {})
            members.append({
                "user_id": user_id,
                "role": row.get("role", "member"),
                "joined_at": row.get("joined_at", ""),
                "user_name": user.get("name", "") or user.get("email", "") or f"Usuario {user_id[:8]}",
                "user_email": user.get("email", ""),
            })
        return members
    except Exception as e:
        print(f"[supabase] get_workspace_members error: {e}")
        return []


async def remove_workspace_member(workspace_id: str, user_id: str) -> bool:
    """Elimina un miembro del workspace (owner puede expulsar, miembro puede salir)."""
    try:
        admin = get_supabase_admin()
        workspace_resp = admin.table("workspaces").select("owner_id").eq("id", workspace_id).single().execute()
        if workspace_resp.data and workspace_resp.data.get("owner_id") == user_id:
            return False
        admin.table("workspace_members") \
            .delete().eq("workspace_id", workspace_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"[supabase] remove_workspace_member error: {e}")
        return False


def get_current_user() -> Any:
    """Devuelve el usuario autenticado actual usando el token guardado."""
    try:
        client = create_client(_SUPABASE_URL, _SUPABASE_ANON_KEY)
        if _current_access_token:
            resp = client.auth.get_user(_current_access_token)
            return resp.user
        return None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════

async def sign_up(email: str, password: str, name: str) -> dict[str, Any]:
    try:
        # Cliente fresco para auth — evita que tokens cacheados contaminen la petición
        fresh = create_client(_SUPABASE_URL, _SUPABASE_ANON_KEY)
        resp = fresh.auth.sign_up({
            "email": email, "password": password,
            "options": {"data": {"name": name}},
        })
        if resp.session:
            set_session_token(resp.session.access_token, resp.session.refresh_token)
        return {"user": resp.user, "session": resp.session, "error": None}
    except Exception as e:
        return {"user": None, "session": None, "error": str(e)}


async def sign_in(email: str, password: str) -> dict[str, Any]:
    try:
        # Cliente fresco para auth — evita que tokens cacheados contaminen la petición
        fresh = create_client(_SUPABASE_URL, _SUPABASE_ANON_KEY)
        resp = fresh.auth.sign_in_with_password({"email": email, "password": password})
        if resp.session:
            set_session_token(resp.session.access_token, resp.session.refresh_token)
        return {"user": resp.user, "session": resp.session, "error": None}
    except Exception as e:
        return {"user": None, "session": None, "error": str(e)}


async def sign_out() -> None:
    global _current_access_token, _current_refresh_token
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    _current_access_token = ""
    _current_refresh_token = ""


# ══════════════════════════════════════════════════════════════
# USUARIOS
# ══════════════════════════════════════════════════════════════

async def get_user_profile(user_id: str) -> Optional[dict[str, Any]]:
    try:
        resp = get_supabase().table("users").select("*").eq("id", user_id).single().execute()
        return resp.data
    except Exception:
        return None


async def update_user_profile(user_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        resp = get_supabase().table("users").update(data).eq("id", user_id).execute()
        return resp.data[0] if resp.data else None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# PROYECTOS
# ══════════════════════════════════════════════════════════════

async def get_projects(workspace_id: str = "", user_id: str = "") -> list[dict[str, Any]]:
    try:
        if workspace_id and user_id:
            admin = get_supabase_admin()
            if _is_workspace_member(admin, workspace_id, user_id):
                resp = (
                    admin.table("projects")
                    .select("*")
                    .eq("workspace_id", workspace_id)
                    .order("created_at")
                    .execute()
                )
                return resp.data or []
        q = get_supabase().table("projects").select("*")
        if workspace_id:
            try:
                resp = q.eq("workspace_id", workspace_id).order("created_at").execute()
                if resp.data is not None:
                    return resp.data
            except Exception:
                pass
        if user_id:
            resp = q.eq("created_by", user_id).order("created_at").execute()
            return resp.data or []
        resp = q.order("created_at").execute()
        return resp.data or []
    except Exception as e:
        print(f"[supabase] get_projects error: {e}")
        return []


async def create_project(name: str, emoji: str, color: str, shape: str, user_id: str, workspace_id: str = "") -> Optional[dict[str, Any]]:
    try:
        data = {"name": name, "emoji": emoji, "color": color, "shape": shape, "created_by": user_id}
        if workspace_id:
            data["workspace_id"] = workspace_id
        resp = get_supabase().table("projects").insert(data).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        try:
            data.pop("shape", None)
            resp = get_supabase().table("projects").insert(data).execute()
            return resp.data[0] if resp.data else None
        except Exception as e2:
            print(f"[supabase] create_project error: {e2}")
            return None


async def get_project_summaries(project_id: str, exclude_conv_id: str = "") -> list[dict[str, Any]]:
    """
    Contexto de memoria de un proyecto: título + resumen de cada conversación.
    - Query 1: conversaciones del proyecto (títulos siempre disponibles)
    - Query 2: nodos procesados (resúmenes y tags, opcionales)
    Usa admin client para evitar restricciones de RLS.
    """
    try:
        admin = get_supabase_admin()

        # Query 1: todas las conversaciones del proyecto
        conv_resp = (
            admin.table("conversations")
            .select("id, title")
            .eq("project_id", project_id)
            .execute()
        )
        convs = {
            c["id"]: {"title": c.get("title", ""), "summary": "", "tags": []}
            for c in (conv_resp.data or [])
            if c["id"] != exclude_conv_id
        }
        if not convs:
            return []

        # Query 2: nodos (con resumen) para esas conversaciones
        node_resp = (
            admin.table("nodes")
            .select("conversation_id, title, summary, tags, pending")
            .in_("conversation_id", list(convs.keys()))
            .execute()
        )
        for node in (node_resp.data or []):
            cid = node.get("conversation_id")
            if cid not in convs:
                continue
            # Preferir título del nodo si es más descriptivo que el del chat
            node_title = node.get("title", "")
            generic = {"nueva conversación", "new conversation", "sin título", ""}
            if node_title and node_title.lower() not in generic:
                convs[cid]["title"] = node_title
            # Resumen y tags solo si el nodo está procesado
            if not node.get("pending", True):
                convs[cid]["summary"] = node.get("summary", "")
                raw_tags = node.get("tags") or []
                if isinstance(raw_tags, str):
                    import json as _json
                    try:
                        raw_tags = _json.loads(raw_tags)
                    except Exception:
                        raw_tags = []
                convs[cid]["tags"] = raw_tags

        # Filtrar entradas sin título útil
        generic_set = {"nueva conversación", "new conversation", "sin título", ""}
        results = [
            v for v in convs.values()
            if v["title"] and v["title"].lower() not in generic_set
        ]
        print(f"[supabase] get_project_summaries project={project_id!r}: {len(results)} convs")
        return results
    except Exception as e:
        print(f"[supabase] get_project_summaries error: {e}")
        return []


async def get_conversation_ids_by_project(project_id: str) -> list[str]:
    try:
        resp = (
            get_supabase_admin().table("conversations")
            .select("id").eq("project_id", project_id).execute()
        )
        return [row["id"] for row in (resp.data or [])]
    except Exception as e:
        print(f"[supabase] get_conversation_ids_by_project error: {e}")
        return []


async def delete_conversations_by_project(project_id: str) -> None:
    """Elimina todas las conversaciones (y sus nodos/mensajes en cascada) de un proyecto."""
    try:
        get_supabase_admin().table("conversations").delete().eq("project_id", project_id).execute()
    except Exception as e:
        print(f"[supabase] delete_conversations_by_project error: {e}")


async def delete_project(project_id: str) -> bool:
    try:
        get_supabase_admin().table("projects").delete().eq("id", project_id).execute()
        return True
    except Exception as e:
        print(f"[supabase] delete_project error: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# CONVERSACIONES
# ══════════════════════════════════════════════════════════════

async def create_conversation(
    title: str, owner_id: str,
    privacy: str = "private",
    project_id: Optional[str] = None,
    model_used: str = "claude-haiku",
    workspace_id: str = "",
) -> Optional[dict[str, Any]]:
    try:
        data = {
            "title": title, "owner_id": owner_id,
            "privacy": privacy, "project_id": project_id, "model_used": model_used,
        }
        if workspace_id:
            data["workspace_id"] = workspace_id
        resp = get_supabase().table("conversations").insert(data).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        print(f"[supabase] create_conversation error: {e}")
        return None


async def get_conversations(user_id: str, workspace_id: str = "") -> list[dict[str, Any]]:
    try:
        if workspace_id and user_id:
            admin = get_supabase_admin()
            if _is_workspace_member(admin, workspace_id, user_id):
                resp = (
                    admin.table("conversations")
                    .select("*, projects(id, name, emoji, color)")
                    .eq("workspace_id", workspace_id)
                    .order("updated_at", desc=True)
                    .execute()
                )
                return resp.data or []
        q = get_supabase().table("conversations").select("*, projects(id, name, emoji, color)")
        if workspace_id:
            try:
                resp = q.eq("workspace_id", workspace_id).order("updated_at", desc=True).execute()
                if resp.data is not None:
                    return resp.data
            except Exception:
                pass
        resp = q.eq("owner_id", user_id).order("updated_at", desc=True).execute()
        return resp.data or []
    except Exception as e:
        print(f"[supabase] get_conversations error: {e}")
        return []


async def get_conversation(conversation_id: str) -> Optional[dict[str, Any]]:
    try:
        resp = (
            get_supabase().table("conversations")
            .select("*, projects(id, name, emoji, color)")
            .eq("id", conversation_id).single().execute()
        )
        return resp.data
    except Exception:
        return None


async def update_conversation(conversation_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        resp = get_supabase().table("conversations").update(data).eq("id", conversation_id).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        print(f"[supabase] update_conversation error: {e}")
        return None


async def delete_conversation(conversation_id: str) -> bool:
    try:
        get_supabase().table("conversations").delete().eq("id", conversation_id).execute()
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# MENSAJES
# ══════════════════════════════════════════════════════════════

async def add_message(
    conversation_id: str, role: str, content: str,
    tokens_used: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    try:
        resp = get_supabase().table("messages").insert({
            "conversation_id": conversation_id,
            "role": role, "content": content, "tokens_used": tokens_used,
        }).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        print(f"[supabase] add_message error: {e}")
        return None


async def get_messages(conversation_id: str, user_id: str = "", workspace_id: str = "") -> list[dict[str, Any]]:
    try:
        if workspace_id and user_id:
            admin = get_supabase_admin()
            if _is_workspace_member(admin, workspace_id, user_id):
                conv_resp = (
                    admin.table("conversations")
                    .select("id")
                    .eq("id", conversation_id)
                    .eq("workspace_id", workspace_id)
                    .limit(1)
                    .execute()
                )
                if conv_resp.data:
                    resp = (
                        admin.table("messages")
                        .select("*").eq("conversation_id", conversation_id)
                        .order("created_at").execute()
                    )
                    return resp.data or []
        resp = (
            get_supabase().table("messages")
            .select("*").eq("conversation_id", conversation_id)
            .order("created_at").execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"[supabase] get_messages error: {e}")
        return []


# ══════════════════════════════════════════════════════════════
# NODOS DEL GRAFO
# ══════════════════════════════════════════════════════════════

async def create_node(conversation_id: str) -> Optional[dict[str, Any]]:
    try:
        resp = get_supabase().table("nodes").insert({
            "conversation_id": conversation_id, "pending": True,
        }).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        print(f"[supabase] create_node error: {e}")
        return None


async def update_node(node_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        resp = get_supabase().table("nodes").update(data).eq("id", node_id).execute()
        return resp.data[0] if resp.data else None
    except Exception:
        return None


def _nodes_with_conversation_query(client: Client):
    return client.table("nodes").select(
        "*, conversations(id, title, privacy, project_id, owner_id, projects(id, name, emoji, color, shape))"
    )


def _nodes_with_conversation_query_legacy(client: Client):
    return client.table("nodes").select(
        "*, conversations(id, title, privacy, project_id, owner_id, projects(id, name, emoji, color))"
    )


def _execute_nodes_query(client: Client, conv_ids: list[str]):
    try:
        return (
            _nodes_with_conversation_query(client)
            .in_("conversation_id", conv_ids)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        if "shape" not in str(e):
            raise
        return (
            _nodes_with_conversation_query_legacy(client)
            .in_("conversation_id", conv_ids)
            .order("created_at", desc=True)
            .execute()
        )


async def get_all_nodes(workspace_id: str = "", user_id: str = "") -> list[dict[str, Any]]:
    try:
        if workspace_id and user_id:
            admin = get_supabase_admin()
            if _is_workspace_member(admin, workspace_id, user_id):
                conv_resp = (
                    admin.table("conversations")
                    .select("id")
                    .eq("workspace_id", workspace_id)
                    .execute()
                )
                conv_ids = [r["id"] for r in (conv_resp.data or [])]
                if not conv_ids:
                    return []
                resp = _execute_nodes_query(admin, conv_ids)
                nodes = resp.data or []
                node_conv_ids = {n.get("conversation_id") for n in nodes}
                missing = [
                    {"conversation_id": cid, "pending": True}
                    for cid in conv_ids
                    if cid not in node_conv_ids
                ]
                if missing:
                    try:
                        admin.table("nodes").upsert(
                            missing,
                            on_conflict="conversation_id",
                        ).execute()
                        resp = _execute_nodes_query(admin, conv_ids)
                        nodes = resp.data or []
                    except Exception as e:
                        print(f"[supabase] create missing workspace nodes skipped: {e}")
                return nodes

        # Paso 1: obtener IDs de conversaciones del usuario/workspace
        conv_ids: list[str] = []
        if workspace_id:
            try:
                resp = get_supabase().table("conversations").select("id").eq("workspace_id", workspace_id).execute()
                conv_ids = [r["id"] for r in (resp.data or [])]
            except Exception:
                pass
        if not conv_ids and user_id:
            resp = get_supabase().table("conversations").select("id").eq("owner_id", user_id).execute()
            conv_ids = [r["id"] for r in (resp.data or [])]

        if not conv_ids:
            return []

        # Paso 2: nodos filtrados por esas conversaciones
        client = get_supabase()
        resp = _execute_nodes_query(client, conv_ids)
        nodes = resp.data or []
        node_conv_ids = {n.get("conversation_id") for n in nodes}
        missing = [
            {"conversation_id": cid, "pending": True}
            for cid in conv_ids
            if cid not in node_conv_ids
        ]
        if missing:
            try:
                client.table("nodes").upsert(
                    missing,
                    on_conflict="conversation_id",
                ).execute()
                resp = _execute_nodes_query(client, conv_ids)
                nodes = resp.data or []
            except Exception as e:
                print(f"[supabase] create missing nodes skipped: {e}")
        return nodes
    except Exception as e:
        print(f"[supabase] get_all_nodes error: {e}")
        return []


async def update_node_position(node_id: str, x: float, y: float) -> None:
    try:
        get_supabase().table("nodes").update({"pos_x": x, "pos_y": y}).eq("id", node_id).execute()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
# CONEXIONES DEL GRAFO
# ══════════════════════════════════════════════════════════════

async def get_connections() -> list[dict[str, Any]]:
    """Devuelve todas las conexiones persistidas en node_connections."""
    try:
        resp = (
            get_supabase().table("node_connections")
            .select("source_id, target_id, strength, score")
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"[supabase] get_connections error: {e}")
        return []


async def upsert_connections_batch(connections: list[dict[str, Any]]) -> None:
    """Inserta o actualiza múltiples conexiones en una sola llamada HTTP."""
    if not connections:
        return
    try:
        get_supabase().table("node_connections").upsert(
            connections,
            on_conflict="source_id,target_id",
        ).execute()
    except Exception as e:
        print(f"[supabase] upsert_connections_batch error: {e}")
