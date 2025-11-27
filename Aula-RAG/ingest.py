# ingest.py (versión mejorada)
import os
import glob
import sqlite3
import numpy as np
import pandas as pd
import argparse

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "db.sqlite"
VECS_DIR = "vecs"
VECS_PATH = os.path.join(VECS_DIR, "all_emb.npy")

client = OpenAI()


# ---------- EMBEDDINGS ----------

def embed_texts(texts, batch_size=64):
    """
    Genera embeddings para una lista de textos en batches.
    Devuelve un np.array de forma (n, d).
    """
    all_embs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        print(f"  → Embedding batch {i}–{i+len(batch)-1} de {len(texts)}")
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )
        embs = [d.embedding for d in resp.data]
        all_embs.extend(embs)
    return np.array(all_embs, dtype=np.float32)


# ---------- LECTURA DE FUENTES ----------

def read_markdowns():
    """
    Lee todos los .md en data/temas.
    Devuelve lista de tuplas: (kind, title, topic, grade, text)
    """
    out = []
    pattern = os.path.join("data", "temas", "*.md")
    files = glob.glob(pattern)

    if not files:
        print("No se han encontrado .md en data/temas/")
        return out

    print(f"Encontrados {len(files)} archivos .md en data/temas/")
    for fp in sorted(files):
        with open(fp, "r", encoding="utf-8") as f:
            text = f.read()

        title = os.path.splitext(os.path.basename(fp))[0]
        parts = title.split("_")
        topic = parts[0] if parts else ""
        grade = parts[-1] if len(parts) > 1 else ""

        out.append((
            "teoria",
            title,
            topic,
            grade,
            text
        ))
    return out


def read_exercises():
    """
    Lee todos los .csv en data/ejercicios.
    Devuelve lista de tuplas: (kind, title, topic, grade, text)
    """
    out = []
    pattern = os.path.join("data", "ejercicios", "*.csv")
    files = glob.glob(pattern)

    if not files:
        print("No se han encontrado .csv en data/ejercicios/")
        return out

    print(f"Encontrados {len(files)} archivos .csv en data/ejercicios/")
    for fp in sorted(files):
        # Por tu comentario, el CSV va con separador ;
        df = pd.read_csv(fp, sep=';')
        df.columns = [c.strip().lower() for c in df.columns]

        for _, r in df.iterrows():
            topic = r.get("topic", "") if not pd.isna(r.get("topic", "")) else ""
            grade = r.get("grade", "") if not pd.isna(r.get("grade", "")) else ""
            enun = r.get("enunciado", "")
            sol = r.get("solucion", "")

            title = f"Ejercicio: {topic}".strip()
            text = f"Enunciado: {enun}\nSolucion: {sol}"

            out.append((
                "ejercicio",
                title,
                topic,
                grade,
                text
            ))
    return out


# ---------- BASE DE DATOS ----------

def init_db(reset=False):
    """
    Crea la BD y la tabla docs. Si reset=True, borra antes el archivo DB.
    Añade una UNIQUE constraint para evitar duplicados.
    """
    if reset and os.path.exists(DB_PATH):
        print(f"Borrando base de datos existente: {DB_PATH}")
        os.remove(DB_PATH)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # UNIQUE para evitar insertar dos veces el mismo texto con mismos metadatos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS docs(
            id INTEGER PRIMARY KEY,
            kind  TEXT,
            title TEXT,
            topic TEXT,
            grade TEXT,
            text  TEXT,
            UNIQUE(kind, title, topic, grade, text)
        )
    """)
    con.commit()
    return con


def insert_items(con, items):
    """
    Inserta una lista de items en la tabla docs, ignorando duplicados.
    """
    if not items:
        print("No hay items para insertar en la BD.")
        return 0

    cur = con.cursor()
    cur.executemany("""
        INSERT OR IGNORE INTO docs(kind, title, topic, grade, text)
        VALUES(?,?,?,?,?)
    """, items)
    con.commit()

    # Número real de filas en BD
    cur.execute("SELECT COUNT(*) FROM docs")
    total_rows = cur.fetchone()[0]
    print(f"BD actualizada. Total de filas en docs: {total_rows}")
    return total_rows


# ---------- MAIN ----------

def main(reset_db=False):
    print("Iniciando ingest...")

    # 1. Inicializar BD
    con = init_db(reset=reset_db)

    # 2. Leer fuentes
    md_items = read_markdowns()
    ex_items = read_exercises()

    items = md_items + ex_items
    print(f"Total de items leídos: {len(items)}")

    if not items:
        print("No hay contenido en data/temas o data/ejercicios. Abortando ingest.")
        con.close()
        return

    # 3. Insertar en BD (evitando duplicados)
    insert_items(con, items)

    # 4. Cargar de DB para asegurar orden e IDs
    df = pd.read_sql_query("SELECT * FROM docs ORDER BY id", con)
    con.close()

    print(f"Generando embeddings para {len(df)} documentos...")

    os.makedirs(VECS_DIR, exist_ok=True)
    embs = embed_texts(df["text"].tolist(), batch_size=64)
    np.save(VECS_PATH, embs)

    print(f"Ingest completado.")
    print(f"   → Documentos en BD: {len(df)}")
    print(f"   → Embeddings guardados en: {VECS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest de contenidos para el RAG Aula.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borra la BD y los embeddings antes de reingestar."
    )
    args = parser.parse_args()

    if args.reset:
        # Si reseteamos, también borramos carpeta vecs
        if os.path.exists(VECS_DIR):
            print(f"Borrando carpeta de embeddings: {VECS_DIR}")
            import shutil
            shutil.rmtree(VECS_DIR, ignore_errors=True)

    main(reset_db=args.reset)