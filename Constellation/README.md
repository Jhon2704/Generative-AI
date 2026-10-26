# CONSTELLATION

Aplicación web que convierte las conversaciones con IA en **conocimiento navegable**. Cada conversación genera un nodo en un *knowledge graph* visual (título, resumen, etiquetas y descripción semántica extraídos por IA), y los nodos se conectan entre sí por similitud de contenido o por pertenecer al mismo proyecto.

## Qué hace

- **Chat con IA** con respuestas en streaming. Soporta Claude (Anthropic) y modelos locales vía Ollama (`mistral`, `llama3`).
- **Proyectos con memoria**: las conversaciones de un mismo proyecto comparten contexto (resúmenes y tags de conversaciones anteriores se inyectan en el prompt).
- **Knowledge graph interactivo**: canvas con simulación *force-directed*, zoom, pan, drag & drop, filtros (todos / míos / públicos / proyecto) y doble clic para abrir la conversación.
- **Workspaces compartidos**: invita a otros usuarios con un código y comparte conversaciones, proyectos y nodos.
- **Archivos adjuntos**: extrae texto de PDF y Word (`.docx`) para usarlo en el chat.
- **Autenticación** con Supabase Auth.

## Stack

| Capa | Tecnología |
|---|---|
| Frontend + backend | [Reflex](https://reflex.dev) (Python) |
| Base de datos y auth | Supabase (Postgres + RLS) |
| IA cloud | Anthropic Claude |
| IA local (opcional) | Ollama |
| Grafo | Canvas HTML5 + JavaScript embebido |

## Estructura

```text
constellation/
  constellation.py      Punto de entrada y rutas
  pages/                Pantallas (principal y login)
  components/           Chat, grafo, sidebar, panel de nodo, intro
  state/                Estado de auth, app (chat) y grafo
  services/             Supabase, IA, extracción de metadatos y de archivos
  utils/similarity.py   Cálculo de conexiones entre nodos
supabase/schema.sql     Esquema de base de datos
workspace_migration.sql Migración para workspaces
```

## Cómo ponerlo en marcha

### 1. Requisitos

- Python 3.12
- Una cuenta de [Supabase](https://supabase.com) (gratuita)
- Una API key de [Anthropic](https://console.anthropic.com/)
- (Opcional) [Ollama](https://ollama.com) para modelos locales

### 2. Instalar dependencias

```bash
cd Constellation
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Preparar Supabase

1. Crea un proyecto en Supabase.
2. En el **SQL Editor**, ejecuta `supabase/schema.sql` y después `workspace_migration.sql`.
3. En *Project Settings → API* copia la URL, la `anon key` y la `service_role key`.

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Rellena `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
OLLAMA_BASE_URL=http://localhost:11434   # opcional
```

> Nunca subas el `.env` al repositorio. `SUPABASE_SERVICE_KEY` solo debe vivir en el backend.

### 5. (Opcional) Modelos locales con Ollama

```bash
ollama serve
ollama pull mistral
ollama pull llama3
```

Si Ollama responde, sus modelos aparecen automáticamente en el selector del chat.

### 6. Arrancar la aplicación

```bash
reflex run
```

Abre http://localhost:3000, regístrate y empieza a conversar. Cada conversación nueva aparecerá como un nodo en el grafo.

### Con Docker

```bash
docker build -t constellation .
docker run -p 8000:8000 --env-file .env constellation
```

La app queda en http://localhost:8000 (modo `--single-port`).

## Más documentación

- [DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md): arquitectura, flujos internos y plan de escalabilidad.
- [DEPLOYMENT.md](DEPLOYMENT.md): despliegue general.
- [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md): despliegue en Azure App Service.
