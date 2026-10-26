# Generative AI

Colección de proyectos de **Inteligencia Artificial Generativa** construidos con **Python** y **modelos de lenguaje (LLMs)**, tanto en la nube (Anthropic Claude) como ejecutados en local con **Ollama**.

Los proyectos recorren distintas formas de llevar los LLMs a aplicaciones reales: desde un asistente conversacional sencillo hasta sistemas **RAG** (*Retrieval-Augmented Generation*) sobre documentos privados y grafos de conocimiento generados a partir de conversaciones.

## Proyectos

| Proyecto | Descripción | Tecnologías |
|---|---|---|
| [**LegalSearch Offline RAG**](./LegalSearch-Offline-RAG) | Aplicación de escritorio para hacer preguntas sobre documentos legales en PDF y obtener respuestas con cita de archivo y página. Funciona **100 % sin internet**: la información confidencial no sale del equipo. Incluye instalador para Windows. | RAG · Ollama (Llama 3.2, Phi-3) · ChromaDB · PySide6 · PyInstaller |
| [**Constellation**](./Constellation) | Aplicación web que convierte las conversaciones con IA en un **knowledge graph** navegable: cada conversación es un nodo con resumen y etiquetas generados por IA, conectado a otros por similitud semántica. Soporta proyectos con memoria y workspaces compartidos. | Reflex · Anthropic Claude · Ollama · Supabase · Docker / Azure |
| [**Virtual Assistant**](./Virtual%20Assitant) | Asistente conversacional por terminal que se ejecuta en local y mantiene el contexto de la conversación. | Ollama (Llama 3.2) · Python |

## Temas que se trabajan

- **RAG**: extracción de texto, *chunking*, *embeddings* y búsqueda vectorial para que el LLM responda con evidencia de los documentos.
- **LLMs locales vs. cloud**: ejecución privada con Ollama y uso de APIs como Anthropic Claude.
- **Memoria y contexto**: historial de conversación, contexto compartido entre conversaciones de un mismo proyecto.
- **Extracción de metadatos con IA**: resúmenes, etiquetas y descripciones semánticas generadas automáticamente.
- **Del prototipo al producto**: interfaces de escritorio y web, autenticación, empaquetado en ejecutable y despliegue.

## Requisitos generales

- Python 3.10+
- [Ollama](https://ollama.com) para los proyectos que usan modelos locales
- Cada proyecto tiene su propio `README` / `requirements.txt` con las instrucciones específicas.

## Autor

**Juan Olivan** · [GitHub](https://github.com/Jhon2704) · [Web](https://jhon2704.github.io/juanolivan.github.io/)
