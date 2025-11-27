# app.py
import os, sqlite3, numpy as np
import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
load_dotenv()

DB="db.sqlite"
VECS="vecs/all_emb.npy"
client = OpenAI()

def ensure_user(username, age, grade):
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, age INTEGER, grade TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS interactions(
        id INTEGER PRIMARY KEY, user_id INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        prompt TEXT, response TEXT, intent TEXT, topic TEXT, difficulty INTEGER, solved INTEGER)""")
    con.commit()
    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    row=cur.fetchone()
    if row: uid=row[0]
    else:
        cur.execute("INSERT INTO users(username,age,grade) VALUES(?,?,?)", (username,age,grade))
        con.commit(); uid=cur.lastrowid
    con.close()
    return uid

def embed(q):
    r = client.embeddings.create(model="text-embedding-3-small", input=q)
    return np.array(r.data[0].embedding, dtype=np.float32).reshape(1,-1)

def retrieve(q, k=5):
    qv = embed(q)
    M = np.load(VECS)
    con=sqlite3.connect(DB)
    df = None
    try:
        import pandas as pd
        df = pd.read_sql_query("SELECT * FROM docs ORDER BY id", con)
    except:
        # fallback sin pandas
        cur = con.cursor()
        rows=cur.execute("SELECT id,kind,title,topic,grade,text FROM docs ORDER BY id").fetchall()
        import pandas as pd
        df=pd.DataFrame(rows, columns=["id","kind","title","topic","grade","text"])
    con.close()
    sims = cosine_similarity(qv, M)[0]
    top = sims.argsort()[::-1][:k]
    ctx = []
    for i in top:
        row = df.iloc[i]
        ctx.append(f"[{row['kind']} | {row['title']} | {row['topic']} | {row['grade']}]\n{row['text'][:800]}")
    return "\n\n---\n\n".join(ctx)

SYSTEM_STYLE = (
    "Eres un tutor de matemáticas para alumnado de 6–12 años. "
    "Explica con frases cortas, ejemplos sencillos y tono animado. "
    "Si el alumno pide ejercicios, proponlos con pasos, y luego ofrece soluciones al final."
)

def rag_answer(username, age, grade, pregunta, pedir_ejercicios):
    if not username:
        return "Escribe tu nombre para empezar."
    uid = ensure_user(username, int(age or 10), grade or "3º")

    intent = "ejercicios" if pedir_ejercicios else "duda"
    q = pregunta or ("Quiero ejercicios de sumas de una cifra" if pedir_ejercicios else "Explícame cómo sumar llevando.")
    contexto = retrieve(q, k=5)

    prompt = f"""{SYSTEM_STYLE}

Pregunta del alumno: {q}

Contexto de tu temario y ejercicios (usa solo si ayuda):
{contexto}

Responde SOLO en el nivel del alumno y, si no encuentras la respuesta en el contexto, explica con tus palabras de forma clara.
Si pide ejercicios, dales en lista (3-5 items) y añade soluciones al final, separadas.
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[{"role":"system","content":"Eres un profesor de Primaria amable y claro."},
                  {"role":"user","content": prompt}]
    ).choices[0].message.content

    # log interacción (sencillo, sin topic/difficulty automática en el MVP)
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute("INSERT INTO interactions(user_id,prompt,response,intent) VALUES(?,?,?,?)",
                (uid, q, resp, intent))
    con.commit(); con.close()
    return resp

with gr.Blocks(title="AULA Matemáticas – RAG MVP") as demo:
    gr.Markdown("## 🧮 Tutor de Matemáticas (MVP)")
    with gr.Row():
        username = gr.Textbox(label="Nombre", placeholder="María...") 
        age = gr.Number(label="Edad", value=9)
        grade = gr.Textbox(label="Curso", value="4º")
    pregunta = gr.Textbox(label="Pregunta o tema (p. ej. 'sumas con llevadas')", lines=2)
    pedir = gr.Checkbox(label="Quiero ejercicios", value=False)
    btn = gr.Button("Preguntar")
    out = gr.Markdown()

    btn.click(fn=rag_answer, inputs=[username, age, grade, pregunta, pedir], outputs=out)

if __name__=="__main__":
    demo.launch()