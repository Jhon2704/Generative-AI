# LegalSearch Offline — Buscador legal con RAG 100 % local

**LegalSearch Offline** es una aplicación de escritorio para Windows que permite **hacer preguntas en lenguaje natural sobre documentos legales en PDF** (contratos, cláusulas, sentencias, normativa…) y obtener respuestas **fundamentadas en esos documentos, con cita de archivo y página**.

Todo funciona **sin conexión a internet**: los documentos, el índice vectorial y el modelo de lenguaje se ejecutan en el propio equipo, por lo que la información confidencial nunca sale de la máquina.

## ¿Qué hace?

- **Importa documentos**: añade PDFs sueltos o carpetas completas a la biblioteca de la aplicación.
- **Indexa el contenido**: extrae el texto de cada página, lo divide en fragmentos y genera *embeddings* locales que guarda en una base vectorial (ChromaDB).
- **Búsqueda semántica con respuesta generada (RAG)**: ante una pregunta, recupera los fragmentos más relevantes y un LLM local (vía **Ollama**) redacta la respuesta usando solo esa evidencia.
- **Resúmenes jurídicos**: genera un resumen breve y accionable sobre un tema a partir de los documentos indexados.
- **Fuentes trazables**: cada respuesta muestra de qué archivo y página proviene la información.
- **Gestión de documentos**: listado y borrado de PDFs desde la propia interfaz.

## Cómo funciona

```text
PDFs ──► extracción de texto por página (pypdf)
     ──► fragmentación con solapamiento (chunks)
     ──► embeddings locales (Ollama)
     ──► índice vectorial persistente (ChromaDB)

Pregunta ──► embedding ──► top-k fragmentos similares
         ──► prompt con contexto ──► LLM local (Ollama) ──► respuesta + fuentes
```

- **Modelos**: `llama3.2` por defecto, con *fallback* automático a `phi3:mini`.
- **Backend vectorial**: ChromaDB; si no está disponible usa un almacén local en JSON.
- **Interfaz**: PySide6 (Qt), con las tareas pesadas en hilos de fondo para no bloquear la UI.

## Tecnologías

Python · PySide6 (Qt) · Ollama · ChromaDB · pypdf · PyInstaller · Inno Setup

## Estructura

```text
LegalSearch-Offline-RAG/
├── launcher_qt.py            # Punto de entrada de la app de escritorio
├── src/
│   ├── rag_core.py           # Motor RAG: indexado, embeddings, recuperación y generación
│   ├── ollama_client.py      # Comprobación/arranque de Ollama y llamadas al LLM
│   ├── document_manager.py   # Importación, listado y borrado de PDFs
│   ├── ui_layout.py          # Ventana principal (Qt)
│   ├── ui_adapter.py         # Puente UI ↔ backend con tareas asíncronas
│   ├── utils.py              # Configuración y rutas (%APPDATA%\LegalSearchOffline)
│   ├── logging_setup.py      # Logs de la aplicación
│   ├── build_index.py        # Reconstruir el índice por consola
│   └── chat_cli.py           # Chat por terminal con el mismo motor
├── data/                     # PDFs legales de ejemplo
├── resources/                # Icono de la aplicación
├── LegalSearchOfflineQt.spec # Configuración de PyInstaller
├── installer.iss             # Script del instalador (Inno Setup)
└── build_installer.py        # Automatiza el empaquetado
```

## Requisitos

- Windows 10/11 y Python 3.10+
- [Ollama](https://ollama.com) instalado y en ejecución, con los modelos:

```bash
ollama pull llama3.2
ollama pull phi3:mini
```

## Uso

```bash
pip install -r requirements.txt

# Aplicación de escritorio
python launcher_qt.py

# Alternativas por consola
python src/build_index.py   # construir el índice con los PDFs de data/
python src/chat_cli.py      # chat interactivo en terminal
```

En la app: **Documentos → Importar** PDFs, pulsa **Reconstruir índice** y después haz tus consultas en la pestaña de **Búsqueda**.

Los datos de usuario se guardan en `%APPDATA%\LegalSearchOffline\` (`documents/`, `chroma_db/`, `logs/`, `config.json`).

## Generar el ejecutable / instalador

```bash
pip install -r requirements-dev.txt
pyinstaller LegalSearchOfflineQt.spec      # genera dist/LegalSearchOfflineQt.exe
```

Después, compilar `installer.iss` con Inno Setup para obtener `LegalSearch_Offline_Setup.exe`.
