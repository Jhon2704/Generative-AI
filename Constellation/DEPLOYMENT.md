# CONSTELLATION — Guía de Despliegue

## 1. Configuración local

### Prerrequisitos
- Python 3.11+
- Node.js 18+ (requerido por Reflex para el frontend)
- Cuenta en Supabase (gratuita)
- API key de Anthropic
- Ollama (opcional, para modelos open source)

### Instalación

```bash
# Clonar/entrar al proyecto
cd constellation

# Crear entorno virtual
python -m venv .venv

# Activar (Linux/Mac)
source .venv/bin/activate

# Activar (Windows)
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales reales
```

### Base de datos Supabase

1. Crear un proyecto en https://supabase.com
2. Ir a **SQL Editor** en el dashboard
3. Ejecutar el contenido de `supabase/schema.sql`
4. Copiar las credenciales en `.env`:
   - `SUPABASE_URL` → Project Settings → API → Project URL
   - `SUPABASE_ANON_KEY` → Project Settings → API → anon public key

### Ollama (opcional)

```bash
# Instalar Ollama desde https://ollama.ai

# Iniciar el servidor
ollama serve

# Descargar modelos
ollama pull mistral
ollama pull llama3
```

### Ejecutar en desarrollo

```bash
reflex run
```

La aplicación estará disponible en: http://localhost:3000

---

## 2. Deploy en Reflex Cloud

### Prerequisito: CLI de Reflex Cloud

```bash
pip install reflex-hosting-cli
reflex login
```

### Desplegar

```bash
# Desde la raíz del proyecto
reflex deploy

# Con nombre personalizado
reflex deploy --app-name constellation-alten
```

### Variables de entorno en Reflex Cloud

En el dashboard de Reflex Cloud → tu app → **Environment Variables**:

```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
OLLAMA_BASE_URL=http://localhost:11434  # No disponible en cloud sin VPN
```

**Nota**: Ollama no funciona en Reflex Cloud sin un servidor dedicado.
En producción cloud, solo estarán disponibles los modelos Claude.

---

## 3. Deploy en Railway

Railway ofrece más control sobre el entorno Docker.

### Dockerfile (crear en raíz)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN reflex init

EXPOSE 3000 8000

CMD ["reflex", "run", "--env", "prod"]
```

### Pasos en Railway

1. Conectar repositorio GitHub en https://railway.app
2. Variables de entorno: añadir las mismas que en Reflex Cloud
3. Railway detecta el Dockerfile y hace el build automáticamente
4. Dominio personalizado: Settings → Domains

---

## 4. Estructura del proyecto

```
constellation/
├── constellation/           ← App Reflex principal
│   ├── pages/
│   │   ├── index.py        ← Página principal (chat + grafo)
│   │   └── auth.py         ← Login y registro
│   ├── components/
│   │   ├── graph.py        ← Grafo canvas interactivo
│   │   ├── chat.py         ← Componente chat con streaming
│   │   ├── sidebar.py      ← Lista de conversaciones
│   │   ├── node_panel.py   ← Panel detalle de nodo
│   │   └── intro.py        ← Pantalla nueva conversación
│   ├── state/
│   │   ├── app_state.py    ← Estado global + chat
│   │   ├── auth_state.py   ← Autenticación
│   │   └── graph_state.py  ← Estado del grafo
│   ├── services/
│   │   ├── ai_service.py   ← Claude + Ollama unificados
│   │   ├── supabase_service.py ← Cliente Supabase
│   │   └── meta_extractor.py   ← Extracción de metadatos IA
│   ├── utils/
│   │   └── similarity.py   ← Similitud Jaccard
│   └── constellation.py    ← Punto de entrada, rutas
├── supabase/
│   └── schema.sql          ← Schema completo con RLS
├── rxconfig.py             ← Configuración Reflex
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 5. Primer uso

1. Acceder a `/auth` → crear cuenta con email corporativo
2. El trigger de Supabase crea automáticamente el perfil en `public.users`
3. Crear proyectos desde el panel admin (icono carpeta en el rail)
4. Iniciar primera conversación → el grafo generará el primer nodo
5. Los metadatos (título, tags, resumen) se extraen automáticamente en ~5 segundos

---

## 6. Troubleshooting

### Error: "SUPABASE_URL no está configurada"
→ Verifica que el archivo `.env` existe y tiene las variables correctas.
→ El `.env` debe estar en la raíz del proyecto (donde está `rxconfig.py`).

### El grafo no muestra nodos
→ Verifica que ejecutaste el schema SQL en Supabase.
→ Comprueba que el RLS está configurado correctamente.
→ Los nodos solo aparecen después de al menos un intercambio de mensajes.

### Ollama no detectado
→ Asegúrate de que `ollama serve` está corriendo.
→ Por defecto busca en `http://localhost:11434`. Cambia `OLLAMA_BASE_URL` si es diferente.
→ Si no hay Ollama, solo aparecen los modelos Claude en el selector.

### Streaming no funciona
→ Verifica que `ANTHROPIC_API_KEY` es válida.
→ En desarrollo, comprueba los logs de `reflex run`.
