# CONSTELLATION - Documentacion tecnica y plan de escalabilidad

## 1. Resumen del producto

CONSTELLATION es una aplicacion web construida con Reflex que combina chat con IA, organizacion por proyectos/workspaces y un knowledge graph visual. Cada conversacion puede generar un nodo en el grafo. Ese nodo contiene titulo, resumen, etiquetas y una descripcion semantica extraida por IA. Los nodos se conectan entre si por similitud o por pertenecer al mismo proyecto.

El objetivo del prototipo es demostrar una forma de trabajar con conversaciones de IA como conocimiento reutilizable, no como chats aislados. El usuario puede crear proyectos, mantener memoria entre conversaciones del mismo proyecto, invitar a otros usuarios a un workspace y visualizar el conocimiento compartido como una constelacion de nodos.

## 2. Stack principal

- Frontend y backend web: Reflex.
- Base de datos y autenticacion: Supabase.
- IA cloud: Anthropic Claude.
- IA local/opcional: Ollama, mediante API HTTP.
- Visualizacion del grafo: canvas HTML5 con JavaScript embebido en componente Reflex.
- Extraccion de metadatos: servicio Python que llama al modelo IA y guarda el resultado en Supabase.
- Workspaces: tablas propias `workspaces` y `workspace_members` sobre Supabase.

## 3. Estructura del proyecto

```text
constellation/
  constellation.py              Punto de entrada de Reflex y rutas.
  pages/
    index.py                    Layout principal: rail, sidebar, chat, grafo, paneles.
    auth.py                     Pantalla de login/registro.
  components/
    chat.py                     UI de chat y controles de modelo.
    graph.py                    Canvas del knowledge graph y JS de interaccion.
    sidebar.py                  Lista de conversaciones agrupadas por proyecto.
    node_panel.py               Detalle del nodo seleccionado.
    intro.py                    Pantalla para iniciar conversacion.
  state/
    auth_state.py               Login, sesion, workspaces, miembros e invitaciones.
    app_state.py                Conversaciones, mensajes, streaming y archivos.
    graph_state.py              Nodos, conexiones, proyectos y filtros del grafo.
  services/
    supabase_service.py         Acceso a Supabase y operaciones de persistencia.
    ai_service.py               Integracion Claude/Ollama.
    meta_extractor.py           Extraccion de titulo, resumen, tags y semantic.
    file_extractor.py           Lectura de texto desde archivos adjuntos.
  utils/
    similarity.py               Calculo de conexiones entre nodos.
supabase/
  schema.sql                    Esquema base.
workspace_migration.sql         Migracion para workspaces.
```

## 4. Flujo de arranque de la aplicacion

El punto de entrada esta en `constellation/constellation.py`.

La ruta principal `/` ejecuta tres handlers en orden:

```python
on_load=[AuthState.restore_session, AppState.on_load, GraphState.load_graph]
```

El flujo es:

1. `AuthState.restore_session` restaura la sesion con los tokens guardados.
2. Si la sesion es valida, carga el perfil del usuario.
3. Inicializa o recupera el workspace personal.
4. `AppState.on_load` carga conversaciones y modelos disponibles.
5. `GraphState.load_graph` carga nodos, proyectos y conexiones del workspace activo.

Si no hay sesion, `AuthState.restore_session` redirige a `/auth`.

## 5. Autenticacion y perfiles

La autenticacion se delega a Supabase Auth.

Archivos relevantes:

- `constellation/state/auth_state.py`
- `constellation/services/supabase_service.py`
- `supabase/schema.sql`

Cuando un usuario se registra:

1. `AuthState.register` valida nombre, email y password.
2. Llama a `sb.sign_up`.
3. Supabase crea el usuario en `auth.users`.
4. El trigger `handle_new_user` crea el perfil en `public.users`.
5. La app guarda `access_token` y `refresh_token` en el estado Reflex.
6. `_init_workspace` crea o recupera el workspace personal.

Cuando un usuario inicia sesion:

1. `AuthState.login` llama a `sb.sign_in`.
2. Se guardan tokens.
3. Se carga el perfil.
4. Se inicializa el workspace.

## 6. Workspaces e invitaciones

Los workspaces permiten compartir conversaciones, proyectos y nodos entre usuarios.

Tablas:

- `workspaces`: espacio de trabajo, owner e invite code.
- `workspace_members`: usuarios miembros del workspace y su rol.

Funciones clave:

- `get_or_create_personal_workspace`
- `get_user_workspaces`
- `join_workspace_by_code`
- `regenerate_invite_code`
- `get_workspace_members`
- `remove_workspace_member`

Flujo para invitar:

1. El owner abre el panel Workspace.
2. Ve el codigo de invitacion.
3. Otro usuario introduce ese codigo.
4. `join_workspace_by_code` inserta al usuario en `workspace_members`.
5. La app cambia al workspace unido y recarga conversaciones/grafo.

Gestion de miembros:

- El invitado puede dejar de ver un workspace desde "Mis workspaces".
- El owner puede quitar miembros desde la seccion "Miembros".
- El backend impide quitar al owner de su propio workspace.

## 7. Conversaciones y mensajes

El estado principal esta en `AppState`.

Responsabilidades:

- Mantener lista de conversaciones.
- Mantener mensajes de la conversacion activa.
- Gestionar streaming de respuestas.
- Crear una conversacion si el usuario envia el primer mensaje sin conversacion activa.
- Inyectar memoria de proyecto.
- Crear nodos del grafo tras el primer mensaje.

Flujo de envio de mensaje:

1. Usuario escribe en el chat.
2. `send_message` valida que haya texto y que no haya otro streaming activo.
3. Si no hay conversacion activa, llama a `start_conversation`.
4. Guarda el mensaje del usuario en Supabase.
5. Construye el historial para el modelo.
6. Si la conversacion pertenece a un proyecto, busca resumenes de otras conversaciones del mismo proyecto.
7. Genera un `system_prompt` con memoria de proyecto.
8. Llama a `ai_service.stream_chat`.
9. Muestra el streaming en pantalla.
10. Guarda la respuesta final del asistente.
11. Si es el primer mensaje de usuario, lanza `_create_node_bg` en background.

## 8. Memoria de proyecto

La memoria de proyecto evita que cada conversacion sea un silo.

Cuando el usuario habla dentro de una conversacion asociada a un proyecto:

1. `AppState.send_message` identifica el `project_id`.
2. Llama a `sb.get_project_summaries`.
3. Recupera titulos, resumenes y tags de conversaciones anteriores del mismo proyecto.
4. Inserta ese contexto en el prompt de sistema.

El resultado es que el modelo puede responder con conocimiento de conversaciones previas del mismo proyecto.

Limitacion actual:

- La memoria se basa en resumenes y tags, no en busqueda vectorial.
- Es suficiente para prototipo.
- Para escalar, conviene usar embeddings y recuperacion semantica.

## 9. Generacion de nodos del grafo

El grafo se alimenta desde la tabla `nodes`.

Flujo:

1. Tras el primer mensaje de usuario, `send_message` lanza `_create_node_bg`.
2. `_create_node_bg` crea un nodo pendiente con `sb.create_node`.
3. Junta la conversacion en texto con `format_conversation_for_extraction`.
4. Llama a `extract_metadata`.
5. La IA devuelve:
   - title
   - summary
   - tags
   - semantic
6. Se actualiza el nodo en Supabase.
7. Se calculan conexiones contra otros nodos.
8. Se persisten conexiones en `node_connections`.

Mientras el nodo esta pendiente, el grafo puede pintarlo como nodo provisional.

## 10. Knowledge graph

El estado del grafo vive en `GraphState`.

Responsabilidades:

- Cargar nodos del workspace activo.
- Cargar proyectos.
- Cargar o calcular conexiones.
- Filtrar nodos por:
  - todos
  - mios
  - publicos
  - proyecto
- Seleccionar nodo.
- Abrir conversacion con doble clic.
- Persistir posicion de nodos.

La UI del grafo esta en `components/graph.py`.

El grafo usa:

- Canvas HTML5.
- JavaScript inline.
- Simulacion force-directed simple:
  - repulsion entre nodos
  - atraccion por links
  - centrado suave
- Drag and drop de nodos.
- Zoom y pan.
- Seleccion por click.
- Navegacion por doble click.

Reflex no renderiza directamente el grafo nodo por nodo. Python genera un JSON con `graph_data_json`; JavaScript lee ese JSON y actualiza el canvas.

## 11. Conexiones entre nodos

Las conexiones estan en `node_connections`.

Origen:

- Misma pertenencia a proyecto.
- Similitud de contenido mediante utilidades de `utils/similarity.py`.

En el prototipo se usa una aproximacion ligera tipo Jaccard/similitud textual. Esto es razonable para demo, pero no es lo ideal para miles de conversaciones.

Para escalar:

- Generar embeddings por nodo.
- Guardarlos en Postgres con `pgvector`.
- Calcular vecinos cercanos por distancia vectorial.
- Recalcular conexiones en jobs asicronos, no dentro del request principal.

## 12. Servicio de IA

Archivo: `services/ai_service.py`.

El servicio unifica dos proveedores:

- Claude via Anthropic.
- Ollama via HTTP local/remoto.

Modelos cloud:

- `claude-sonnet-4-6`
- `claude-haiku-4-5-20251001`

Modelos Ollama:

- `mistral`
- `llama3`

La app detecta Ollama con:

```text
GET {OLLAMA_BASE_URL}/api/tags
```

Si responde OK, aparecen modelos locales en el selector.

Para usar Ollama en despliegue cloud:

- No usar `localhost` salvo que Ollama viva en el mismo contenedor.
- Recomendado: ejecutar Ollama como servicio separado.
- Configurar en la app:

```env
OLLAMA_BASE_URL=http://servicio-ollama:11434
```

Para prototipo online, Claude es mas simple. Ollama requiere VM/Container con suficiente RAM/GPU.

## 13. Supabase y seguridad

Supabase cubre:

- Auth.
- Base de datos.
- RLS.
- Persistencia de conversaciones, mensajes, proyectos, nodos y workspaces.

La app usa dos tipos de cliente:

- Cliente anon con token del usuario para operaciones normales.
- Cliente service role para operaciones admin controladas desde backend.

Variables:

```env
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
```

Advertencia:

- `SUPABASE_SERVICE_KEY` nunca debe exponerse en frontend.
- En este proyecto vive en backend Python y se configura como secreto de entorno.

RLS actual:

- Usuarios ven su perfil.
- Conversaciones privadas solo owner.
- Conversaciones publicas visibles.
- Nodos siguen privacidad de la conversacion.

Workspaces se han implementado con validaciones desde backend usando service role. Para una version empresarial, conviene reforzar tambien RLS a nivel SQL para workspace membership.

## 14. Despliegue online

### Opcion rapida: Reflex Cloud

Ventajas:

- Menos infraestructura.
- Despliegue directo de apps Reflex.
- Buen camino para demo.

Comando orientativo:

```powershell
reflex login
reflex deploy --envfile .env
```

### Opcion Azure: App Service con Docker

Recomendado para tener control y URL propia.

Puntos clave:

- Reflex normalmente usa frontend `3000` y backend `8000`.
- Para Azure App Service conviene usar `--single-port`.
- El contenedor debe exponer un solo puerto, por ejemplo `8000`.

Variables en Azure:

```env
WEBSITES_PORT=8000
ANTHROPIC_API_KEY=...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
OLLAMA_BASE_URL=...
```

Para prototipo, `OLLAMA_BASE_URL` puede omitirse y se usaran solo modelos Claude.

## 15. Como hacerlo escalable

### 15.1 Separar responsabilidades

Estado actual:

- Reflex ejecuta UI, backend, streaming, creacion de nodos y extraccion de metadatos.

Escalable:

- App web Reflex para UI y eventos interactivos.
- Worker separado para:
  - extraccion de metadatos
  - calculo de conexiones
  - embeddings
  - tareas pesadas de archivos
- Cola de trabajos:
  - Celery + Redis
  - RQ + Redis
  - Supabase Edge Functions + queue externa
  - Azure Service Bus

### 15.2 Cambiar similitud textual por embeddings

Estado actual:

- Similitud ligera en Python.

Escalable:

- Tabla `node_embeddings`.
- Extension `pgvector`.
- Embeddings por nodo.
- Busqueda top-k por distancia vectorial.
- Recalculo incremental.

Beneficio:

- Mejor precision.
- Menos coste en cada carga de grafo.
- Capacidad para miles de nodos.

### 15.3 Cachear lecturas frecuentes

Lecturas candidatas a cache:

- Proyectos por workspace.
- Lista de modelos disponibles.
- Resumenes de proyecto.
- JSON del grafo.

Opciones:

- Redis.
- Cache en memoria si solo hay una instancia.
- Materialized views en Postgres.

### 15.4 Hacer paginacion y lazy loading

El prototipo carga todas las conversaciones/nodos del workspace.

Para escalar:

- Paginacion en sidebar.
- Busqueda server-side.
- Grafo por ventanas:
  - cargar ultimos N nodos
  - cargar nodos relacionados al nodo seleccionado
  - filtros por proyecto antes de consultar

### 15.5 Endurecer permisos de workspace

Mejoras:

- RLS basada en `workspace_members`.
- Politicas SQL para que miembros accedan a recursos del workspace.
- Evitar depender tanto del service role.
- Auditoria:
  - quien invita
  - quien sale
  - quien elimina miembros
  - quien cambia privacidad

### 15.6 Observabilidad

Agregar:

- Logs estructurados.
- Trazas de requests lentos.
- Metricas:
  - tiempo de respuesta IA
  - coste por modelo
  - tokens por workspace
  - nodos generados
  - errores de Supabase
  - latencia del grafo

Herramientas:

- Azure Application Insights.
- Sentry.
- Logfire.
- OpenTelemetry.

### 15.7 Gestion de modelos

Para demo:

- Claude por API.
- Ollama opcional.

Para escalar:

- Router de modelos.
- Politicas por workspace:
  - modelos permitidos
  - limites de coste
  - limite de tokens
  - fallback si un proveedor falla
- Ejecucion de Ollama separada de la app.

Arquitectura con Ollama:

```text
Browser
  -> Constellation
      -> Claude API
      -> Ollama service privado
```

No exponer Ollama publicamente sin autenticacion.

## 16. Riesgos actuales del prototipo

- El estado de Reflex puede no ser ideal para tareas largas en background si hay muchas sesiones.
- La creacion de nodos usa `asyncio.create_task` dentro del proceso web.
- El calculo de conexiones puede crecer en coste con muchos nodos.
- El grafo completo no esta paginado.
- `SUPABASE_SERVICE_KEY` debe protegerse muy bien.
- La memoria de proyecto puede crecer demasiado si se meten muchos resumenes en el prompt.
- Ollama en cloud requiere recursos dedicados; no es gratuito ni trivial si se busca buen rendimiento.

## 17. Roadmap recomendado

### Fase 1 - Demo publica

- Desplegar en Reflex Cloud o Azure App Service.
- Usar Claude.
- Mantener Supabase.
- Añadir dominio propio.
- Añadir monitorizacion basica.

### Fase 2 - Robustez

- Worker para nodos/metadatos.
- Cola de trabajos.
- Reintentos en extraccion IA.
- Logs estructurados.
- RLS de workspaces mas estricta.

### Fase 3 - Escalabilidad de conocimiento

- Embeddings.
- `pgvector`.
- Busqueda semantica.
- Grafo incremental.
- Paginacion de conversaciones.

### Fase 4 - Multiempresa

- Roles:
  - owner
  - admin
  - member
  - viewer
- Auditoria.
- Limites por workspace.
- Configuracion de modelos por workspace.
- Exportacion/importacion de conocimiento.

## 18. Resumen ejecutivo

CONSTELLATION demuestra una idea potente: convertir conversaciones con IA en conocimiento navegable, compartible y conectado. El prototipo ya cubre autenticacion, workspaces, invitaciones, chat, memoria de proyecto, nodos, grafo interactivo y soporte para multiples proveedores de IA.

Para una demo online, el camino mas simple es desplegar la app con Claude y Supabase. Para una version escalable, el principal cambio arquitectonico es separar tareas pesadas en workers, usar embeddings para relacionar conocimiento y reforzar seguridad de workspace a nivel SQL.

