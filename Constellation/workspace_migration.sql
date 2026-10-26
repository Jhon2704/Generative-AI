-- ═══════════════════════════════════════════════════════════════
-- CONSTELLATION — Migración de Workspaces
-- Ejecutar en Supabase → SQL Editor
-- ═══════════════════════════════════════════════════════════════

-- 1. Tabla de espacios de trabajo
CREATE TABLE IF NOT EXISTS workspaces (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT        NOT NULL DEFAULT 'Mi espacio',
  owner_id    UUID        NOT NULL,
  invite_code TEXT        UNIQUE NOT NULL DEFAULT upper(left(replace(gen_random_uuid()::text, '-', ''), 8)),
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- 2. Tabla de miembros del workspace
CREATE TABLE IF NOT EXISTS workspace_members (
  workspace_id UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id      UUID        NOT NULL,
  role         TEXT        NOT NULL DEFAULT 'member', -- 'owner' | 'member'
  joined_at    TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (workspace_id, user_id)
);

-- 3. Añadir workspace_id a conversaciones y proyectos
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE projects      ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id);

-- 4. Índices de rendimiento
CREATE INDEX IF NOT EXISTS idx_conv_workspace ON conversations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_proj_workspace ON projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_wm_user        ON workspace_members(user_id);
CREATE INDEX IF NOT EXISTS idx_wm_workspace   ON workspace_members(workspace_id);
