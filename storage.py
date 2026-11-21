"""PostgreSQL JSON document storage. DATABASE_URL required for production."""
import json
import os
import psycopg
from psycopg.types.json import Jsonb

def _url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta DATABASE_URL: no se guardarán pedidos sin base de datos permanente")
    return url

def load_document(name, default):
    with psycopg.connect(_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS tienda_documentos (nombre TEXT PRIMARY KEY, contenido JSONB NOT NULL)")
            cur.execute("SELECT contenido FROM tienda_documentos WHERE nombre = %s", (name,))
            row = cur.fetchone()
            return row[0] if row else default

def save_document(name, data):
    with psycopg.connect(_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS tienda_documentos (nombre TEXT PRIMARY KEY, contenido JSONB NOT NULL)")
            cur.execute("INSERT INTO tienda_documentos(nombre, contenido) VALUES (%s, %s) ON CONFLICT(nombre) DO UPDATE SET contenido=EXCLUDED.contenido", (name, Jsonb(data)))
