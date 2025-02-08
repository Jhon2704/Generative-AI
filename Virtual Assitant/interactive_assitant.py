#asistente interactivo by Juan Olivan , se usa el modelo de Ollama 3.2.
#librerias 
import ollama #modelo al que vamos hacer servicio de llm
import requests #descarga el contenido de una página web
from bs4 import BeautifulSoup #analiza y extrae información relevante del contenido HTML
from IPython.display import Markdown, display #presenta los datos de forma visual en un entorno interactivo como un Jupyter Notebook
#Modelo base para el asistente 
MODEL_LLAMA='llama3.2'
#Historial de mensajes para mantener contexto
def initialize_chat():
    return[
        {"role":"system","content":"Eres mi asistente interactivo. Responde a mis preguntas y proporciona explicaciones claras y precisas."}
    ]

#Función para interactuar con el modelo Ollama
def query_ollama(model,messages):
    response=ollama.chat(model=model,messages=messages)
    return response['message']['content']

#Función principal del asistente interactivo
def interactive_assistant():
    messages=initialize_chat()
    print("\nBienvenido a tu asistente , escriba 'salir' para terminar.\n")

    while True:
        #Obtener la entrada del usuario
        user_input=input("Tú: ")
        if user_input.lower() in ['salir','exit','quit']:
            print("\n¡Adiós! Gracias por usar tú asistente.")
            break
        #Agregar mensaje del usuario al historial
        messages.append({"role":"user","content":user_input})
        #Consultar el modelo Ollama
        try:
            reply = query_ollama(MODEL_LLAMA, messages)
            messages.append({"role": "assistant", "content": reply})

            # Mostrar respuesta en formato Markdown
            #display(Markdown(reply))
            print(reply)
        except Exception as e:
            print("\nOcurrió un error al consultar el modelo:", e)

#Ejecutar el asistente
if __name__ == "__main__":
    interactive_assistant()