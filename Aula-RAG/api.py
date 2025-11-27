# api.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
from pydantic import BaseModel
from dotenv import load_dotenv
from app import run_rag, ensure_tables, init_index, VIDEO_DIR
from pydantic import BaseModel
from uuid import uuid4
from openai import OpenAI

APP_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(APP_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

 
# =========================
#  Carga de entorno e index
# =========================
load_dotenv()

# Inicializamos BD e índice RAG al arrancar
# Nos aseguramos de que todo está inicializado al arrancar el servidor
ensure_tables()
init_index()

# Cliente OpenAI (usa OPENAI_API_KEY del .env)
client = OpenAI()

# Carpeta donde guardaremos los archivos de audio
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)


#CREAR LA APP FASTAPI
#=====================#

app = FastAPI(title="AULA RAG API")

# Servir vídeos locales si los usas desde VIDEO_DIR

if os.path.isdir(VIDEO_DIR):
    app.mount("/videos",
          StaticFiles(directory=VIDEO_DIR),
          name="videos")



#FUNCIÓN PARA GENERAR EL ARCHIVO DE AUDIO
#========================================#

def generar_audio(texto: str) -> str | None:
    """
    Genera un MP3 con la respuesta usando OpenAI TTS.
    Devuelve SOLO el nombre del archivo (ej. 'abcd1234.mp3').
    """
    if not texto:
        return None

    filename = f"{uuid4().hex}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    print("[TTS] Guardando audio en:", filepath)

    try:
        # Modelo TTS de OpenAI (ajusta si usas otro)
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=texto,
        )
        # En el client nuevo: speech.read() devuelve los bytes
        with open(filepath, "wb") as f:
            f.write(speech.read())
        return filename
    except Exception as e:
        print("[TTS] Error generando audio:", e)
        return None




#ENTRADA Y SALIDA DEL RAG
class RAGQuery(BaseModel):
    question: str

class RAGAnswer(BaseModel):
    answer: str
    video_url: str | None = None
    audio_url: str | None = None


#ENDPOINT
#=========#

#ENDPOINT DE PRUEBA (GET) → PARA COMPROBAR API
@app.get("/")
def home():
    """
    Ruta de comprobación.
    Si vemos este mensaje en el navegador,
    significa que la API está funcionando.
    """
    return {"status": "AulaWrite API OK", "version": "1.0"}

#GET
@app.get("/audio/{filename}")
def get_audio(filename:str):
    """
    Devuelve un archivo de audio previamente generado.
    Ejemplo de URL: http://127.0.0.1:8000/audio/abcd1234.mp3
    """
    filepath = os.path.join(AUDIO_DIR, filename)
    print("[AUDIO] Sirviendo:", filepath)
    
    if not os.path.exists(filepath):
        print("[AUDIO] No existe el archivo:", filepath)
        raise HTTPException(status_code=404, detail="Audio not found")
    
    #    return {"error": "audio not found"}
    return FileResponse(filepath,media_type="audio/meg")


#ENDPOINT PRINCIPAL DEL RAG (POST)
@app.post("/ask", response_model=RAGAnswer)
async def ask_rag(q: RAGQuery):
    """
    Recibe una pregunta y devuelve:
      - answer: texto de la profesora
      - video_url: vídeo educativo local (si hay)
      - audio_url: URL del mp3 con la respuesta leída
    """
    # 1) Ejecutar el RAG en un hilo aparte
    answer, video_url = await asyncio.to_thread(run_rag, q.question)

    # 2) Generar el audio también en un hilo aparte
    audio_filename = await asyncio.to_thread(generar_audio, answer)

    # 3) Construir la URL del audio (completa o relativa)
    audio_url = None
    if audio_filename:
        # Si usas la API desde el simulador en el mismo Mac:
        # base_url = "http://127.0.0.1:8000"
        # audio_url = f"{base_url}/audio/{audio_filename}"
        audio_url = f"/audio/{audio_filename}"

    # 4) Respuesta final para AulaWrite
    return RAGAnswer(
        answer=answer,
        video_url=video_url,
        audio_url=audio_url
    )