# ingest.py
import os, glob, sqlite3, numpy as np, pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

DB="db.sqlite"
client = OpenAI()

def embed_texts(texts):
    # devuelve np.array (n, d)
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return np.array([d.embedding for d in resp.data], dtype=np.float32)

def read_markdowns():
    out=[]
    for fp in glob.glob("data/temas/*.md"):
        with open(fp,"r",encoding="utf-8") as f:
            text=f.read()
        title=os.path.splitext(os.path.basename(fp))[0]
        # inferencia tonta de topic/grade a partir de nombre
        topic = title.split("_")[0]
        grade = title.split("_")[-1] if "_" in title else ""
        out.append(("teoria", title, topic, grade, text))
    return out

def read_exercises():
    out=[]
    for fp in glob.glob("data/ejercicios/*.csv"):
        #df=pd.read_csv(fp)  # cols: enunciado,solucion,topic,grade,dificultad
        df = pd.read_csv(fp, sep=';')
        df.columns = [c.strip().lower() for c in df.columns]
        for _,r in df.iterrows():
            title=f"Ejercicio: {r.get('topic','')}"
            text=f"Enunciado: {r['enunciado']}\nSolucion: {r.get('solucion','')}"
            out.append(("ejercicio", title, r.get('topic',''), r.get('grade',''), text))
    return out

def main():
    os.makedirs("vecs", exist_ok=True)
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS docs(
        id INTEGER PRIMARY KEY, kind TEXT, title TEXT, topic TEXT, grade TEXT, text TEXT)""")
    con.commit()

    items = read_markdowns() + read_exercises()
    if not items:
        print("No hay contenido en data/temas o data/ejercicios")
        return

    cur.executemany("INSERT INTO docs(kind,title,topic,grade,text) VALUES(?,?,?,?,?)", items)
    con.commit()

    # cargar de DB para asegurar orden e IDs
    df = pd.read_sql_query("SELECT * FROM docs ORDER BY id", con)
    embs = embed_texts(df["text"].tolist())
    np.save("vecs/all_emb.npy", embs)
    print(f"Ingestados {len(df)} trozos. Embeddings guardados en vecs/all_emb.npy")
    con.close()

if __name__=="__main__":
    main()