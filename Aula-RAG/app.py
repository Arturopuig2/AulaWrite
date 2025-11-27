# app.py
import os, sqlite3, numpy as np
import gradio as gr
import re
import unicodedata
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import time
import pandas as pd
import glob



USE_GRADIO=False #Esto es para activar Gradio (la versión web del RAG)


# --- al principio del archivo ---

DB = "db.sqlite"
VECS = "vecs/all_emb.npy"

DF_DOCS = None        # cache global
VECS_M = None         # cache global (numpy array)

def init_index():
    global DF_DOCS, VECS_M
    if VECS_M is None:
        VECS_M = np.load(VECS)              # <-- carga una vez
    if DF_DOCS is None:
        con = sqlite3.connect(DB)
        DF_DOCS = pd.read_sql_query("SELECT * FROM docs ORDER BY id", con)
        con.close()

init_index()  # <-- llama una sola vez al arrancar

load_dotenv()
DB = "db.sqlite"
VECS = "vecs/all_emb.npy"
client = OpenAI()


def run_rag(question: str) -> tuple[str,str | None]:
    
    """
    Punto de entrada 'simple' para la API.
    
    Recibe una pregunta en texto y devuelve solo la respuesta del modelo,
    sin tocar nada de Gradio.
    
    Devuelve (respuesta, video_url_relativa) donde video_url_relativa
    es algo como '/videos/archivo.mp4' o None si no hay vídeo.
    
    """
    # Asegura que el índice y las tablas están listos
    init_index()
    ensure_tables()

    # Usuario genérico para las llamadas de la app (puedes cambiar nombre/edad/curso)
    try:
        uid = ensure_user("Alumno API", 10, "4º")
    except Exception:
        uid = None

    # Inferimos tema a partir del texto
    tema_detectado = infer_topic_from_text(question)  # puede ser None
    tema_norm = normalize_topic_for_video(tema_detectado or "")

    # Generamos la respuesta igual que en on_duda
    resp = generar_respuesta(q=question, intent="duda", topic=tema_norm)

    # Registramos la interacción si hay usuario
    try:
        if uid is not None:
            registrar_interaccion(uid, question, resp, "duda", tema_norm or "", None)
    except Exception as e:
        print("[registrar_interaccion] WARN en run_rag:", e)

    # Buscar vídeo igual que en on_duda
    vid_path = find_local_video(tema_norm, question)
    video_url = None
    if vid_path is not None:
        # Solo el nombre del archivo, la ruta la sirve FastAPI en /videos
        filename = os.path.basename(vid_path)
        video_url = f"/videos/{filename}"

    try:
        if uid is not None:
            registrar_interaccion(uid, question, resp, "duda", tema_norm or "", None)
    except Exception as e:
        print("[registrar_interaccion] WARN en run_rag:", e)

    return resp, video_url
    


# ============ Utilidades de datos ============

def ensure_tables():
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, age INTEGER, grade TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS interactions(
        id INTEGER PRIMARY KEY, user_id INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        prompt TEXT, response TEXT, intent TEXT, topic TEXT, difficulty INTEGER, solved INTEGER)""")
    con.commit(); con.close()

def ensure_user(username, age, grade):
    ensure_tables()
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    row=cur.fetchone()
    if row: uid=row[0]
    else:
        cur.execute("INSERT INTO users(username,age,grade) VALUES(?,?,?)", (username,age,grade))
        con.commit(); uid=cur.lastrowid
    con.close()
    return uid

def get_topics():
    """Lee temas distintos desde docs.topic para llenar el desplegable."""
    con=sqlite3.connect(DB)
    try:
        cur=con.cursor()
        rows = cur.execute("SELECT DISTINCT topic FROM docs WHERE topic IS NOT NULL AND topic!='' ORDER BY topic").fetchall()
        topics = [r[0] for r in rows] or ["sumas","restas","problemas","fracciones"]
        return topics
    finally:
        con.close()

def embed(q: str) -> np.ndarray:
    r = client.embeddings.create(model="text-embedding-3-small", input=q)
    return np.array(r.data[0].embedding, dtype=np.float32).reshape(1,-1)

def retrieve(q: str, k: int = 3, max_chars: int = 400) -> str:
    qv = embed(q)
    sims = cosine_similarity(qv, VECS_M)[0]    # usa VECS_M en memoria
    top = sims.argsort()[::-1][:k]

    ctx = []
    for i in top:
        row = DF_DOCS.iloc[i]                  # usa DF_DOCS en memoria
        snippet = (row['text'] or '')[:max_chars]
        ctx.append(f"[{row['kind']} | {row['title']} | {row['topic']} | {row['grade']}]\n{snippet}")
    return "\n\n---\n\n".join(ctx)

SYSTEM_STYLE = (
    "Eres una profesora de matemáticas para alumnado de educación primaria."
    "Da respuestas muy breves: no más de 60 palabras"
    "Los alumnos y alumnas tienen una edad entre 6 y 12 años."
    "Todas las respuestas deben estar conforme al sistema educativo español: LOMLOE"
    "Explica de forma clara y amable, sin usar emoticonos ni expresiones exageradas."
    "Usa ejemplos sencillos y frases cortas. "
    "Sé directo, ve al grano"
    "Si el alumno o alumna pide ejercicios, propón 2 ejercicios con pasos y añade soluciones al final."
    "Si el alumno o alumna pide ejemplos, muestra 2 ejercicios resueltos, paso a paso, y añade solución."
    "No uses 'restablecer', 'reiniciar' ni sinónimos para referirte a una resta; usa 'restar'. "
    #"Cuando muestres una operación, usa formato de bloque de texto (```text ... ```)"
    "Cuando muestres operaciones matemáticas (como sumas o restas), escríbelas en formato vertical y completo, los números alineados a las unidades, incluyendo el resultado al final del bloque." 
    #Por ejemplo, usa este formato dentro de un bloque de texto:\n```text\n  27\n+ 46\n-----\n  73\n```\n"
)

def generar_respuesta(q: str, intent: str, topic: str):
    contexto = retrieve(q, k=3, max_chars=400)
    prompt = f"""{SYSTEM_STYLE}

Tema: {topic or 'general'} | Intención: {intent}
Pregunta: {q}

Contexto (úsalo solo si ayuda):
{contexto}

Responde claro y breve, con pasos numerados si hace falta.
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=450,           # <-- limita longitud de salida
        messages=[
            {"role":"system","content":"Eres un profesor de Primaria, claro y sin emoticonos."},
            {"role":"user","content": prompt}
        ]
    ).choices[0].message.content
    resp = limpiar_texto_respuesta(resp)
    return resp

def registrar_interaccion(user_id, q, resp, intent, topic, difficulty):
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute("INSERT INTO interactions(user_id,prompt,response,intent,topic,difficulty) VALUES(?,?,?,?,?,?)",
                (user_id, q, resp, intent, topic, difficulty))
    con.commit(); con.close()

# --- Correcciones automáticas de texto del modelo ---

def _preserva_mayus(reemplazo: str, original: str) -> str:
    """Conserva la capitalización inicial si el original empieza en mayúscula."""
    return reemplazo.capitalize() if original and original[0].isupper() else reemplazo

def limpiar_texto_respuesta(texto: str) -> str:
    if texto is None:
        return texto

    texto = unicodedata.normalize("NFC", texto)

    # ==============================
    # 1️⃣ Corrige "sumas/restas con llamadas"
    # ==============================
    def _rep_suma_resta(m: re.Match) -> str:
        op = m.group("op")
        base = op.lower()
        out = {
            "suma": "suma llevando",
            "sumas": "sumas llevando",
            "resta": "resta llevando",
            "restas": "restas llevando"
        }.get(base, op)
        return _preserva_mayus(out, op)

    patron_suma_resta = re.compile(
        r"\b(?P<op>suma|sumas|resta|restas)\s+con\s+(?:llamada|llamadas|llamado|llamados|llevada|llevadas)\b",
        flags=re.IGNORECASE
    )
    texto = patron_suma_resta.sub(_rep_suma_resta, texto)

    # ==============================
    # 2️⃣ Corrige “reiniciar”, “quitar”, “eliminar”, “retirar” → “restar” en contexto numérico
    # ==============================
    patron_restar = re.compile(
        r"\b(?P<verbo>reiniciar|reinicias|reiniciamos|reinician|"
        r"quitar|quitas|quitamos|quitan|"
        r"eliminar|eliminas|eliminamos|eliminan|"
        r"retirar|retiras|retiramos|retiran)\b"
        r"([^.\n]{0,20}\d+[^.\n]{0,20})?",  # busca si hay número cerca
        flags=re.IGNORECASE
    )

    def _reemplazo_restar(m: re.Match) -> str:
        verbo = m.group("verbo")
        return _preserva_mayus("restar", verbo)

    texto = patron_restar.sub(_reemplazo_restar, texto)

    # ==============================
    # 3️⃣ Limpieza de espacios
    # ==============================
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    texto = re.sub(r"[ \t]+\n", "\n", texto)

    return texto

# --- Importación de vídeos ---

APP_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(APP_DIR, "assets", "videos")
VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v")

# ============ Callbacks ============

def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def _keywords(s: str) -> set[str]:
    s = _norm(s)
    # tokens simples alfanuméricos
    return set(re.findall(r"[a-z0-9]+", s))

def normalize_topic_for_video(tema: str) -> str:
    t = _norm(tema)
    if t in {"resta", "restas"}: return "resta"
    if t in {"suma", "sumas","adicion"}: return "suma"
    if t in {"suma llevando", "suma con llevada", "sumas llevando"}: return "suma llevando" 
    if t in {"resta llevando", "resta con llevada", "resta con llevadas","resta con prestamo", "restas con prestamos"}: return "resta llevando"        
    if t in {"multiplicacion", "multiplicaciones", "producto"}: return "multiplicacion"
    if t in {"division", "divisiones", "cociente"}: return "division"
    if t in {"problema", "problemas"}: return "problemas"
    return t

def find_local_video(topic: str | None, pregunta: str | None = None) -> str | None:
    """Elige el mejor vídeo de assets/videos por puntuación."""
    if not topic:
        print("[VIDEO] topic vacío")
        return None
    if not os.path.isdir(VIDEO_DIR):
        print(f"[VIDEO] No existe carpeta: {VIDEO_DIR}")
        return None

    t = normalize_topic_for_video(topic)     # ej. “restas”→“resta”
    t_norm = _norm(t)
    q_keys = _keywords(pregunta or "")

    try:
        files = [f for f in os.listdir(VIDEO_DIR)
                 if os.path.isfile(os.path.join(VIDEO_DIR, f))]
    except Exception as e:
        print("[VIDEO] No se pudo listar carpeta:", e)
        return None

    candidates = []
    for f in files:
        path = os.path.join(VIDEO_DIR, f)
        name_no_ext, ext = os.path.splitext(f)
        if ext.lower() not in VIDEO_EXTS:
            continue
        name_norm = _norm(name_no_ext)

        # --- scoring ---
        score = 0
        # 1) Contiene el tema normalizado
        if t_norm and t_norm in name_norm:
            score += 5
        # 2) Coincidencias con palabras clave de la pregunta
        for kw in q_keys:
            if kw and kw in name_norm:
                score += 1
        # 3) Bonus por coincidencias fuertes muy comunes
        if any(x in name_norm for x in ["llevando", "acarreo"]) and t_norm == "suma":
            score += 2
        # 4) desempate: más reciente primero
        mtime = os.path.getmtime(path)

        candidates.append((score, mtime, path))

    if not candidates:
        print(f"[VIDEO] No hay match para topic='{t_norm}'. Archivos:", files)
        return None

    # Ordena por score DESC, luego mtime DESC
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best = candidates[0]
    print(f"[VIDEO] elegido score={best[0]}, mtime={time.ctime(best[1])}, path={best[2]}")
    return best[2]

def infer_topic_from_text(text: str) -> str | None:
    t = _norm(text)
    if any(k in t for k in ["suma", "sumar", "llevando", "acarreo", "llevar"]): return "sumas"
    if any(k in t for k in ["resta", "restar"]): return "restas"
    if any(k in t for k in ["multiplica", "producto", " por "]): return "multiplicaciones"
    if any(k in t for k in ["divide", "division", "cociente"]): return "divisiones"
    if any(k in t for k in ["problema", "enunciado"]): return "problemas"
    return None

def on_duda(nombre, edad, curso, tema, pregunta):
    # Normaliza datos del alumno
    nombre = (nombre or "").strip() or "Alumno/a"
    uid = ensure_user(nombre, int(edad or 9), curso or "3º")

    # Determina el texto de la duda
    q = pregunta or f"Explícame {tema or ''}"

    tema_eff = (infer_topic_from_text(pregunta) or tema or "").strip()

    # Normaliza el tema para buscar vídeo (por ejemplo "restas" → "resta")
    tema_eff = normalize_topic_for_video(tema_eff or "")
    

    # Genera la respuesta
    resp = generar_respuesta(q=q, intent="duda", topic=tema_eff)
    registrar_interaccion(uid, q, resp, "duda", tema_eff or "", None)

    # 👇 ahora se pasa también la pregunta, para mejorar el score
    vid = find_local_video(tema_eff, pregunta)
    print(f"[DEBUG] tema='{tema_eff}' video='{vid}'")
    # ...

    if vid:
        # Mostrar el vídeo debajo de la respuesta
        return resp, gr.update(value=vid, visible=True)
    else:
        # Ocultar el componente si no hay vídeo
        return resp, gr.update(value=None, visible=False)

def on_ejercicios(nombre, edad, curso, tema, dificultad):
    # Normaliza entradas
    nombre = (nombre or "").strip() or "Alumno/a"
    curso = (curso or "3º").strip()
    edad = int(edad or 9)
    tema = (tema or "sumas llevando").strip()
    try:
        dificultad = int(dificultad or 2)
    except Exception:
        dificultad = 2

    # Guarda/crea usuario (si usas perfil)
    try:
        uid = ensure_user(nombre, edad, curso)
    except Exception as e:
        print("[ensure_user] ERROR:", e)

    #--- Prompt para ejercicios ---
    
    prompt = (
        f"Quiero ejercicios de {tema} de dificultad {dificultad}. "
        "Explícalos paso a paso y añade la solución al final. "
        "Usa bloque monoespaciado para las operaciones verticales (```text ... ```)."
    )

    try:
        resp = generar_respuesta(q=prompt, intent="ejercicios", topic=tema)
    except Exception as e:
        # Muestra el error al usuario y en consola
        print("[generar_respuesta] ERROR:", e)
        return (
            "⚠️ No he podido generar ejercicios ahora mismo.\n\n"
            f"**Detalle técnico:** `{e}`\n\n"
            "Prueba otra vez en unos segundos."
        )

    # Registro (si lo usas), no rompas la respuesta si falla
    try:
        registrar_interaccion(uid, prompt, resp, "ejercicios", tema, dificultad)
    except Exception as e:
        print("[registrar_interaccion] WARN:", e)

    return resp
   
def _clear_video():
    return gr.update(value=None, visible=False)

def _clear_duda_outputs():
    # Limpia texto y oculta/borra el vídeo
    return gr.update(value=""), gr.update(value=None, visible=False)
    
    
# ============ Tema y CSS ============
custom_css = """
:root {
  --brand: #2d7cff;
  --brand-2: #6aa7ff;
  --radius: 12px;
  --body-text-color: #111111 !important;   /* asegura texto oscuro por defecto */
}

/* Fuerza color oscuro en TODA la respuesta (dudas y ejercicios) */
#respuesta_duda,
#respuesta_ej,
#respuesta_duda *:not(code),
#respuesta_ej *:not(code),
#respuesta_duda .prose,
#respuesta_ej .prose,
#respuesta_duda .prose *:not(code),
#respuesta_ej .prose *:not(code),
#respuesta_duda .markdown-body,
#respuesta_ej .markdown-body,
#respuesta_duda .markdown-body *:not(code),
#respuesta_ej .markdown-body *:not(code) {
  color: #111111 !important;
  opacity: 1 !important; /* quita atenuados */
}

/* Títulos, negritas, cursivas, citas y listas */
#respuesta_duda h1, #respuesta_duda h2, #respuesta_duda h3,
#respuesta_duda h4, #respuesta_duda h5, #respuesta_duda h6,
#respuesta_ej h1, #respuesta_ej h2, #respuesta_ej h3,
#respuesta_ej h4, #respuesta_ej h5, #respuesta_ej h6,
#respuesta_duda strong, #respuesta_ej strong,
#respuesta_duda em, #respuesta_ej em,
#respuesta_duda blockquote, #respuesta_ej blockquote,
#respuesta_duda li, #respuesta_ej li,
#respuesta_duda a, #respuesta_ej a {
  color: #111111 !important;
  opacity: 1 !important;
}

/* Mantén estilo de bloques de operación (code/pre) con fondo claro */
#respuesta_duda pre, #respuesta_duda code,
#respuesta_ej pre, #respuesta_ej code {
  background: #f8f9fb !important;
  color: #111111 !important;
}

/* Quitar el botón de copiar (cuadrado negro con check) en bloques de código */
#respuesta_duda pre code button,
#respuesta_duda pre > button,
#respuesta_duda .copy-code,
#respuesta_ej pre code button,
#respuesta_ej pre > button,
#respuesta_ej .copy-code {
  display: none !important;
  visibility: hidden !important;
}

/* Fondo blanco global */
body, .gradio-container {
  background-color: #ffffff !important;
  color: #000000 !important;
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
}

/* Fondo blanco también en cada bloque o tarjeta */
.gr-block, .gr-panel, .gr-box, .gr-group, .gr-row, .gr-column {
  background-color: #ffffff !important;
}

/* Asegura que los tabs no tengan gris */
.gradio-container .tabitem, .gradio-container .tabbed-interface {
  background-color: #ffffff !important;
}

/* Elimina sombreado o degradado */
#header-card {
  background: white !important;
  color: #000000 !important;
  box-shadow: none !important;
  border: none !important;
}


.gradio-container {
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
}

/* Tarjeta de cabecera */
#header-card {
  border-radius: var(--radius);
  padding: 12px 16px;
  background: linear-gradient(90deg, var(--brand), var(--brand-2));
  color: white;
}
#header-card h1 { margin: 0; font-size: 1.2rem; }

/* Logo: escalado sin recortes y centrado */
#logo .image-container,
#logo .wrap,
#logo{
background: transparent !important;
  padding: 0 !important;
  margin: 0 auto !important;
  box-shadow: none !important;
}

#logo img, #logo {
  max-width: 180px;
  max-height: 50px;
  object-fit: contain;
  margin: auto;
  display: block;
  border-radius: 12px !important;
  margin-left: 0 !important;
  display: block !important;
  padding: 10 !import;
  margin-bottom:30px !important;
}

/* Ocultar el footer y enlaces de Gradio */
footer, #footer, .gradio-container footer, .svelte-drum1k {
    display: none !important;
    visibility: hidden !important;
}

/* Alinear logo y título arriba */
#fila_header, #col_logo, #col_titulo {
  display: flex !important;
  align-items: flex-start !important;  /* alinear arriba */
}

/* Mantener separación agradable entre logo y texto */
#col_logo {
  justify-content: flex-start !important;
  margin-top: 12px; /* ajusta según altura del logo */
  padding-left: 0 !important;
  marging-left: 0 !important; 
}

/* Ocultar toda la columna del título */
#col_titulo {
  display: none !important;
}

/* Ajustar el título y subtítulo para compactar */
#header-card h1 {
  margin: 0 !important;
  line-height: 1.1 !important;
}

#header-card div {
  margin-top: 2px !important;
  font-size: 1rem;
  font-weight: 400;
  color: #333;
}


/* Ocultar iconos de fullscreen y descarga si alguna versión los ignora por props */
button[aria-label="Download"], button[aria-label="Fullscreen"] {
  display: none !important;
}

/* Forzar tamaño grande en las respuestas del RAG */
#respuesta_duda, #respuesta_ej {
  font-size: 1.75rem !important;
  line-height: 1.6 !important;
  color: #000000 !important;   /* ← texto negro */
}

/* Asegura que parrafos/listas dentro también crezcan */
#respuesta_duda p, #respuesta_duda li,
#respuesta_ej p,   #respuesta_ej li {
  font-size: 1.75rem !important;
  line-height: 1.6 !important;
  color: #000000 !important;   /* ← texto negro */  
}

/* Cobertura extra para distintas versiones de Gradio */
#respuesta_duda .prose, #respuesta_ej .prose,
#respuesta_duda .gr-prose, #respuesta_ej .gr-prose,
#respuesta_duda .markdown-body, #respuesta_ej .markdown-body {
  font-size: 1.35rem !important;
  line-height: 1.6 !important;
    color: #000000 !important;   /* ← texto negro */
}

/* Caja de operaciones matemáticas con resultado alineado */.gr-markdown pre,
.gr-markdown pre,
.gr-markdown code,
#respuesta_duda pre, #respuesta_duda code,
#respuesta_ej pre,   #respuesta_ej code {
    font-size: 1.75rem !important;     /* tamaño grande para operaciones */
    line-height: 1.4 !important;
    font-family: "Courier New", "Lucida Console", monospace !important;
    background: #f9fafc !important;   /* fondo claro tipo papel */
    color: #000 !important;
    padding: 14px 20px !important;
    border-radius: 12px !important;
    box-shadow: 0 3px 10px rgba(0,0,0,0.08);
    display: block !important;
    text-align: right !important;
    white-space: pre !important;         /* respeta espacios y saltos */
    width:fit-content !important;
    margin: 0 auto !important;
}


/* Elimina completamente el botón flotante de copiar código de Gradio */
button.copy-code,
.copy-code,
.copy-btn,
.copy-button,
.absolute.top-2.right-2,
.absolute.top-1.right-1,
button[aria-label="Copy code"],
button[aria-label="Copiar código"],
button[title="Copy"],
button[title="Copiar"] {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

/* También oculta cualquier contenedor flotante residual */
div[class*="copy"],
div[aria-label*="Copy"],
div[title*="Copy"],
div[aria-label*="Copiar"] {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
}

/* Limpieza general: elimina cualquier bloque negro o sombra lateral en el área derecha */
#respuesta_duda::after,
#respuesta_ej::after {
  content: none !important;
  display: none !important;
}

.gr-markdown button.copy-code, .gr-markdown .copy-code {
  display: none !important;
  visibility: hidden !important;
}

/* AUMENTAR EL TAMAÑO GLOBAL DE LA INTERFAZ */
.gradio-container, body {
  font-size: 1.4rem !important;    /* aumenta tamaño base de todo el texto */
}

label, .gr-text-input label, .gr-dropdown label, .gr-number label {
  font-size: 1.4rem !important;    /* etiquetas */
  font-weight: 600 !important;
}

input, select, textarea {
  font-size: 1.4rem !important;    /* campos de texto y desplegables */
}

button {
  font-size: 1.2rem !important;   /* botones */
}

h1, h2, h3, .gr-markdown h1, .gr-markdown h2, .gr-markdown h3 {
  font-size: 1.5rem !important;
}

footer {display:none}
"""

theme = gr.themes.Soft(primary_hue="blue", radius_size=gr.themes.sizes.radius_md)


# ============ Construcción de la interfaz ============

#DESACTIVO TODO GRADIO PORQUE VOY A HACERLO DENTRO DE LA APP

if USE_GRADIO:

    with gr.Blocks(title="AULA Mates – RAG", css=custom_css, theme=theme) as demo:
        demo.queue()  # 👈 necesario para spinner/progreso
        # Header con logo y título
            
        with gr.Row(equal_height=True, elem_id="fila_header"):
            with gr.Column(scale=1, elem_id="col_logo"):
                logo = gr.Image(
                    value="assets/logo.png" if os.path.exists("assets/logo.png") else None,
                    label="", show_label=False, interactive=False, elem_id="logo",
                    height=60,  # controla altura (también puedes usar width)
                    show_download_button=False,      # <-- quitar descargar
                    show_fullscreen_button=False     # <-- quitar ampliar
                )
                
            with gr.Column(scale=11, elem_id="col_titulo"):
                gr.HTML('<div id="header-card"><h1>AULA de Matemáticas — Tutor RAG</h1><div>Primaria (6–12 años)</div></div>')
                
                
        with gr.Row():
            with gr.Column(scale=12):
                with gr.Tabs():
                    # ---------------------- DUDAS ----------------------
                    with gr.Tab("Dudas"):
                        pregunta = gr.Textbox(label="Escribe tu duda", lines=3,
                                            placeholder="Ej.: Explícame cómo sumar llevando")
                        # Se usarán los datos de la pestaña Perfil
                        btn_duda = gr.Button("Preguntar", variant="primary")
                            # 👇 Spinner propio, inicialmente oculto
                        spinner_duda = gr.HTML(
                            "<div id='spin-duda' style='display:none'>🌀 Pensando...</div>"
                        )
                        out_duda = gr.Markdown(elem_id="respuesta_duda")
                        out_duda_video = gr.Video(label=None, visible=False, show_label=False)
                        
                    # ------------------- EJERCICIOS --------------------
                    with gr.Tab("Ejercicios"):
                        topics = get_topics() or []

                        # Temas mínimos que siempre quieres mostrar
                        DEFAULT_TOPICS = ["Sumas", "Restas", "Multiplicaciones", "Divisiones", "Problemas verbales"]

                        # Mezcla: primero los mínimos (en este orden), luego lo que venga de BD, sin duplicar
                        def unique(seq):
                            seen = set()
                            out = []
                            for x in seq:
                                key = x.strip().lower()
                                if key and key not in seen:
                                    seen.add(key)
                                    out.append(x.strip())
                            return out

                        topics_ui = unique(DEFAULT_TOPICS + topics)

                        tema_ej = gr.Dropdown(
                            choices=topics_ui,
                            label="Tema",
                            value="Sumas",        # valor por defecto
                            interactive=True
                        )
                        dificultad = gr.Slider(1, 5, value=2, step=1, label="Dificultad")
                        btn_ej = gr.Button("Generar ejercicios", variant="primary")
                            # 👇 Spinner propio, inicialmente oculto
                        spinner_ej = gr.HTML(
                            "<div id='spin-ej' style='display:none'>🌀 Pensando...</div>"
                        )
                        out_ej = gr.Markdown(elem_id="respuesta_ej")
                                    
                    # ------------------- EJERCICIOS INTERACTIVOS  --------------------

                    with gr.Tab("Interactivos"):
                        topics = get_topics()
                        tema_ej = gr.Dropdown(choices=topics, label="Tema",
                                            value=(topics[0] if topics else None))
                        #dificultad = gr.Slider(1, 5, value=2, step=1, label="Dificultad")
                        btn_interactivos = gr.Button("Generar interactivos", variant="primary")
                        #out_ej = gr.Markdown(elem_id="respuesta_ej")

                    # ---------------------- PERFIL ---------------------
                    with gr.Tab("Perfil"):
                        gr.Markdown("Configura tu perfil de alumno.")
                        nombre = gr.Textbox(label="Nombre", placeholder="María")
                        edad = gr.Number(label="Edad", value=9, precision=0)
                        curso = gr.Textbox(label="Curso", value="4º")
                        #tema_pref = gr.Dropdown(choices=topics, label="Tema preferido",
                        #                       value=(topics[0] if topics else None))
                        gr.Markdown("> Guarda aquí tu información. Las otras pestañas usarán estos datos.")

                # Eventos (usan el estado de la pestaña Perfil)
                
                            # Paso 1: limpiar SIEMPRE salida y vídeo
                def _show_thinking():
                    return gr.update(value="🌀 Pensando...")

                btn_duda.click(
                    fn=_clear_duda_outputs,
                    inputs=[],
                    outputs=[out_duda, out_duda_video],
                    show_progress=False
                ).then(
                    fn=_show_thinking,
                    inputs=[],
                    outputs=out_duda,
                    show_progress=False
                ).then(
                    fn=lambda n,e,c,tp,p: on_duda(n,e,c,tp or "", p),
                    inputs=[nombre, edad, curso, pregunta],
                    outputs=[out_duda, out_duda_video],
                    show_progress=True
                )
                
                
                # Para ejercicios, usamos el tema elegido en su propia pestaña si existe
                def _ej_handler(n,e,c,tema_tab,dif):
                    tema_final = (tema_tab or "").strip()
                    return on_ejercicios(n,e,c,tema_final,dif)

                btn_ej.click(fn=_ej_handler,
                            inputs=[nombre, edad, curso, tema_ej, dificultad],
                            outputs=out_ej,
                            show_progress=True,   # 👈 activa el spinner nativo                         
                )


    if __name__ == "__main__":
        ensure_tables()
      #  demo.queue()
      #  APP_DIR = os.path.dirname(os.path.abspath(__file__))
      #  demo.launch(allowed_paths=["assets", os.path.join(APP_DIR, "assets")])

#FIN INTERFAZ
