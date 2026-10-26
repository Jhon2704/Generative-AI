-- ═══════════════════════════════════════════════════════════════
-- CONSTELLATION — Schema completo de Supabase
-- ALTEN Spain · Knowledge Graph Corporativo
-- ═══════════════════════════════════════════════════════════════

-- Habilitar extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Para búsqueda de texto

-- ──────────────────────────────────────────────────────────────
-- TABLA: users (perfil extendido sobre auth.users de Supabase)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE public.users (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL DEFAULT '',
    email       TEXT NOT NULL,
    -- Modelo preferido: claude-sonnet-4, claude-haiku, mistral, llama3
    preferred_model TEXT NOT NULL DEFAULT 'claude-haiku',
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.users IS 'Perfil extendido de usuarios ALTEN. Vinculado a auth.users.';

-- ──────────────────────────────────────────────────────────────
-- TABLA: projects (proyectos/áreas de conocimiento)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE public.projects (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    emoji       TEXT NOT NULL DEFAULT '📁',
    -- Color hex para nodos del grafo (p.ej. '#4f8ef7')
    color       TEXT NOT NULL DEFAULT '#4f8ef7',
    created_by  UUID NOT NULL REFERENCES public.users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.projects IS 'Proyectos corporativos. Cada proyecto agrupa conversaciones y nodos del grafo.';

-- ──────────────────────────────────────────────────────────────
-- TABLA: conversations (conversaciones con IA)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE public.conversations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       TEXT NOT NULL DEFAULT 'Nueva conversación',
    -- 'public' visible para el equipo, 'private' solo el owner
    privacy     TEXT NOT NULL DEFAULT 'private' CHECK (privacy IN ('public', 'private')),
    project_id  UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    owner_id    UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    -- Modelo de IA usado: claude-sonnet-4, claude-haiku, mistral, llama3
    model_used  TEXT NOT NULL DEFAULT 'claude-haiku',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.conversations IS 'Conversaciones con IA. Cada conversación genera un nodo en el grafo.';

-- Índice para búsqueda por owner y proyecto
CREATE INDEX idx_conversations_owner ON public.conversations(owner_id);
CREATE INDEX idx_conversations_project ON public.conversations(project_id);
CREATE INDEX idx_conversations_privacy ON public.conversations(privacy);

-- ──────────────────────────────────────────────────────────────
-- TABLA: messages (mensajes de cada conversación)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE public.messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    -- 'user' o 'assistant'
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL DEFAULT '',
    -- Tokens usados (para métricas)
    tokens_used     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.messages IS 'Mensajes individuales dentro de cada conversación.';

CREATE INDEX idx_messages_conversation ON public.messages(conversation_id);
CREATE INDEX idx_messages_created_at ON public.messages(created_at);

-- ──────────────────────────────────────────────────────────────
-- TABLA: nodes (nodos del knowledge graph)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE public.nodes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID UNIQUE NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    -- Título extraído por IA
    title           TEXT NOT NULL DEFAULT '',
    -- Resumen generado por IA (2-3 frases)
    summary         TEXT NOT NULL DEFAULT '',
    -- Tags como array JSON: ["kubernetes", "devops", "ci-cd"]
    tags            JSONB NOT NULL DEFAULT '[]',
    -- Descripción semántica para cálculo de similitud
    semantic        TEXT NOT NULL DEFAULT '',
    -- true = IA aún procesando metadatos
    pending         BOOLEAN NOT NULL DEFAULT TRUE,
    -- Posición en el canvas (para recordar layout)
    pos_x           FLOAT DEFAULT 0,
    pos_y           FLOAT DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.nodes IS 'Nodos del knowledge graph. Uno por conversación. La IA extrae título, resumen y tags.';

CREATE INDEX idx_nodes_conversation ON public.nodes(conversation_id);
CREATE INDEX idx_nodes_pending ON public.nodes(pending);
-- Índice GIN para búsqueda en tags JSON
CREATE INDEX idx_nodes_tags ON public.nodes USING GIN (tags);

-- ──────────────────────────────────────────────────────────────
-- TABLA: node_connections (conexiones entre nodos del grafo)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE public.node_connections (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id   UUID NOT NULL REFERENCES public.nodes(id) ON DELETE CASCADE,
    target_id   UUID NOT NULL REFERENCES public.nodes(id) ON DELETE CASCADE,
    -- 'strong' mismo proyecto, 'weak' similitud semántica Jaccard
    strength    TEXT NOT NULL DEFAULT 'weak' CHECK (strength IN ('strong', 'weak')),
    -- Puntuación de similitud [0.0 - 1.0]
    score       FLOAT NOT NULL DEFAULT 0.0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- No duplicar conexiones bidireccionales
    UNIQUE(source_id, target_id)
);

COMMENT ON TABLE public.node_connections IS 'Aristas del grafo. strong = mismo proyecto, weak = similitud Jaccard ≥ 0.15.';

CREATE INDEX idx_connections_source ON public.node_connections(source_id);
CREATE INDEX idx_connections_target ON public.node_connections(target_id);

-- ══════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS)
-- ══════════════════════════════════════════════════════════════

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.node_connections ENABLE ROW LEVEL SECURITY;

-- ── USERS ──
-- Cada usuario ve y edita solo su perfil
CREATE POLICY "users_select_own" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "users_update_own" ON public.users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "users_insert_own" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

-- ── PROJECTS ──
-- Todos los usuarios autenticados ven todos los proyectos
CREATE POLICY "projects_select_authenticated" ON public.projects
    FOR SELECT USING (auth.role() = 'authenticated');

-- Solo el creador puede modificar/eliminar
CREATE POLICY "projects_insert_own" ON public.projects
    FOR INSERT WITH CHECK (auth.uid() = created_by);

CREATE POLICY "projects_delete_own" ON public.projects
    FOR DELETE USING (auth.uid() = created_by);

-- ── CONVERSATIONS ──
-- El owner siempre ve sus conversaciones; las públicas las ve todo el equipo
CREATE POLICY "conversations_select" ON public.conversations
    FOR SELECT USING (
        auth.uid() = owner_id
        OR privacy = 'public'
    );

CREATE POLICY "conversations_insert_own" ON public.conversations
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "conversations_update_own" ON public.conversations
    FOR UPDATE USING (auth.uid() = owner_id);

CREATE POLICY "conversations_delete_own" ON public.conversations
    FOR DELETE USING (auth.uid() = owner_id);

-- ── MESSAGES ──
-- Sigue la privacidad de la conversación padre
CREATE POLICY "messages_select" ON public.messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id
              AND (c.owner_id = auth.uid() OR c.privacy = 'public')
        )
    );

CREATE POLICY "messages_insert" ON public.messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id
              AND c.owner_id = auth.uid()
        )
    );

-- ── NODES ──
-- Sigue la privacidad de la conversación padre
CREATE POLICY "nodes_select" ON public.nodes
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id
              AND (c.owner_id = auth.uid() OR c.privacy = 'public')
        )
    );

CREATE POLICY "nodes_insert" ON public.nodes
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id
              AND c.owner_id = auth.uid()
        )
    );

CREATE POLICY "nodes_update" ON public.nodes
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id
              AND c.owner_id = auth.uid()
        )
    );

-- ── NODE_CONNECTIONS ──
-- Visible si al menos uno de los nodos es visible
CREATE POLICY "connections_select" ON public.node_connections
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.nodes n
            JOIN public.conversations c ON c.id = n.conversation_id
            WHERE n.id = source_id
              AND (c.owner_id = auth.uid() OR c.privacy = 'public')
        )
    );

CREATE POLICY "connections_insert" ON public.node_connections
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- ══════════════════════════════════════════════════════════════
-- TRIGGERS Y FUNCIONES
-- ══════════════════════════════════════════════════════════════

-- Función: crear perfil automáticamente al registrarse
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.users (id, name, email)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1)),
        NEW.email
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Función: actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER set_conversations_updated_at
    BEFORE UPDATE ON public.conversations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER set_nodes_updated_at
    BEFORE UPDATE ON public.nodes
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ══════════════════════════════════════════════════════════════
-- DATOS INICIALES: Proyectos por defecto ALTEN
-- ══════════════════════════════════════════════════════════════
-- NOTA: Ejecutar después de crear el primer usuario admin
-- INSERT INTO public.projects (name, emoji, color, created_by) VALUES
--     ('DevOps & Cloud',    '☁️',  '#4f8ef7', '<admin-uuid>'),
--     ('Data & Analytics',  '📊',  '#a855f7', '<admin-uuid>'),
--     ('Regulatory & GxP',  '🏥',  '#22c55e', '<admin-uuid>'),
--     ('Ingeniería',        '⚙️',  '#f59e0b', '<admin-uuid>'),
--     ('General',           '💬',  '#6b7280', '<admin-uuid>');
