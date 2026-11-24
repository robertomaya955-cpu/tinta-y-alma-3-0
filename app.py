import os
import io
import json
import secrets
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from flask import abort, send_file
from itsdangerous import URLSafeSerializer, BadSignature
from werkzeug.utils import secure_filename
from pypdf import PdfReader
from flask import Flask, request, render_template_string, redirect, url_for, session, flash
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from storage import load_document, save_document

app = Flask(__name__)
app.secret_key = os.environ["TINTA_ALMA_SECRET"]
# Uso local de prueba. Antes de publicar, configurar una clave segura y HTTPS.

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
FOLDER_ID = "1IbFgn383EZkib2XiVOGxofpwDINYDiM1"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
BOOK_PRICES_FILE = os.path.join(BASE_DIR, "precios_libros.json")
ORDERS_FILE = os.path.join(BASE_DIR, "pedidos.json")
BOOK_META_FILE = os.path.join(BASE_DIR, "datos_libros.json")

HTML = """
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tinta y Alma | Biblioteca digital</title>
<style>
:root{--bg:#0d0b10;--panel:#1c1620;--panel2:#261c28;--rose:#f2bfd3;--muted:#d3c0ce;--line:#664458;--accent:#b56c93}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 85% 0%,#301c30 0%,transparent 45%),var(--bg);color:#f9f4f7;font-family:Arial,Helvetica,sans-serif;line-height:1.5}
a{color:inherit;text-decoration:none}.shell{max-width:1240px;margin:auto;padding:0 22px}
header{border-bottom:1px solid #3b2939;background:#151019}.header-row{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;padding:19px 0}
.brand{font-family:Georgia,serif;font-size:29px;color:var(--rose);font-weight:bold;letter-spacing:1px}.brand small{display:block;font:12px Arial,sans-serif;color:var(--muted);letter-spacing:2px;text-transform:uppercase}
nav{display:flex;gap:8px;flex-wrap:wrap}nav a{padding:10px 14px;border-radius:22px;color:#f2dce7}nav a:hover,nav a:first-child{background:#372237}
.hero{margin:28px 0 20px;padding:43px 42px;border:1px solid #68435d;border-radius:24px;background:linear-gradient(115deg,#402238 0%,#221722 62%,#17141d 100%)}
.kicker{color:#f4bdd2;font-size:12px;font-weight:bold;letter-spacing:3px;text-transform:uppercase}.hero h1{font:clamp(32px,5vw,57px) Georgia,serif;margin:10px 0 8px}.hero p{color:#e7d7e0;max-width:600px;font-size:17px;margin:0}
.searchbar{display:flex;gap:10px;margin:22px 0 0;max-width:710px}.searchbar input{flex:1;min-width:0;padding:15px 19px;border:1px solid #9b728b;border-radius:14px;background:#fff;color:#241722;font-size:16px}.btn,button{display:inline-block;border:0;border-radius:13px;background:var(--accent);color:#fff;padding:12px 16px;font-weight:bold;cursor:pointer;font-size:14px}.btn:hover,button:hover{background:#bf759b}
.section-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin:30px 0 15px}.section-head h2{font:27px Georgia,serif;color:#f4c9d9;margin:0}.subtle{color:var(--muted);font-size:14px}
.categories{display:flex;gap:9px;flex-wrap:wrap;margin:15px 0 25px}.category{border:1px solid #79536d;background:#2b1e2b;padding:9px 13px;border-radius:30px;font-size:13px}.category.active{background:#b26b91;color:#fff;border-color:#e4a9c5}.tag{font-size:12px;color:#f2b9d4;margin-top:8px}.folders{display:flex;flex-wrap:wrap;gap:10px}.folder{background:#2c2030;border:1px solid #69465f;padding:12px 17px;border-radius:12px;color:#f6dbe7}.folder:hover{background:#483047}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:18px}.book{min-width:0;background:var(--panel);border:1px solid #473044;border-radius:17px;padding:15px;display:flex;flex-direction:column;box-shadow:0 8px 25px #0003;transition:transform .2s,border-color .2s,box-shadow .2s}.book:hover{transform:translateY(-5px);border-color:#e0a0c1;box-shadow:0 14px 34px #0006}
.cover-wrap{display:flex;align-items:center;justify-content:center;background:#302531;border-radius:11px;height:235px;overflow:hidden}.cover{max-width:100%;width:100%;height:100%;object-fit:contain}.missing{font-size:53px;color:#f0bfd1}
.book-title{font-size:14px;font-weight:700;margin:13px 0 8px;overflow-wrap:anywhere;min-height:42px}.price{color:#f3b9d2;font-weight:bold;font-size:17px;margin:5px 0 10px}.pending{color:#c8b4c0;font-size:13px;margin:6px 0 12px}.book form{margin-top:auto}.book form button{width:100%;padding:11px 8px}.admin-price{margin-top:10px!important}.admin-price input{width:100%;padding:9px;border-radius:8px;border:1px solid #aa8ca0;margin:0 0 7px}
.notice{background:#342233;border:1px solid #80516f;padding:16px;border-radius:12px}.pagination{display:flex;justify-content:center;align-items:center;gap:18px;flex-wrap:wrap;margin:34px 0 55px}.pagination a{background:#3a2637;border:1px solid #77506a;border-radius:12px;padding:10px 17px}.pagination a:hover{background:#58334e}
footer{border-top:1px solid #342535;padding:22px 0;color:#bba7b6;text-align:center;font-size:13px}
@media(max-width:650px){.shell{padding:0 14px}.header-row{justify-content:center}.brand{text-align:center}nav{justify-content:center}.hero{padding:27px 20px}.searchbar{flex-direction:column}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.book{padding:10px}.cover-wrap{height:190px}.book-title{font-size:13px}nav a{padding:8px 10px}}
</style></head>
<body>
<header><div class="shell header-row"><a class="brand" href="/">Tinta y Alma<small>Tu próxima lectura comienza aquí</small></a><nav><a href="/">📚 Libros</a><a href="/packs">🎁 Packs</a><a href="/carrito">🛒 Carrito</a><a href="/admin/pedidos">📦 Pedidos</a><a href="/admin/panel">⚙️ Administración</a></nav></div></header>
<main class="shell">
<section class="hero"><div class="kicker">Biblioteca digital</div><h1>Historias para llevar en el alma</h1><p>Explorá nuestra colección de libros digitales, descubrí nuevas lecturas y prepará tu pedido de forma sencilla.</p>
<form method="get" class="searchbar"><input name="q" value="{{ q }}" placeholder="Buscar libros o carpetas..." aria-label="Buscar libros"><input type="hidden" name="folder" value="{{ folder_id }}"><input type="hidden" name="categoria" value="{{ categoria }}"><button type="submit">🔎 Buscar</button></form></section>
<div class="section-head"><h2>📚 Elegí una categoría</h2></div>
<div class="categories">{% for c in categorias %}<a class="category {% if categoria == c %}active{% endif %}" href="/?folder={{ folder_id|urlencode }}&q={{ q|urlencode }}&categoria={{ c|urlencode }}">{{ c }}</a>{% endfor %}</div>
<p class="subtle">Categorías sugeridas automáticamente según el título. Pueden existir errores; el filtro se aplica a la carpeta abierta.</p>
{% if parent_id %}<p><a class="btn" href="/?folder={{ parent_id }}">← Volver a la carpeta anterior</a></p>{% endif %}
{% if error %}<p class="notice">{{ error }}</p>{% endif %}
{% set carpetas = items | selectattr('type','equalto','folder') | list %}
{% set libros = items | selectattr('type','equalto','pdf') | list %}
{% if carpetas %}<div class="section-head"><h2>📂 Explorá por carpetas</h2></div><div class="folders">{% for item in carpetas %}<a class="folder" href="/?folder={{ item.id }}">📁 {{ item.name }}</a>{% endfor %}</div>{% endif %}
{% if libros and page == 1 and not q and categoria == "Todas" %}<div class="section-head"><h2>✨ Para descubrir</h2><span class="subtle">Una selección de los libros de esta página</span></div><div class="grid">
{% for item in libros[:4] %}<article class="book"><a href="/libro/{{ item.id }}"><div class="cover-wrap">{% if item.thumbnailLink %}<img class="cover" loading="lazy" src="{{ item.thumbnailLink }}" alt="Portada de {{ item.name }}">{% else %}<span class="missing">📖</span>{% endif %}</div><div class="book-title">{{ item.name }}</div><div class="tag">{{ item.categoria }}</div></a>{% if item.precio is not none %}<div class="price">{{ item.precio_texto }}</div><form method="post" action="/carrito/agregar/libro:{{ item.id }}"><button>🛒 Agregar al carrito</button></form>{% else %}<div class="pending">Precio pendiente</div>{% endif %}{% if admin_activo %}<form class="admin-price" method="post" action="/admin/precio-libro/{{ item.id }}"><input type="hidden" name="nombre" value="{{ item.name }}"><input type="number" name="precio" min="0" step="0.01" placeholder="Precio" required><button>Guardar precio</button></form>{% endif %}</article>{% endfor %}</div>{% endif %}
<div class="section-head"><h2>📚 {% if q or categoria != "Todas" %}Resultados: {{ categoria }}{% else %}Nuestro catálogo{% endif %}</h2><span class="subtle">{{ total_items }} elementos · Página {{ page }} de {{ total_pages }}</span></div>
{% if libros %}<div class="grid">{% for item in libros %}<article class="book"><a href="/libro/{{ item.id }}"><div class="cover-wrap">{% if item.thumbnailLink %}<img class="cover" loading="lazy" src="{{ item.thumbnailLink }}" alt="Portada de {{ item.name }}">{% else %}<span class="missing">📖</span>{% endif %}</div><div class="book-title">{{ item.name }}</div><div class="tag">{{ item.categoria }}</div></a>{% if item.precio is not none %}<div class="price">{{ item.precio_texto }}</div><form method="post" action="/carrito/agregar/libro:{{ item.id }}"><button>🛒 Agregar al carrito</button></form>{% else %}<div class="pending">Precio pendiente</div>{% endif %}{% if admin_activo %}<form class="admin-price" method="post" action="/admin/precio-libro/{{ item.id }}"><input type="hidden" name="nombre" value="{{ item.name }}"><input type="number" name="precio" min="0" step="0.01" placeholder="Precio" required><button>Guardar precio</button></form>{% endif %}</article>{% endfor %}</div>{% elif not carpetas %}<p class="notice">No hay carpetas ni libros para mostrar en esta página.</p>{% endif %}
<div class="pagination">{% if page > 1 %}<a href="/?folder={{ folder_id }}&q={{ q|urlencode }}&categoria={{ categoria|urlencode }}&page={{ page-1 }}">← Anterior</a>{% endif %}<span>Página {{ page }} de {{ total_pages }}</span>{% if page < total_pages %}<a href="/?folder={{ folder_id }}&q={{ q|urlencode }}&categoria={{ categoria|urlencode }}&page={{ page+1 }}">Siguiente →</a>{% endif %}</div>
</main><footer>© Tinta y Alma · Biblioteca digital</footer></body></html>
"""

def cargar_datos_libros():
    return load_document("datos_libros", {})


def guardar_datos_libros(datos):
    save_document("datos_libros", datos)


def titulo_y_autor(nombre):
    limpio = re.sub(r"\.pdf$", "", nombre, flags=re.I).replace("_", " ").strip()
    partes = re.split(r"\s+[-–—]\s+", limpio, maxsplit=1)
    return partes[0].strip(), partes[1].strip() if len(partes) == 2 else ""


def cargar_precios_libros():
    return load_document("precios_libros", {})


def guardar_precios_libros(datos):
    save_document("precios_libros", datos)


def nombre_libro_drive(file_id):
    service = get_drive()
    archivo = service.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    if archivo.get("mimeType") != "application/pdf":
        raise ValueError("El archivo no es un PDF")
    return archivo["name"]

def get_drive():
    token_json = os.environ.get("TINTA_ALMA_GOOGLE_TOKEN_JSON")
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    else:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return build("drive", "v3", credentials=creds)

# Clasificación orientativa por palabras del título (sin modificar Google Drive).
CATEGORIAS = [
    "Todas", "Romance", "Misterio y suspenso", "Novelas y literatura",
    "Autoayuda y desarrollo personal", "Psicología", "Historia",
    "Ciencia ficción y fantasía", "Infantil y juvenil",
    "Negocios y emprendimientos", "Otros libros"
]
PALABRAS_CATEGORIA = {
    "Romance": ["amor", "enamorad", "romance", "beso", "corazon", "pasión", "pasion", "novia", "duque", "boda"],
    "Misterio y suspenso": ["misterio", "asesin", "crimen", "detective", "suspenso", "thriller", "secreto", "homicidio", "policial"],
    "Autoayuda y desarrollo personal": ["autoayuda", "habitos", "ansiedad", "autoestima", "felicidad", "motivacion", "superacion", "crecimiento personal", "karma"],
    "Psicología": ["psicologia", "psicoanalisis", "mente", "trauma", "terapia", "emociones", "depresion"],
    "Historia": ["historia", "historico", "guerra mundial", "revolucion", "imperio", "civilizacion", "biografia"],
    "Ciencia ficción y fantasía": ["fantasia", "magia", "dragon", "hechizo", "narnia", "galaxia", "espacial", "ciencia ficcion", "distopia"],
    "Infantil y juvenil": ["infantil", "cuentos para niños", "adolescentes", "juvenil", "princesa", "hada"],
    "Negocios y emprendimientos": ["negocios", "emprend", "marketing", "ventas", "finanzas", "inversion", "liderazgo", "empresa", "dinero"],
    "Novelas y literatura": ["novela", "poesia", "poemas", "cuentos", "literatura", "relatos", "cronicas"],
}

def normalizar_titulo(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in texto if not unicodedata.combining(c))

def clasificar_libro(titulo):
    titulo = normalizar_titulo(titulo.rsplit(".", 1)[0])
    for categoria, palabras in PALABRAS_CATEGORIA.items():
        for palabra in palabras:
            palabra = normalizar_titulo(palabra)
            if re.search(r"(?<![a-z])" + re.escape(palabra) + r"[a-z]*(?![a-z])", titulo):
                return categoria
    return "Otros libros"

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "Todas")
    if categoria not in CATEGORIAS:
        categoria = "Todas"
    folder_id = request.args.get("folder", FOLDER_ID)
    page = request.args.get("page", 1, type=int)
    page = max(page, 1)
    per_page = 25
    items = []
    error = None
    parent_id = None
    total_items = 0
    total_pages = 1
    precios = cargar_precios_libros()
    metadatos = cargar_datos_libros()

    try:
        service = get_drive()
        folder = service.files().get(
            fileId=folder_id,
            fields="id,name,mimeType,parents"
        ).execute()

        if folder.get("mimeType") != "application/vnd.google-apps.folder":
            raise ValueError("El elemento seleccionado no es una carpeta.")

        parents = folder.get("parents", [])
        if folder_id != FOLDER_ID and parents:
            parent_id = parents[0]

        page_token = None
        while True:
            response = service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
               fields="nextPageToken,files(id,name,mimeType,thumbnailLink)", 
                pageSize=100,
                pageToken=page_token,
                orderBy="name"
            ).execute()

            for item in response.get("files", []):
                name = item.get("name", "")
                mime = item.get("mimeType", "")

                if q and q.casefold() not in name.casefold():
                    continue

                if mime == "application/vnd.google-apps.folder":
                    items.append({"id": item["id"], "name": name, "type": "folder"})
                elif mime == "application/pdf":
                    datos = metadatos.get(item["id"], {})
                    categoria_libro = datos.get("categoria") or clasificar_libro(name)
                    if categoria != "Todas" and categoria_libro != categoria:
                        continue
                    precio = precios.get(item["id"])
                    items.append({
                        "id": item["id"],
                        "name": datos.get("titulo") or titulo_y_autor(name)[0],
                        "type": "pdf",
                        "categoria": categoria_libro,
                        "thumbnailLink": item.get("thumbnailLink"),
                        "precio": precio,
                        "precio_texto": precio_formateado(precio) if precio is not None else ""
                    })

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        items.sort(key=lambda item: (item["type"] != "folder", item["name"].casefold()))
        total_items = len(items)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        page = min(page, total_pages)
        start = (page - 1) * per_page
        items = items[start:start + per_page]

    except Exception as exc:
        error = "No se pudo consultar Google Drive. Detalle: {}: {}".format(
            type(exc).__name__, exc
        )

   
    return render_template_string(
        HTML,
        items=items,
        q=q,
        categoria=categoria,
        categorias=CATEGORIAS,
        error=error,
        folder_id=folder_id,
        parent_id=parent_id,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        admin_activo=bool(session.get("packs_admin"))
    )



@app.route("/libro/<file_id>")
def ver_libro(file_id):
    try:
        service = get_drive()
        archivo = service.files().get(
            fileId=file_id, fields="id,name,mimeType,thumbnailLink"
        ).execute()
        if archivo.get("mimeType") != "application/pdf":
            return "Este archivo no es un PDF.", 404

        titulo_archivo = archivo["name"]
        datos = cargar_datos_libros().get(file_id, {})
        titulo_base, autor_base = titulo_y_autor(titulo_archivo)
        titulo = datos.get("titulo") or titulo_base
        autor = datos.get("autor") or autor_base or "Autor no especificado"
        precio = cargar_precios_libros().get(file_id)
        categoria = datos.get("categoria") or clasificar_libro(titulo_archivo)
        portada = archivo.get("thumbnailLink", "")
        resena = "Todavía no hay una descripción disponible para este libro."
        if datos.get("descripcion"):
            resena = datos["descripcion"]
        else:
          try:
            contenido = service.files().get_media(fileId=file_id).execute()
            lector = PdfReader(io.BytesIO(contenido))
            texto = " ".join(" ".join((pagina.extract_text() or "").split()) for pagina in lector.pages[:12]).strip()
            if texto:
                # Vista previa textual, no una reseña editorial inventada.
                resena = texto[:850] + ("…" if len(texto) > 850 else "")
            else:
                resena = "Este PDF no tiene texto extraíble para generar una vista previa."
          except Exception:
              resena = "La vista previa del contenido no está disponible por el momento."

        return render_template_string("""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ titulo }} | Tinta y Alma</title><style>
:root{--bg:#0d0b10;--panel:#1c1620;--rose:#e9b2c7;--muted:#c7b8c5;--accent:#a35c81}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#f9f4f7;font:16px/1.6 Arial,Helvetica,sans-serif}
a{color:var(--rose);text-decoration:none}.shell{max-width:1080px;margin:auto;padding:22px}
header{background:#151019;border-bottom:1px solid #3b2939}.brand{font:28px Georgia,serif;font-weight:bold}
.back{display:inline-block;margin:22px 0}.detail{display:grid;grid-template-columns:minmax(210px,320px) 1fr;gap:36px;align-items:start}
.coverbox{background:#302531;border:1px solid #65445d;border-radius:20px;padding:20px;min-height:360px;display:grid;place-items:center}
.coverbox img{max-width:100%;max-height:420px;object-fit:contain;border-radius:8px}.placeholder{font-size:70px}
.info{background:var(--panel);border:1px solid #473044;border-radius:20px;padding:30px;min-width:0}
h1{font:clamp(28px,4vw,42px) Georgia,serif;color:var(--rose);line-height:1.2;margin:10px 0 18px;overflow-wrap:anywhere}
.label{color:var(--muted);font-size:14px}.tag{display:inline-block;background:#3c283a;color:#f3c7da;padding:7px 12px;border-radius:22px;font-size:13px}
.price{font-size:27px;color:#f3b9d2;font-weight:bold;margin:20px 0}.btn{background:var(--accent);color:#fff;border:0;border-radius:13px;padding:14px 22px;font-size:16px;font-weight:bold;cursor:pointer}
.description{margin-top:26px;border-top:1px solid #543b50;padding-top:18px;overflow-wrap:anywhere;white-space:pre-wrap}
@media(max-width:680px){.detail{grid-template-columns:1fr;gap:18px}.info{padding:22px}.coverbox{min-height:280px}}
</style></head><body>
<header><div class="shell"><a class="brand" href="/">Tinta y Alma</a></div></header>
<main class="shell"><a class="back" href="/">← Volver al catálogo</a>
<section class="detail"><div class="coverbox">{% if portada %}<img src="{{ portada }}" alt="Portada de {{ titulo }}">{% else %}<span class="placeholder">📚</span>{% endif %}</div>
<div class="info"><span class="tag">{{ categoria }}</span><h1>{{ titulo }}</h1>
<p><span class="label">Autor:</span> {{ autor }}</p>
{% if precio is not none %}<p class="price">{{ precio_texto }}</p>
<form method="post" action="{{ url_for('packs_agregar_carrito', producto_id='libro:' + file_id) }}"><button class="btn" type="submit">🛒 Agregar al carrito</button></form>
{% else %}<p class="label">Precio pendiente de publicación</p>{% endif %}
<div class="description"><h2>📖 Descripción / vista previa</h2><p>{{ resena }}</p></div>
{% if admin_activo %}<p><a class="btn" href="{{ url_for('editar_datos_libro', file_id=file_id) }}">✏️ Editar datos del libro</a></p>{% endif %}
</div></section></main></body></html>""", titulo=titulo, autor=autor, categoria=categoria,
            portada=portada, precio=precio,
            precio_texto=precio_formateado(precio) if precio is not None else "",
            resena=resena, file_id=file_id, admin_activo=admin_requerido())
    except Exception as exc:
        return "No se pudo abrir la ficha del libro: {}.".format(exc), 500


@app.route("/admin/libro/<file_id>", methods=["GET", "POST"])
def editar_datos_libro(file_id):
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    try:
        archivo = get_drive().files().get(fileId=file_id, fields="id,name,mimeType").execute()
        if archivo.get("mimeType") != "application/pdf":
            return "No es un PDF.", 404
    except Exception:
        return "No se pudo consultar el libro en Drive.", 404
    todos = cargar_datos_libros()
    datos = todos.get(file_id, {})
    titulo_base, autor_base = titulo_y_autor(archivo["name"])
    if request.method == "POST":
        categoria = request.form.get("categoria", "")
        if categoria and categoria not in CATEGORIAS[1:]:
            flash("Categoría no válida.")
            return redirect(url_for("editar_datos_libro", file_id=file_id))
        nuevos = {
            "titulo": request.form.get("titulo", "").strip()[:200],
            "autor": request.form.get("autor", "").strip()[:200],
            "categoria": categoria,
            "descripcion": request.form.get("descripcion", "").strip()[:5000],
        }
        if any(nuevos.values()):
            todos[file_id] = nuevos
        else:
            todos.pop(file_id, None)
        guardar_datos_libros(todos)
        flash("Datos del libro guardados.")
        return redirect(url_for("ver_libro", file_id=file_id))
    return render_template_string("""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Editar libro | Tinta y Alma</title>
<style>body{background:#0d0b10;color:#f9f4f7;font:16px Arial,sans-serif;max-width:720px;margin:35px auto;padding:20px}
h1{color:#e9b2c7;font-family:Georgia,serif}label{display:block;margin-top:18px}input,select,textarea{display:block;width:100%;box-sizing:border-box;padding:12px;margin-top:6px;background:#fff;color:#222;border:0;border-radius:9px;font:inherit}
button{background:#a35c81;color:#fff;padding:13px 22px;border:0;border-radius:10px;margin-top:20px;cursor:pointer}a{color:#e9b2c7}p{line-height:1.6}</style></head><body>
<h1>✏️ Editar ficha del libro</h1><p>Archivo en Drive: {{ nombre_original }}</p>
<p>Los cambios se guardan solo en Tinta y Alma. No modifican el PDF de Google Drive.</p>
<form method="post"><label>Título<input name="titulo" maxlength="200" value="{{ datos.get('titulo') or titulo_base }}"></label>
<label>Autor<input name="autor" maxlength="200" value="{{ datos.get('autor') or autor_base }}"></label>
<label>Categoría<select name="categoria"><option value="">Automática</option>{% for cat in categorias %}<option value="{{ cat }}" {% if datos.get('categoria') == cat %}selected{% endif %}>{{ cat }}</option>{% endfor %}</select></label>
<label>Descripción<textarea name="descripcion" rows="9" maxlength="5000" placeholder="Escribí una descripción del libro...">{{ datos.get('descripcion', '') }}</textarea></label>
<button type="submit">💾 Guardar cambios</button></form>
<p><a href="{{ url_for('ver_libro', file_id=file_id) }}">← Volver a la ficha</a></p></body></html>""",
        nombre_original=archivo["name"], datos=datos, titulo_base=titulo_base,
        autor_base=autor_base, categorias=CATEGORIAS[1:], file_id=file_id)


# ===================== TIENDA DE PACKS =====================
PACKS_FILE = os.path.join(BASE_DIR, "packs.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "packs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB por archivo
WHATSAPP_NUMBER = "5492257400129"  # WhatsApp de Tinta y Alma: formato internacional, solo dígitos.
ADMIN_PASSWORD = os.environ["TINTA_ALMA_ADMIN_PASSWORD"]
UALA_ALIAS = "tintayalma.pdf"
MEDIOS_PAGO = {"uala": "Ualá (transferencia)", "transferencia": "Transferencia bancaria", "efectivo": "Efectivo"}

def cargar_packs():
    return load_document("packs", [])


def guardar_packs(packs):
    save_document("packs", packs)


def precio_formateado(valor):
    try:
        return "$" + format(float(valor), ",.2f").replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "$0,00"

@app.route("/packs")
def packs_tienda():
    packs = cargar_packs()
    carrito = session.get("carrito_packs", {})
    cantidad = sum(int(v) for v in carrito.values())
    return render_template_string("""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Packs - Tinta y Alma</title><style>
body{background:#000;color:#fff;font-family:Georgia,serif;max-width:1100px;margin:auto;padding:25px}
h1{color:#d9a0b5;text-align:center}a{color:#f0b8ce}.nav{text-align:center;margin:20px}
.grid{display:flex;flex-wrap:wrap;gap:18px;justify-content:center}
.card{width:220px;background:#171014;border:1px solid #70354b;border-radius:14px;padding:15px;text-align:center}
.card img{width:100%;height:210px;object-fit:contain;background:#241820;border-radius:8px}
button{background:#986d82;color:white;border:0;border-radius:20px;padding:10px 16px;cursor:pointer}
.price{color:#f0b8ce;font-size:1.2em}.desc{white-space:pre-wrap;overflow-wrap:anywhere}
.notice{background:#321b26;padding:12px;border-radius:10px;margin:12px 0}
</style></head><body>
<h1>🎁 Packs de Tinta y Alma</h1><div class="nav"><a href="/">📚 Volver a libros</a> · <a href="/carrito">🛒 Carrito ({{ cantidad }})</a> · <a href="/admin">Administrar packs</a></div>
{% with mensajes=get_flashed_messages() %}{% for mensaje in mensajes %}<div class="notice">{{ mensaje }}</div>{% endfor %}{% endwith %}
{% if packs %}<div class="grid">{% for pack in packs %}
<div class="card">
{% if pack.foto %}<img src="{{ url_for('static', filename='packs/' + pack.foto) }}" alt="{{ pack.nombre }}">{% else %}<div style="height:210px;display:grid;place-items:center;font-size:60px">🎁</div>{% endif %}
<h2>{{ pack.nombre }}</h2><div class="desc">{{ pack.descripcion }}</div><p class="price">{{ pack.precio_texto }}</p>
<form method="post" action="/carrito/agregar/pack:{{ pack.id }}"><button type="submit">Agregar al carrito</button></form>
</div>{% endfor %}</div>
{% else %}<div class="notice">Todavía no hay packs publicados. Entrá en “Administrar packs” para agregar el primero. 💗</div>{% endif %}
</body></html>""", packs=[{**p, "precio_texto": precio_formateado(p.get("precio"))} for p in packs], cantidad=cantidad)

@app.route("/admin/login", methods=["GET", "POST"])
def packs_login():
    if request.method == "POST":
        if request.form.get("password", "") == ADMIN_PASSWORD:
            session["packs_admin"] = True
            return redirect(url_for("panel_admin"))
        flash("La contraseña no es correcta.")
    return render_template_string("""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Acceso administración</title>
<style>body{background:#000;color:#fff;font-family:Georgia,serif;max-width:500px;margin:60px auto;padding:20px}h1{color:#d9a0b5}input,button{padding:12px;border-radius:8px;margin:6px 0}button{background:#986d82;color:white;border:0}</style>
<h1>Administración de Packs</h1>{% with mensajes=get_flashed_messages() %}{% for mensaje in mensajes %}<p>{{ mensaje }}</p>{% endfor %}{% endwith %}
<form method="post"><label>Contraseña de administración</label><br><input type="password" name="password" required><br><button>Ingresar</button></form><p><a href="/packs">Volver a Packs</a></p></html>""")

def admin_requerido():
    return bool(session.get("packs_admin"))

@app.route("/admin/logout")
def packs_logout():
    session.pop("packs_admin", None)
    return redirect(url_for("packs_tienda"))

@app.route("/admin", methods=["GET", "POST"])
def packs_admin():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    packs = cargar_packs()
    return render_template_string("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Administrar Packs</title>
<style>body{background:#000;color:#fff;font-family:Georgia,serif;max-width:900px;margin:auto;padding:25px}h1,h2{color:#d9a0b5}a{color:#f0b8ce}input,textarea{display:block;width:100%;max-width:600px;padding:10px;margin:8px 0;box-sizing:border-box}button{background:#986d82;color:white;border:0;border-radius:15px;padding:10px 15px;cursor:pointer}.fila{border:1px solid #70354b;padding:15px;margin:12px 0;border-radius:10px}.fila img{max-width:80px;max-height:90px;vertical-align:middle}.aviso{background:#321b26;padding:12px;border-radius:10px}</style></head><body>
<h1>Administrar Packs</h1><p><a href="/packs">Ver tienda</a> · <a href="/">Configurar precios de libros</a> · <a href="/admin/pedidos">📦 Administrar pedidos</a> · <a href="/admin/logout">Cerrar sesión</a></p>
{% with mensajes=get_flashed_messages() %}{% for mensaje in mensajes %}<p class="aviso">{{ mensaje }}</p>{% endfor %}{% endwith %}
<p><a href="/admin/packs/importar-drive" style="display:inline-block;background:#a45c82;color:white;padding:12px 16px;border-radius:10px;text-decoration:none">☁️ Importar packs desde Google Drive</a></p>
 <h2>Agregar un pack</h2><form method="post" action="/admin/guardar" enctype="multipart/form-data">
<label>Nombre del pack</label><input name="nombre" required maxlength="120">
<label>Descripción</label><textarea name="descripcion" rows="4" maxlength="2000"></textarea>
<label>Precio (solo números; por ejemplo 12000)</label><input name="precio" type="number" min="0" step="0.01" required>
<label>Foto (opcional; JPG, PNG, WEBP o GIF, máximo 8 MB)</label><input name="foto" type="file" accept=".jpg,.jpeg,.png,.webp,.gif">
<button type="submit">Guardar pack</button></form>
<h2>Packs existentes</h2>{% if packs %}{% for p in packs %}<div class="fila">
{% if p.foto %}<img src="{{ url_for('static', filename='packs/' + p.foto) }}" alt="">{% endif %}<strong>{{ p.nombre }}</strong> — {{ p.precio_texto }}<p>{{ p.descripcion }}</p>
<a href="/admin/editar/{{ p.id }}">Modificar</a>
<form method="post" action="/admin/eliminar/{{ p.id }}" style="display:inline" onsubmit="return confirm('¿Eliminar este pack?');"><button type="submit">Eliminar</button></form></div>{% endfor %}{% else %}<p>Todavía no hay packs.</p>{% endif %}
</body></html>""", packs=[{**p, "precio_texto": precio_formateado(p.get("precio"))} for p in packs])

@app.route("/admin/guardar", methods=["POST"])
def packs_guardar():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    nombre = request.form.get("nombre", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    try:
        precio = float(request.form.get("precio", ""))
        if precio < 0:
            raise ValueError
    except ValueError:
        flash("Ingresá un precio válido.")
        return redirect(url_for("packs_admin"))
    if not nombre:
        flash("El nombre es obligatorio.")
        return redirect(url_for("packs_admin"))
    foto = guardar_foto(request.files.get("foto"))
    packs = cargar_packs()
    packs.append({"id": secrets.token_hex(8), "nombre": nombre, "descripcion": descripcion, "precio": precio, "foto": foto})
    guardar_packs(packs)
    flash("¡Pack guardado! 💗")
    return redirect(url_for("packs_admin"))

def guardar_foto(archivo):
    if not archivo or not archivo.filename:
        return ""
    nombre_original = secure_filename(archivo.filename)
    extension = os.path.splitext(nombre_original)[1].lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise ValueError("Formato de foto no permitido.")
    nombre = secrets.token_hex(8) + extension
    archivo.save(os.path.join(UPLOAD_DIR, nombre))
    return nombre

@app.route("/admin/editar/<pack_id>", methods=["GET", "POST"])
def packs_editar(pack_id):
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    packs = cargar_packs()
    pack = next((p for p in packs if p["id"] == pack_id), None)
    if not pack:
        return "Pack no encontrado.", 404
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        try:
            precio = float(request.form.get("precio", ""))
            if not nombre or precio < 0:
                raise ValueError
        except ValueError:
            flash("Revisá el nombre y el precio.")
            return redirect(url_for("packs_editar", pack_id=pack_id))
        pack["nombre"] = nombre
        pack["descripcion"] = request.form.get("descripcion", "").strip()
        pack["precio"] = precio
        try:
            foto_nueva = guardar_foto(request.files.get("foto"))
        except ValueError as exc:
            flash(str(exc))
            return redirect(url_for("packs_editar", pack_id=pack_id))
        if foto_nueva:
            foto_anterior = pack.get("foto")
            pack["foto"] = foto_nueva
            if foto_anterior:
                try:
                    os.remove(os.path.join(UPLOAD_DIR, foto_anterior))
                except OSError:
                    pass
        guardar_packs(packs)
        flash("Pack actualizado.")
        return redirect(url_for("packs_admin"))
    return render_template_string("""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Modificar pack</title>
<style>body{background:#000;color:#fff;font-family:Georgia,serif;max-width:650px;margin:auto;padding:25px}h1{color:#d9a0b5}input,textarea{display:block;width:100%;padding:10px;margin:8px 0;box-sizing:border-box}button{background:#986d82;color:white;padding:10px;border:0;border-radius:12px}</style>
<h1>Modificar pack</h1><form method="post" enctype="multipart/form-data"><label>Nombre</label><input name="nombre" value="{{ p.nombre }}" required><label>Descripción</label><textarea name="descripcion" rows="4">{{ p.descripcion }}</textarea><label>Precio</label><input type="number" name="precio" min="0" step="0.01" value="{{ p.precio }}" required><label>Cambiar foto (opcional)</label><input type="file" name="foto" accept=".jpg,.jpeg,.png,.webp,.gif"><button>Guardar cambios</button></form><p><a href="/admin">Volver</a></p></html>""", p=pack)

@app.route("/admin/eliminar/<pack_id>", methods=["POST"])
def packs_eliminar(pack_id):
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    packs = cargar_packs()
    pack = next((p for p in packs if p["id"] == pack_id), None)
    if pack:
        packs = [p for p in packs if p["id"] != pack_id]
        guardar_packs(packs)
        if pack.get("foto"):
            try:
                os.remove(os.path.join(UPLOAD_DIR, pack["foto"]))
            except OSError:
                pass
        flash("Pack eliminado.")
    return redirect(url_for("packs_admin"))

@app.route("/admin/precio-libro/<file_id>", methods=["POST"])
def admin_precio_libro(file_id):
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    try:
        nombre = nombre_libro_drive(file_id)
        precio = float(request.form.get("precio", ""))
        if precio < 0:
            raise ValueError
    except Exception:
        flash("No se pudo guardar el precio. Revisá que sea un PDF y que el precio sea válido.")
        return redirect(request.referrer or url_for("index"))
    precios = cargar_precios_libros()
    precios[file_id] = precio
    guardar_precios_libros(precios)
    flash("Precio guardado para: " + nombre)
    return redirect(request.referrer or url_for("index"))

@app.route("/carrito")
def packs_carrito():
    carrito = session.get("carrito", {})
    packs = cargar_packs()
    precios_libros = cargar_precios_libros()
    productos = []
    total = 0.0
    for p in packs:
        key = "pack:" + p["id"]
        cantidad = int(carrito.get(key, 0))
        if cantidad > 0:
            subtotal = float(p["precio"]) * cantidad
            productos.append({"key": key, "nombre": "Pack: " + p["nombre"], "cantidad": cantidad, "subtotal_texto": precio_formateado(subtotal)})
            total += subtotal
    for file_id, cantidad_raw in carrito.items():
        if not file_id.startswith("libro:"):
            continue
        file_id_real = file_id.split(":", 1)[1]
        cantidad = int(cantidad_raw)
        precio = precios_libros.get(file_id_real)
        if cantidad <= 0 or precio is None:
            continue
        try:
            nombre = nombre_libro_drive(file_id_real)
        except Exception:
            nombre = "Libro"
        subtotal = float(precio) * cantidad
        productos.append({"key": file_id, "nombre": "Libro: " + nombre, "cantidad": cantidad, "subtotal_texto": precio_formateado(subtotal)})
        total += subtotal
    return render_template_string("""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Carrito</title>
<style>body{background:#000;color:#fff;font-family:Georgia,serif;max-width:800px;margin:auto;padding:25px}h1{color:#d9a0b5}a{color:#f0b8ce}button{background:#986d82;color:white;border:0;border-radius:12px;padding:8px 12px;cursor:pointer}.fila{border-bottom:1px solid #70354b;padding:12px 0}</style><h1>🛒 Tu carrito</h1><p><a href="/">Seguir viendo libros</a> · <a href="/packs">Seguir viendo packs</a></p>
{% if productos %}{% for p in productos %}<div class="fila"><strong>{{ p.nombre }}</strong> × {{ p.cantidad }} — {{ p.subtotal_texto }} <form method="post" action="/carrito/quitar/{{ p.key }}" style="display:inline"><button>Quitar</button></form></div>{% endfor %}<h2>Total: {{ total_texto }}</h2><p><a href="/pedido-whatsapp"><button>Preparar pedido por WhatsApp</button></a></p>{% else %}<p>Tu carrito está vacío.</p>{% endif %}</html>""", productos=productos, total_texto=precio_formateado(total))

@app.route("/carrito/agregar/<path:producto_id>", methods=["POST"])
def packs_agregar_carrito(producto_id):
    carrito = session.get("carrito", {})
    if producto_id.startswith("libro:"):
        file_id = producto_id.split(":", 1)[1]
        if file_id not in cargar_precios_libros():
            flash("Este libro todavía no tiene precio.")
            return redirect(request.referrer or url_for("index"))
    elif producto_id.startswith("pack:"):
        pack_id = producto_id.split(":", 1)[1]
        if not any(p["id"] == pack_id for p in cargar_packs()):
            return "Pack no encontrado.", 404
    else:
        # Compatibilidad con botones antiguos de packs
        pack_id = producto_id
        if not any(p["id"] == pack_id for p in cargar_packs()):
            return "Producto no encontrado.", 404
        producto_id = "pack:" + pack_id
    carrito[producto_id] = int(carrito.get(producto_id, 0)) + 1
    session["carrito"] = carrito
    flash("Producto agregado al carrito. 💗")
    return redirect(request.referrer or url_for("packs_carrito"))

@app.route("/carrito/quitar/<path:producto_id>", methods=["POST"])
def packs_quitar_carrito(producto_id):
    carrito = session.get("carrito", {})
    carrito.pop(producto_id, None)
    session["carrito"] = carrito
    return redirect(url_for("packs_carrito"))

def cargar_pedidos():
    return load_document("pedidos", [])


def guardar_pedidos(pedidos):
    save_document("pedidos", pedidos)


def normalizar_telefono(valor):
    return "".join(caracter for caracter in valor if caracter.isdigit())


def url_whatsapp(telefono, texto):
    from urllib.parse import quote
    return "https://wa.me/{}?text={}".format(telefono, quote(texto))


def obtener_productos_carrito(carrito):
    packs = cargar_packs()
    precios_libros = cargar_precios_libros()
    productos = []
    total = 0.0
    for pack in packs:
        clave = "pack:" + pack["id"]
        cantidad = int(carrito.get(clave, 0))
        if cantidad > 0:
            precio = float(pack.get("precio", 0))
            subtotal = precio * cantidad
            productos.append({"nombre": "Pack: " + pack["nombre"], "cantidad": cantidad,
                              "precio": precio, "subtotal": subtotal, "pack_id": pack["id"]})
            total += subtotal
    for clave, cantidad_raw in carrito.items():
        if not clave.startswith("libro:"):
            continue
        file_id = clave.split(":", 1)[1]
        cantidad = int(cantidad_raw)
        precio = precios_libros.get(file_id)
        if cantidad <= 0 or precio is None:
            continue
        try:
            nombre = nombre_libro_drive(file_id)
        except Exception:
            nombre = "Libro"
        precio = float(precio)
        subtotal = precio * cantidad
        productos.append({"nombre": "Libro: " + nombre, "cantidad": cantidad,
                          "precio": precio, "subtotal": subtotal, "drive_id": file_id})
        total += subtotal
    return productos, total


@app.route("/pedido-whatsapp", methods=["GET", "POST"])
def packs_pedido_whatsapp():
    carrito = session.get("carrito", {})
    productos, total = obtener_productos_carrito(carrito)
    if not productos:
        flash("El carrito está vacío o los productos no tienen precio.")
        return redirect(url_for("packs_carrito"))

    if request.method == "POST":
        nombre_cliente = request.form.get("nombre", "").strip()
        if not nombre_cliente:
            flash("Por favor, escribí tu nombre.")
            return redirect(url_for("packs_pedido_whatsapp"))
        telefono = normalizar_telefono(request.form.get("whatsapp", ""))
        correo = request.form.get("email", "").strip().lower()
        if not 10 <= len(telefono) <= 15:
            flash("Ingresá un número de WhatsApp válido, con código de país (10 a 15 dígitos).")
            return redirect(url_for("packs_pedido_whatsapp"))
        if correo and (len(correo) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", correo)):
            flash("Revisá el correo electrónico o dejalo vacío.")
            return redirect(url_for("packs_pedido_whatsapp"))
        pedidos = cargar_pedidos()
        numero = secrets.token_hex(3).upper()
        medio_pago = request.form.get("medio_pago", "uala")
        if medio_pago not in MEDIOS_PAGO:
            flash("Seleccioná un medio de pago válido.")
            return redirect(url_for("packs_pedido_whatsapp"))
        pedido = {
            "medio_pago": MEDIOS_PAGO[medio_pago],
            "estado_pago": "Pendiente",
            "id": numero,
            "nombre": nombre_cliente,
            "whatsapp": telefono,
            "email": correo,
            "productos": productos,
            "total": total,
            "estado": "Pendiente de confirmación",
            "creado": __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        pedidos.insert(0, pedido)
        guardar_pedidos(pedidos)

        lineas = ["¡Hola, Tinta y Alma! 💗", "Soy " + nombre_cliente + ".", "Quiero encargar el pedido N.º " + numero, ""]
        for producto in productos:
            lineas.append("• {} × {} — {}".format(
                producto["nombre"], producto["cantidad"],
                precio_formateado(producto["subtotal"])))
        lineas.extend(["", "TOTAL: " + precio_formateado(total),
                       "Medio de pago: " + MEDIOS_PAGO[medio_pago],
                       "Estado del pago: Pendiente"])
        if medio_pago == "uala":
            lineas.extend(["Transferir a Ualá - alias: " + UALA_ALIAS,
                           "El pago se confirmará cuando se acredite la transferencia."])
        elif medio_pago == "transferencia":
            lineas.append("Solicitar los datos bancarios a la tienda.")
        else:
            lineas.append("Coordinar el pago en efectivo con la tienda.")
        session["carrito"] = {}
        session["ultimo_pedido"] = numero
        return redirect(url_for("pedido_confirmacion"))

    return render_template_string("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pedido - Tinta y Alma</title>
<style>body{background:#000;color:#fff;font-family:Georgia,serif;max-width:720px;margin:auto;padding:24px}h1,h2{color:#d9a0b5}a{color:#f0b8ce}.panel{background:#171014;border:1px solid #70354b;border-radius:14px;padding:18px;margin:18px 0}.fila{padding:10px 0;border-bottom:1px solid #492633}button{background:#986d82;color:white;border:0;border-radius:22px;padding:13px 20px;font-size:16px;cursor:pointer;margin-top:16px}.aviso{background:#321b26;padding:12px;border-radius:8px}</style></head><body>
<h1>💗 Preparar pedido</h1><p>Completá tus datos. Guardaremos el pedido y después podrás enviar el aviso por WhatsApp.</p>
{% with mensajes=get_flashed_messages() %}{% for mensaje in mensajes %}<div class="aviso">{{ mensaje }}</div>{% endfor %}{% endwith %}
<div class="panel"><h2>Resumen del pedido</h2>{% for p in productos %}<div class="fila">{{ p.nombre }} × {{ p.cantidad }} — {{ p.subtotal_texto }}</div>{% endfor %}<h2>Total: {{ total_texto }}</h2></div>
<div class="panel"><h2>💳 Cómo pagar</h2><p>Para transferir por Ualá, usá el alias <strong id="alias-uala">{{ alias_uala }}</strong> <button type="button" onclick="navigator.clipboard.writeText('{{ alias_uala }}').then(()=>alert('Alias copiado')).catch(()=>alert('Seleccioná y copiá el alias manualmente'))">📋 Copiar alias</button></p><p>El pedido se confirmará una vez que verifiquemos el pago completo.</p></div>
    <form method="post"><label for="medio_pago">Medio de pago</label><select id="medio_pago" name="medio_pago" required style="display:block;width:100%;padding:12px;margin:10px 0"><option value="uala">Ualá (transferencia)</option><option value="transferencia">Transferencia bancaria</option><option value="efectivo">Efectivo</option></select><label for="nombre">Tu nombre</label><input id="nombre" name="nombre" type="text" maxlength="80" required autocomplete="given-name" placeholder="Escribí tu nombre" style="display:block;width:100%;box-sizing:border-box;padding:13px;margin:10px 0;background:#171014;color:#fff;border:1px solid #986d82;border-radius:8px"><label for="whatsapp" style="display:block;margin-top:14px">WhatsApp (con código de país, obligatorio)</label><input id="whatsapp" name="whatsapp" type="tel" maxlength="20" required placeholder="Ej.: 5491123456789" style="display:block;width:100%;box-sizing:border-box;padding:13px;margin:10px 0;background:#171014;color:#fff;border:1px solid #986d82;border-radius:8px"><label for="email" style="display:block;margin-top:14px">Correo electrónico (opcional)</label><input id="email" name="email" type="email" maxlength="254" placeholder="tu@correo.com" style="display:block;width:100%;box-sizing:border-box;padding:13px;margin:10px 0;background:#171014;color:#fff;border:1px solid #986d82;border-radius:8px"><button type="submit">📦 Registrar pedido</button></form><p><a href="/carrito">Volver al carrito</a></p></body></html>""",
        productos=[{**p, "subtotal_texto": precio_formateado(p["subtotal"])} for p in productos],
        total_texto=precio_formateado(total), alias_uala=UALA_ALIAS)

@app.route("/pedido-confirmado")
def pedido_confirmacion():
    numero = session.get("ultimo_pedido")
    pedido = next((p for p in cargar_pedidos() if p.get("id") == numero), None)
    if not pedido:
        return redirect(url_for("index"))
    lineas = ["¡Hola, Tinta y Alma! 💗", "Soy " + pedido.get("nombre", "") + ".",
              "Registré el pedido N.º " + numero, ""]
    for producto in pedido.get("productos", []):
        lineas.append("• {} × {}".format(producto.get("nombre", "Producto"), producto.get("cantidad", 1)))
    lineas += ["", "TOTAL: " + precio_formateado(pedido.get("total", 0)),
               "Medio de pago: " + pedido.get("medio_pago", ""),
               "Estado del pago: Pendiente"]
    if pedido.get("medio_pago") == MEDIOS_PAGO["uala"]:
        lineas.append("Alias Ualá: " + UALA_ALIAS)
    enlace = url_whatsapp(WHATSAPP_NUMBER, "\n".join(lineas))
    return render_template_string("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pedido registrado | Tinta y Alma</title><style>
    body{margin:0;background:#100d13;color:#f8eff5;font:16px/1.6 Arial,sans-serif}.wrap{max-width:760px;margin:55px auto;padding:26px}.card{background:#241a27;border:1px solid #80546d;border-radius:24px;padding:36px;box-shadow:0 18px 55px #0005}h1{font:36px Georgia,serif;color:#f4b9d1}h2{color:#efc2d5}strong{color:#ffccdf}.btn{display:inline-block;background:#ae628a;color:#fff;text-decoration:none;padding:14px 22px;border-radius:13px;font-weight:bold;margin:8px 10px 8px 0}.secondary{background:#493044}.notice{background:#352536;border-radius:12px;padding:16px;margin:18px 0}</style></head><body><main class="wrap"><div class="card"><h1>💗 ¡Pedido registrado!</h1><p>Tu número de pedido es <strong>{{ pedido.id }}</strong>.</p><p>Importe total: <strong>{{ total }}</strong>.</p><p>Medio de pago: {{ pedido.medio_pago }}.</p>{% if pedido.medio_pago == uala %}<div class="notice"><h2>💳 Transferencia Ualá</h2><p>Alias: <strong>{{ alias }}</strong></p><p>Realizá la transferencia por el importe indicado. El pago se confirma cuando la tienda verifica la acreditación.</p></div>{% else %}<div class="notice">La tienda te indicará cómo completar el pago seleccionado.</div>{% endif %}<p>El pedido ya está guardado. Podés avisarnos por WhatsApp, pero el mensaje <strong>no se envía automáticamente</strong>.</p><a class="btn" href="{{ enlace }}" target="_blank" rel="noopener noreferrer">📲 Avisar por WhatsApp</a><a class="btn secondary" href="/">📚 Volver al catálogo</a></div></main></body></html>""", pedido=pedido, total=precio_formateado(pedido.get("total",0)), uala=MEDIOS_PAGO["uala"], alias=UALA_ALIAS, enlace=enlace)


@app.template_filter("precio")
def filtro_precio(valor):
    return precio_formateado(valor)


@app.route("/admin/pedidos")
def admin_pedidos():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    pedidos = cargar_pedidos()
    return render_template_string("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Pedidos - Tinta y Alma</title><style>
body{background:#000;color:#fff;font-family:Georgia,serif;max-width:1000px;margin:auto;padding:22px}h1,h2{color:#d9a0b5}a{color:#f0b8ce}.pedido{background:#171014;border:1px solid #70354b;border-radius:12px;padding:16px;margin:16px 0;overflow-wrap:anywhere}.estado{color:#f0b8ce;font-weight:bold}button{background:#986d82;color:white;border:0;border-radius:18px;padding:10px 14px;cursor:pointer;margin:5px 4px 5px 0}</style></head><body>
<h1>📦 Pedidos de Tinta y Alma</h1><p><a href="/admin/ventas">💰 Resumen de ventas</a> · <a href="/admin">Administrar packs</a> · <a href="/packs">Ver tienda</a></p>
{% if not pedidos %}<p>Todavía no hay pedidos guardados. Los pedidos nuevos aparecerán aquí.</p>{% endif %}
{% for p in pedidos %}<section class="pedido"><h2>Pedido N.º {{ p.id }}</h2><p class="estado">Estado: {{ p.estado }}</p><p><strong>Nombre:</strong> {{ p.nombre or 'No informado' }}<br><strong>Fecha:</strong> {{ p.creado }}<br><strong>Medio de pago:</strong> {{ p.get('medio_pago', 'Sin registrar') }}<br><strong>Pago:</strong> {{ p.get('estado_pago', 'Sin registrar') }}<br><strong>Tipo:</strong> {% if p.get("es_prueba") %}🧪 Prueba{% else %}Real{% endif %}</p><h3>Productos</h3>{% for producto in p.productos %}<p>{{ producto.nombre }} × {{ producto.cantidad }} — {{ producto.subtotal|precio }}</p>{% endfor %}<h3>Total: {{ p.total|precio }}</h3><a href="{{ url_for('admin_detalle_pedido', pedido_id=p.id) }}"><button type="button">📋 Ver detalles / actualizar estado</button></a></section>{% endfor %}
</body></html>""", pedidos=pedidos)


@app.route("/admin/pedidos/<pedido_id>", methods=["GET", "POST"])
def admin_detalle_pedido(pedido_id):
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    pedidos = cargar_pedidos()
    pedido = next((p for p in pedidos if p.get("id") == pedido_id), None)
    if not pedido:
        return "Pedido no encontrado.", 404
    estados = {
        "confirmado": ("Confirmado", "¡Hola {nombre}! 💗 Confirmamos tu pedido N.º {id} de Tinta y Alma. Total: {total}. ¡Gracias por tu compra!"),
        "pagado": ("Pagado", "¡Hola {nombre}! 💗 Registramos el pago de tu pedido N.º {id} de Tinta y Alma. ¡Muchas gracias!"),
        "enviado": ("Enviado", "¡Hola {nombre}! 📦 Tu pedido N.º {id} de Tinta y Alma ya fue enviado. ¡Gracias por comprar con nosotros! 💗"),
        "entregado": ("Entregado", "¡Hola {nombre}! 📚 Tu pedido N.º {id} de Tinta y Alma figura como entregado. ¡Esperamos que disfrutes tu lectura! 💗"),
    }
    if request.method == "POST":
        accion = request.form.get("estado", "")
        if accion == "vincular_pdf":
            try:
                indice = int(request.form.get("indice", "-1"))
                productos = pedido.get("productos", [])
                if indice < 0 or indice >= len(productos):
                    raise ValueError("Producto no válido.")
                producto = productos[indice]
                if not producto.get("nombre", "").startswith("Libro:"):
                    raise ValueError("Solo se pueden vincular libros individuales.")
                esperado = producto["nombre"].split(":", 1)[1].strip()
                servicio = get_drive()
                identificador = request.form.get("drive_id", "").strip()
                if identificador:
                    archivo = servicio.files().get(fileId=identificador, fields="id,name,mimeType,trashed").execute()
                    if archivo.get("mimeType") != "application/pdf" or archivo.get("trashed"):
                        raise ValueError("El identificador no corresponde a un PDF disponible.")
                    if archivo.get("name", "").casefold() != esperado.casefold():
                        raise ValueError("El nombre del PDF no coincide con el libro comprado. No se vinculó.")
                else:
                    nombre_escapado = esperado.replace("\\", "\\\\").replace("'", "\\'")
                    encontrados = servicio.files().list(
                        q="name = '{}' and mimeType = 'application/pdf' and trashed = false".format(nombre_escapado),
                        fields="nextPageToken,files(id,name,mimeType)", pageSize=100).execute()
                    archivos = encontrados.get("files", [])
                    if len(archivos) != 1 or encontrados.get("nextPageToken"):
                        raise ValueError("Se encontraron {} coincidencias exactas. Ingresá el ID de Drive del PDF correcto.".format(len(archivos)))
                    archivo = archivos[0]
                producto["drive_id"] = archivo["id"]
                guardar_pedidos(pedidos)
                flash("PDF vinculado correctamente. El enlace privado ahora muestra el botón de descarga.")
            except Exception as exc:
                flash("No se pudo vincular el PDF: {}".format(exc))
            return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))
        if accion == "marcar_prueba":
            pedido["es_prueba"] = True
            guardar_pedidos(pedidos)
            flash("Pedido marcado como prueba. No se incluirá en las estadísticas ni informes.")
            return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))
        if accion == "marcar_real":
            pedido["es_prueba"] = False
            guardar_pedidos(pedidos)
            flash("Pedido marcado como real. Se incluirá en las estadísticas.")
            return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))
        if accion == "eliminar_pedido":
            if request.form.get("confirmacion", "") != "ELIMINAR":
                flash("Para eliminar, escribí ELIMINAR en el campo de confirmación.")
                return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))
            guardar_pedidos([p for p in pedidos if p.get("id") != pedido_id])
            flash("Pedido eliminado definitivamente.")
            return redirect(url_for("admin_pedidos"))
        if accion == "cancelar_pago":
            pedido["estado_pago"] = "Cancelado"
            pedido["estado"] = "Pendiente de confirmación"
            pedido["token_descarga"] = ""
            pedido["descarga_vence_en"] = ""
            guardar_pedidos(pedidos)
            flash("Pago cancelado. Enlace de descarga invalidado.")
            return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))
        if accion == "pagado" and pedido.get("estado_pago") == "Pagado":
            flash("Este pago ya fue confirmado. No se generó otro enlace.")
            return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))
        if accion == "pagado":
            medio = request.form.get("medio_pago", "")
            if medio not in MEDIOS_PAGO:
                flash("Seleccioná el medio de pago antes de confirmar.")
                return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))
            pedido["medio_pago"] = MEDIOS_PAGO[medio]
            pedido["estado_pago"] = "Pagado"
            pedido["pago_confirmado_en"] = datetime.now(timezone.utc).isoformat()
            pedido["descarga_vence_en"] = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
            pedido["renovaciones_usadas"] = 0
            pedido["token_descarga"] = secrets.token_urlsafe(32)
        if accion not in estados:
            flash("Estado no válido.")
            return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))
        nombre_estado, plantilla = estados[accion]
        pedido["estado"] = nombre_estado
        guardar_pedidos(pedidos)
        flash(f"Estado actualizado correctamente: {nombre_estado}")
        return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))

    # WhatsApp se abre con un mensaje prearmado: el administrador decide si lo envía.
    # Para entregas fuera de esta PC se necesita una URL pública HTTPS configurada.
    whatsapp_cliente = normalizar_telefono(str(pedido.get("whatsapp", "")))
    public_url = os.environ.get("TINTA_ALMA_PUBLIC_URL", "").strip().rstrip("/")
    if public_url and not public_url.startswith("https://"):
        public_url = ""  # No ofrecer como enlace público una dirección sin HTTPS.
    enlace_entrega_publico = (
        public_url + url_for("entrega_pedido", token=pedido["token_descarga"])
        if public_url and pedido.get("token_descarga") else ""
    )
    mensaje_entrega = (
        "¡Hola, {}! 💗\nTu pago del pedido N.º {} de Tinta y Alma fue confirmado.\n"
        "Descargá tus libros desde este enlace privado (vigente 48 horas):\n{}\n"
        "No compartas el enlace con otras personas. ¡Gracias por tu compra! 📚"
    ).format(pedido.get("nombre", ""), pedido.get("id", ""), enlace_entrega_publico)
    enlace_whatsapp_entrega = (
        url_whatsapp(whatsapp_cliente, mensaje_entrega)
        if enlace_entrega_publico and 10 <= len(whatsapp_cliente) <= 15
        and pedido.get("estado_pago") == "Pagado" else ""
    )
    return render_template_string("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">*{box-sizing:border-box}
body{
    background:#080608;
    color:#fff5f8;
    font-family:Arial,sans-serif;
    max-width:1100px;
    margin:auto;
    padding:28px;
}
h1{
    color:#e8c77d;
    font-size:30px;
}
h2{
    color:#edb8d1;
    font-size:23px;
}
h3{color:#e8c77d}
a{color:#f0b8ce}
.panel{
    background:linear-gradient(145deg,#21151d,#140e14);
    border:1px solid #80546d;
    border-radius:20px;
    padding:25px;
    margin:22px 0;
    box-shadow:0 8px 25px rgba(0,0,0,.4);
}
.estado{
    background:#39212f;
    color:#f5c4dc;
    font-weight:bold;
    border-radius:12px;
    padding:14px;
}
.fila{
    background:#281b25;
    border-bottom:1px solid #80546d;
    border-radius:10px;
    padding:16px;
    margin:8px 0;
}
button{
    background:linear-gradient(135deg,#a45c82,#70354b);
    color:white;
    border:1px solid #b77b99;
    border-radius:12px;
    padding:14px 20px;
    font-weight:bold;
    cursor:pointer;
    margin:6px 0;
    transition:.2s;
}
button:hover{
    background:#bd779b;
    transform:translateY(-2px);
}
.acciones form{
    display:inline-block;
    margin:6px;
}
input,select{
    background:#30212c;
    color:white;
    border:1px solid #80546d;
    border-radius:9px;
    padding:12px;
    max-width:100%;
}
p{line-height:1.7}
small{color:#d5b6c9}
@media(max-width:600px){
    body{padding:12px}
    .panel{padding:16px}
    h1{font-size:24px}
    .acciones form{display:block;margin:10px 0}
    button{width:100%}
}
:root{--bg:#100d14;--side:#211725;--card:#281d2c;--rose:#edb8d1;--line:#60455c;--text:#fff5fb}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 Arial,sans-serif}
a{color:var(--rose);text-decoration:none}.layout{display:flex;min-height:100vh}.sidebar{width:240px;flex-shrink:0;background:var(--side);border-right:1px solid var(--line);padding:25px 16px}.logo{font:25px Georgia,serif;color:var(--rose);margin-bottom:6px}.subtitle{font-size:12px;color:#cbb6c8;margin-bottom:28px}.sidebar a{display:block;color:#f5dbe9;padding:12px;border-radius:10px;margin:3px 0}.sidebar a:hover,.sidebar a.active{background:#55364e}.main{flex:1;min-width:0;padding:34px;max-width:1500px}h1{font:34px Georgia,serif;color:var(--rose);margin:0 0 8px}h2{font:24px Georgia,serif;color:var(--rose)}.muted{color:#cbb6c8}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:25px 0}.card,.box{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px}.number{font-size:30px;font-weight:bold;color:var(--rose)}.actions{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}.button,button{background:#a45c82;border:0;border-radius:10px;color:white;padding:10px 15px;cursor:pointer;display:inline-block;font:inherit}.button:hover,button:hover{background:#c0789f}.tablewrap{overflow-x:auto}.table{width:100%;border-collapse:collapse;text-align:left}.table th,.table td{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}.table th{color:var(--rose)}input,select{padding:10px;border:1px solid #aa86a1;border-radius:8px;max-width:100%}.search{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}.search input{min-width:230px}.notice{padding:14px;background:#3b2939;border-radius:10px}.pager{display:flex;gap:15px;align-items:center;margin:25px 0}.badge{border-radius:20px;padding:4px 9px;background:#503449;color:#f9d8e8;font-size:12px}
@media(max-width:760px){.layout{display:block}.sidebar{width:auto}.sidebar a{display:inline-block}.main{padding:20px}.table th,.table td{padding:8px}}
</style></head><body><div class="layout"><aside class="sidebar"><div class="logo">Tinta y Alma</div><div class="subtitle">Panel de administración</div>
{% for etiqueta,ruta,clave in menu %}<a class="{% if actual == clave %}active{% endif %}" href="{{ ruta }}">{{ etiqueta }}</a>{% endfor %}
</aside><main class="main"><h1>{{ titulo }}</h1><p class="muted">{{ subtitulo }}</p>
{% with mensajes=get_flashed_messages() %}{% for m in mensajes %}<p class="notice">{{ m }}</p>{% endfor %}{% endwith %}
{{ contenido|safe }}</main></div></body></html>"""

from markupsafe import Markup


def mostrar_panel(titulo, subtitulo, actual, contenido):
    menu = [
        ("🏠 Inicio", url_for("panel_admin"), "inicio"),
        ("📚 Libros", url_for("panel_libros"), "libros"),
        ("💰 Precios", url_for("panel_precios"), "precios"),
        ("🎁 Packs", url_for("packs_admin"), "packs"),
        ("☁️ Importar packs de Drive", url_for("packs_importar_drive"), "importar"),
        ("🛒 Pedidos", url_for("admin_pedidos"), "pedidos"),
        ("📊 Ventas", url_for("panel_ventas"), "ventas"),
        ("📈 Panel avanzado", url_for("panel_avanzado"), "avanzado"),
        ("💸 Gastos", url_for("panel_gastos"), "gastos"),
        ("⚙️ Configuración", url_for("panel_configuracion"), "configuracion"),
        ("📖 Ver tienda", url_for("index"), "tienda"),
        ("🚪 Cerrar sesión", url_for("packs_logout"), "salir"),
    ]
    return render_template_string(PANEL_HTML, titulo=titulo, subtitulo=subtitulo,
                                  actual=actual, menu=menu, contenido=Markup(contenido))


def estadisticas_pedidos():
    pedidos = [p for p in cargar_pedidos() if not p.get("es_prueba", False)]
    pagados = [p for p in pedidos if pago_confirmado(p)]
    total = sum(float(p.get("total") or 0) for p in pagados)
    return pedidos, pagados, total


@app.route("/admin/panel")
def panel_admin():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    pedidos, pagados, total = estadisticas_pedidos()
    datos = dict(pedidos=len(pedidos), pendientes=sum(1 for p in pedidos if p.get("estado") == "Pendiente de confirmación"),
                 cobrados=len(pagados), ingresos=precio_formateado(total),
                 libros=len(cargar_datos_libros()), precios=len(cargar_precios_libros()), packs=len(cargar_packs()))
    contenido = render_template_string("""
    <div class="cards"><div class="card"><div>📦 Pedidos registrados</div><div class="number">{{ d.pedidos }}</div></div>
    <div class="card"><div>⏳ Pedidos pendientes</div><div class="number">{{ d.pendientes }}</div></div>
    <div class="card"><div>💳 Pedidos pagados o posteriores</div><div class="number">{{ d.cobrados }}</div></div>
    <div class="card"><div>💗 Total registrado como pagado*</div><div class="number">{{ d.ingresos }}</div></div></div>
    <div class="box"><h2>Tu biblioteca y tienda</h2><p>Fichas personalizadas: <b>{{ d.libros }}</b> · Libros con precio: <b>{{ d.precios }}</b> · Packs: <b>{{ d.packs }}</b></p>
    <div class="actions"><a class="button" href="{{ url_for('panel_libros') }}">📚 Gestionar libros</a><a class="button" href="{{ url_for('panel_precios') }}">💰 Gestionar precios</a><a class="button" href="{{ url_for('admin_pedidos') }}">🛒 Ver pedidos</a><a class="button" href="{{ url_for('packs_admin') }}">🎁 Gestionar packs</a></div>
    <p class="muted">*Son importes de pedidos marcados como Pagado, Enviado o Entregado. No verifica depósitos bancarios ni descuenta gastos.</p></div>
    """,d=datos)
    return mostrar_panel("🏠 Inicio", "Resumen de la actividad de Tinta y Alma", "inicio", contenido)


def consultar_libros_panel():
    carpeta = request.args.get("folder", FOLDER_ID)
    buscar = request.args.get("q", "").strip().casefold()
    pagina = max(1, request.args.get("page", 1, type=int))
    metadatos = cargar_datos_libros()
    precios = cargar_precios_libros()
    service = get_drive()
    carpeta_info = service.files().get(fileId=carpeta, fields="id,name,mimeType,parents").execute()
    if carpeta_info.get("mimeType") != "application/vnd.google-apps.folder":
        raise ValueError("El elemento no es una carpeta")
    padre = (carpeta_info.get("parents") or [None])[0] if carpeta != FOLDER_ID else None
    elementos = []
    token = None
    while True:
        respuesta = service.files().list(q=f"'{carpeta}' in parents and trashed = false",
                                         fields="nextPageToken,files(id,name,mimeType)", pageSize=100,
                                         pageToken=token, orderBy="name").execute()
        for f in respuesta.get("files", []):
            if f.get("mimeType") == "application/vnd.google-apps.folder":
                tipo = "carpeta"
            elif f.get("mimeType") == "application/pdf":
                tipo = "libro"
            else:
                continue
            titulo = metadatos.get(f["id"], {}).get("titulo") or titulo_y_autor(f["name"])[0]
            if buscar and buscar not in titulo.casefold() and buscar not in f["name"].casefold():
                continue
            elementos.append(dict(id=f["id"], titulo=titulo, tipo=tipo,
                                  precio=precios.get(f["id"]), nombre=f["name"]))
        token = respuesta.get("nextPageToken")
        if not token:
            break
    elementos.sort(key=lambda x: (x["tipo"] != "carpeta", x["titulo"].casefold()))
    paginas = max(1, (len(elementos)+24)//25)
    pagina = min(pagina, paginas)
    return elementos[(pagina-1)*25:pagina*25], carpeta, padre, buscar, pagina, paginas, len(elementos)


def pagina_listado_libros(es_precios=False):
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    try:
        libros, carpeta, padre, buscar, pagina, paginas, total = consultar_libros_panel()
        error = None
    except Exception as exc:
        libros, carpeta, padre, buscar, pagina, paginas, total = [], FOLDER_ID, None, "", 1, 1, 0
        error = "No se pudo consultar Drive: " + str(exc)
    contenido = render_template_string("""
    {% if error %}<p class="notice">{{ error }}</p>{% endif %}
    <form class="search" method="get"><input type="hidden" name="folder" value="{{ carpeta }}"><input name="q" placeholder="Buscar en esta carpeta" value="{{ buscar }}"><button>🔎 Buscar</button></form>
    {% if padre %}<p><a class="button" href="{{ url_for(destino, folder=padre) }}">← Carpeta anterior</a></p>{% endif %}
    <div class="box"><p class="muted">{{ total }} elementos · Página {{ pagina }} de {{ paginas }}. Se muestran los libros de la carpeta abierta.</p>
    <div class="tablewrap"><table class="table"><thead><tr><th>Libro o carpeta</th><th>Precio</th><th>Acciones</th></tr></thead><tbody>
    {% for l in libros %}<tr><td>{% if l.tipo == 'carpeta' %}📁{% else %}📖{% endif %} {{ l.titulo }}</td>
    <td>{% if l.tipo == 'libro' %}{{ l.precio|precio if l.precio is not none else 'Sin precio' }}{% else %}—{% endif %}</td>
    <td>{% if l.tipo == 'carpeta' %}<a href="{{ url_for(destino, folder=l.id) }}">Abrir carpeta →</a>
    {% else %}<a href="{{ url_for('editar_datos_libro', file_id=l.id) }}">✏️ Editar ficha</a> · <a href="{{ url_for('ver_libro', file_id=l.id) }}">Ver libro</a>
    <form action="{{ url_for('admin_precio_libro', file_id=l.id) }}" method="post" style="margin-top:8px;display:flex;gap:5px;flex-wrap:wrap"><input type="number" name="precio" min="0" step="0.01" placeholder="Nuevo precio" required style="width:135px"><button>Guardar precio</button></form>{% endif %}</td></tr>{% endfor %}
    </tbody></table></div><div class="pager">{% if pagina > 1 %}<a href="{{ url_for(destino, folder=carpeta, q=buscar, page=pagina-1) }}">← Anterior</a>{% endif %}<span>{{ pagina }} / {{ paginas }}</span>{% if pagina < paginas %}<a href="{{ url_for(destino, folder=carpeta, q=buscar, page=pagina+1) }}">Siguiente →</a>{% endif %}</div></div>
    """,libros=libros, carpeta=carpeta, padre=padre, buscar=buscar, pagina=pagina,
        paginas=paginas,total=total,error=error, destino="panel_precios" if es_precios else "panel_libros")
    return mostrar_panel("💰 Precios" if es_precios else "📚 Libros", "Gestioná los libros de Google Drive sin modificar los PDF.",
                         "precios" if es_precios else "libros", contenido)


@app.route("/admin/panel/libros")
def panel_libros():
    return pagina_listado_libros()


@app.route("/admin/panel/precios")
def panel_precios():
    return pagina_listado_libros(True)


@app.route("/admin/panel/ventas")
def panel_ventas():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    pedidos, pagados, total = estadisticas_pedidos()
    contenido = render_template_string("""<div class="cards"><div class="card">Pedidos registrados<div class="number">{{ pedidos|length }}</div></div><div class="card">Pedidos pagados, enviados o entregados<div class="number">{{ pagados|length }}</div></div><div class="card">Importe registrado<div class="number">{{ total|precio }}</div></div></div>
    <div class="box"><h2>Últimos pedidos</h2><div class="tablewrap"><table class="table"><tr><th>N.º</th><th>Fecha</th><th>Estado</th><th>Total</th><th>Acción</th></tr>
    {% for p in pedidos[:30] %}<tr><td>{{ p.id }}</td><td>{{ p.creado }}</td><td><span class="badge">{{ p.estado }}</span>{% if p.get("es_prueba") %} 🧪 Prueba{% endif %}</td><td>{{ p.total|precio }}</td><td><a href="{{ url_for('admin_detalle_pedido', pedido_id=p.id) }}">Ver pedido</a></td></tr>{% endfor %}</table></div>
    <p class="muted">Los importes se basan en los estados guardados manualmente, no en pagos bancarios confirmados automáticamente.</p></div>""", pedidos=pedidos,pagados=pagados,total=total)
    return mostrar_panel("📊 Ventas", "Resumen de pedidos e importes registrados", "ventas", contenido)


@app.route("/admin/panel/configuracion")
def panel_configuracion():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    contenido = render_template_string("""<div class="box"><h2>Archivos de la tienda</h2>
    <p>Los datos se guardan en la carpeta del programa: <strong>datos_libros.json</strong>, <strong>precios_libros.json</strong>, <strong>packs.json</strong> y <strong>pedidos.json</strong>.</p>
    <p>Conservá copias de seguridad de esos archivos y de <strong>token.json</strong>. No compartas token.json ni contraseñas.</p>
    <p>Para cambiar la contraseña de administración, configurá la variable de entorno <strong>TINTA_ALMA_ADMIN_PASSWORD</strong> antes de iniciar el servidor.</p>
    <p>Esta aplicación funciona de forma local en tu computadora.</p>
    <a class="button" href="{{ url_for('packs_logout') }}">Cerrar sesión</a></div>""")
    return mostrar_panel("⚙️ Configuración", "Información y mantenimiento de tu tienda", "configuracion", contenido)



@app.route("/admin/ventas")
def admin_ventas():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    pedidos = cargar_pedidos()
    pagados = [p for p in pedidos if p.get("estado_pago") == "Pagado" or ("estado_pago" not in p and p.get("estado") == "Pagado")]
    total = sum(float(p.get("total", 0)) for p in pagados)
    contenido = render_template_string("""
    <div class="box"><h2>📊 Resumen de ventas</h2>
    <p>Pedidos registrados: <strong>{{ cantidad }}</strong></p>
    <p>Pedidos pagados: <strong>{{ pagados }}</strong></p>
    <p>Total cobrado: <strong>{{ total }}</strong></p>
    <p class="muted">Los pedidos antiguos marcados como Pagado se incluyen en el resumen. Las transferencias no se verifican automáticamente.</p>
    <p><a class="button" href="{{ url_for('admin_pedidos') }}">📦 Ver pedidos y registrar pagos</a></p></div>
    """, cantidad=len(pedidos), pagados=len(pagados), total=precio_formateado(total))
    return mostrar_panel("💰 Ventas y pagos", "Control de cobros confirmados", "ventas", contenido)

# ===================== IMPORTAR PACKS DESDE DRIVE =====================
# La conexión es de solo lectura: se guarda una referencia a la carpeta.
def carpetas_drive_para_packs():
    servicio = get_drive()
    resultado = []
    pendientes = [(FOLDER_ID, 0)]
    visitadas = set()
    # Permite localizar packs en subcarpetas, con un límite de seguridad.
    while pendientes and len(visitadas) < 300:
        carpeta, nivel = pendientes.pop(0)
        if carpeta in visitadas:
            continue
        visitadas.add(carpeta)
        token = None
        while True:
            respuesta = servicio.files().list(
                q=f"'{carpeta}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.folder'",
                fields="nextPageToken,files(id,name)", pageSize=100,
                pageToken=token, orderBy="name").execute()
            for elemento in respuesta.get("files", []):
                resultado.append(elemento)
                if nivel < 4:
                    pendientes.append((elemento["id"], nivel + 1))
            token = respuesta.get("nextPageToken")
            if not token:
                break
    return resultado


def contar_pdfs_carpeta(servicio, folder_id):
    cantidad = 0
    token = None
    while True:
        respuesta = servicio.files().list(
            q=f"'{folder_id}' in parents and trashed = false and mimeType = 'application/pdf'",
            fields="nextPageToken,files(id)", pageSize=1000,
            pageToken=token).execute()
        cantidad += len(respuesta.get("files", []))
        token = respuesta.get("nextPageToken")
        if not token:
            return cantidad


@app.route("/admin/packs/importar-drive", methods=["GET", "POST"])
def packs_importar_drive():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    existentes = cargar_packs()
    ids_importados = {p.get("drive_folder_id") for p in existentes if p.get("drive_folder_id")}
    if request.method == "POST":
        folder_id = request.form.get("folder_id", "").strip()
        nombre = request.form.get("nombre", "").strip()[:120]
        descripcion = request.form.get("descripcion", "").strip()[:2000]
        try:
            precio = float(request.form.get("precio", ""))
            if not nombre or not folder_id or not (0 <= precio < 1000000000):
                raise ValueError()
            if folder_id in ids_importados:
                flash("Esta carpeta ya fue importada. No se creó un duplicado.")
                return redirect(url_for("packs_importar_drive"))
            servicio = get_drive()
            carpeta = servicio.files().get(fileId=folder_id, fields="id,name,mimeType").execute()
            if carpeta.get("mimeType") != "application/vnd.google-apps.folder":
                raise ValueError("El elemento no es una carpeta")
            # Solo permitimos carpetas descubiertas dentro de la biblioteca configurada.
            permitidas = {c["id"] for c in carpetas_drive_para_packs()}
            if folder_id not in permitidas:
                raise ValueError("La carpeta no pertenece a la biblioteca configurada")
            cantidad = contar_pdfs_carpeta(servicio, folder_id)
            if cantidad == 0:
                flash("La carpeta no contiene PDF directamente. No se importó.")
                return redirect(url_for("packs_importar_drive"))
            existentes.append({"id": secrets.token_hex(8), "nombre": nombre,
                               "descripcion": descripcion, "precio": precio,
                               "foto": "", "drive_folder_id": folder_id})
            guardar_packs(existentes)
            flash(f"Pack importado: {nombre} ({cantidad} PDF). Los archivos de Drive no se modificaron.")
            return redirect(url_for("packs_admin"))
        except (ValueError, TypeError) as exc:
            flash("Revisá los datos del pack. " + str(exc))
        except Exception as exc:
            flash("No se pudo importar la carpeta: " + str(exc))
        return redirect(url_for("packs_importar_drive"))
    try:
        carpetas = carpetas_drive_para_packs()
        error = None
    except Exception as exc:
        carpetas = []
        error = "No se pudieron consultar las carpetas de Google Drive: " + str(exc)
    contenido = render_template_string("""
    <div class="box"><h2>☁️ Importar un pack desde Google Drive</h2>
    <p>Seleccioná una carpeta que contenga los PDF del pack. Se guardará una referencia en <b>packs.json</b>; no se copiarán ni modificarán los archivos de Drive.</p>
    {% if error %}<p class="notice">{{ error }}</p>{% endif %}
    {% if carpetas %}<form method="post">
      <p><label>Carpeta de Drive<br><select name="folder_id" id="carpeta" required style="width:100%;max-width:620px" onchange="document.getElementById('nombre').value=this.options[this.selectedIndex].dataset.nombre || ''">
      <option value="">Elegí una carpeta...</option>
      {% for c in carpetas %}<option value="{{ c.id }}" data-nombre="{{ c.name }}" {% if c.id in ids_importados %}disabled{% endif %}>{{ c.name }}{% if c.id in ids_importados %} (ya importada){% endif %}</option>{% endfor %}
      </select></label></p>
      <p><label>Nombre del pack<br><input id="nombre" name="nombre" maxlength="120" required style="width:100%;max-width:620px"></label></p>
      <p><label>Precio<br><input name="precio" type="number" min="0" step="0.01" required></label></p>
      <p><label>Descripción (opcional)<br><textarea name="descripcion" maxlength="2000" rows="4" style="width:100%;max-width:620px;padding:10px;border-radius:8px"></textarea></label></p>
      <button type="submit">🎁 Importar pack</button>
    </form>{% else %}<p>No se encontraron carpetas para importar.</p>{% endif %}
    <p class="muted">Solo se importan carpetas con archivos PDF directamente dentro. Si una carpeta contiene otras subcarpetas, elegí la carpeta que tenga los PDF.</p>
    <p><a class="button" href="{{ url_for('packs_admin') }}">← Volver a administrar packs</a></p></div>
    """, carpetas=carpetas, ids_importados=ids_importados, error=error)
    return mostrar_panel("☁️ Importar packs", "Convertí tus carpetas de Drive en packs de la tienda", "importar", contenido)




# ===================== TINTA Y ALMA 2.1: FINANZAS =====================
# Archivo independiente: nunca se alteran los JSON existentes de la tienda.
GASTOS_FILE = os.path.join(BASE_DIR, "gastos.json")
CATEGORIAS_GASTOS = ("Publicidad", "Compras", "Servicios", "Otros")


def cargar_gastos():
    return load_document("gastos", [])


def guardar_gastos(gastos):
    save_document("gastos", gastos)


def fecha_pedido(pedido):
    from datetime import datetime
    try:
        return datetime.strptime(pedido.get("creado", ""), "%d/%m/%Y %H:%M").strftime("%Y-%m")
    except (ValueError, TypeError):
        return ""


def pago_confirmado(pedido):
    # Estado explícito tiene prioridad. Para pedidos antiguos sin estado_pago,
    # se reconoce el estado de pedido que históricamente representaba cobro.
    pago = str(pedido.get("estado_pago", "")).casefold()
    if pago:
        return pago == "pagado"
    return str(pedido.get("estado", "")).casefold() in ("pagado", "enviado", "entregado")


def es_prueba(pedido):
    return bool(pedido.get("es_prueba", False))


def resumen_financiero(mes=""):
    pedidos = [p for p in cargar_pedidos() if not es_prueba(p) and (not mes or fecha_pedido(p) == mes)]
    gastos = [g for g in cargar_gastos() if not mes or str(g.get("fecha", ""))[:7] == mes]
    cobrados = [p for p in pedidos if pago_confirmado(p)]
    pendientes = [p for p in pedidos if not pago_confirmado(p) and str(p.get("estado_pago", "")).casefold() != "cancelado"]
    ingresos = sum(float(p.get("total") or 0) for p in cobrados)
    egresos = sum(float(g.get("importe") or 0) for g in gastos)
    por_medio = {}
    for p in cobrados:
        medio = p.get("medio_pago") or "Sin registrar"
        por_medio[medio] = por_medio.get(medio, 0) + float(p.get("total") or 0)
    cantidades = {}
    for p in cobrados:
        for producto in p.get("productos", []):
            nombre = producto.get("nombre", "Producto")
            cantidades[nombre] = cantidades.get(nombre, 0) + int(producto.get("cantidad", 0))
    return dict(pedidos=pedidos, cobrados=cobrados, pendientes=pendientes, gastos=gastos,
                ingresos=ingresos, egresos=egresos, resultado=ingresos-egresos,
                por_medio=por_medio, cantidades=cantidades,
                pendiente_total=sum(float(p.get("total") or 0) for p in pendientes),
                ventas_total=sum(float(p.get("total") or 0) for p in pedidos))


def validar_mes(mes):
    from datetime import datetime
    if not mes:
        return ""
    try:
        datetime.strptime(mes, "%Y-%m")
    except ValueError:
        return None
    return mes if len(mes) == 7 else None


@app.route("/admin/avanzado")
def panel_avanzado():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    from datetime import date
    mes = validar_mes(request.args.get("mes", date.today().strftime("%Y-%m")))
    if mes is None:
        return "Mes inválido", 400
    d = resumen_financiero(mes)
    contenido = render_template_string("""
    <form class="search" method="get"><label>Mes <input type="month" name="mes" value="{{ mes }}"></label><button>Consultar</button>
    <a class="button" href="{{ url_for('panel_avanzado', mes='') }}">Todos los meses</a></form>
    <div class="cards">
    <div class="card">Ventas registradas<div class="number">{{ d.ventas_total|precio }}</div></div>
    <div class="card">Dinero cobrado<div class="number">{{ d.ingresos|precio }}</div></div>
    <div class="card">Pendiente de cobro<div class="number">{{ d.pendiente_total|precio }}</div></div>
    <div class="card">Gastos<div class="number">{{ d.egresos|precio }}</div></div>
    <div class="card">Resultado (cobros − gastos)<div class="number">{{ d.resultado|precio }}</div></div></div>
    <div class="actions"><a class="button" href="{{ url_for('panel_gastos') }}">💸 Cargar gastos</a>
    <a class="button" href="{{ url_for('descargar_informe', formato='pdf', mes=mes) }}">📄 Descargar PDF</a>
    <a class="button" href="{{ url_for('descargar_informe', formato='xlsx', mes=mes) }}">📊 Descargar Excel</a></div>
    <div class="box"><h2>📊 Cobros por medio de pago</h2>
    {% if d.por_medio %}{% set maximo = d.por_medio.values()|max %}{% for medio, importe in d.por_medio.items() %}
    <p>{{ medio }} — {{ importe|precio }}</p><div style="height:20px;background:#503449;border-radius:8px"><div style="width:{{ (importe/maximo*100)|round|int if maximo else 0 }}%;height:20px;background:#e9b2c7;border-radius:8px"></div></div>
    {% endfor %}{% else %}<p>No hay cobros confirmados en el período.</p>{% endif %}</div>
    <div class="box"><h2>📚 Productos vendidos (pedidos cobrados)</h2>
    {% for nombre, cantidad in d.cantidades.items() %}<p>{{ nombre }}: {{ cantidad }}</p>{% else %}<p>Sin productos vendidos.</p>{% endfor %}</div>
    <p class="muted">El resultado es cobros menos gastos registrados; no equivale necesariamente a la ganancia contable o fiscal. Los pedidos de prueba marcados como tales se excluyen. La fecha de cobro no se registra históricamente: los cobros se agrupan por fecha del pedido.</p>
    """, d=d, mes=mes)
    return mostrar_panel("📈 Ventas y ganancias", "Informe financiero por período", "avanzado", contenido)


@app.route("/admin/gastos", methods=["GET", "POST"])
def panel_gastos():
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    from datetime import date, datetime
    gastos = cargar_gastos()
    editar_id = request.args.get("editar", "")
    edicion = next((g for g in gastos if g.get("id") == editar_id), None)
    if request.method == "POST":
        accion = request.form.get("accion", "guardar")
        id_gasto = request.form.get("id", "")
        actual = next((g for g in gastos if g.get("id") == id_gasto), None)
        if accion == "eliminar":
            if not actual:
                return "Gasto no encontrado", 404
            guardar_gastos([g for g in gastos if g.get("id") != id_gasto])
            flash("Gasto eliminado.")
            return redirect(url_for("panel_gastos"))
        fecha = request.form.get("fecha", "")
        concepto = request.form.get("concepto", "").strip()[:180]
        categoria = request.form.get("categoria", "")
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
            importe = float(request.form.get("importe", ""))
            if not (0 < importe < 100000000000) or categoria not in CATEGORIAS_GASTOS or not concepto:
                raise ValueError
        except (ValueError, TypeError):
            flash("Revisá fecha, concepto, categoría e importe mayor que cero.")
            return redirect(url_for("panel_gastos"))
        if id_gasto and not actual:
            return "Gasto no encontrado", 404
        if actual:
            actual.update(fecha=fecha, concepto=concepto, categoria=categoria, importe=importe)
        else:
            gastos.append(dict(id=secrets.token_hex(8), fecha=fecha, concepto=concepto,
                               categoria=categoria, importe=importe))
        guardar_gastos(gastos)
        flash("Gasto guardado correctamente.")
        return redirect(url_for("panel_gastos"))
    contenido = render_template_string("""
    <div class="box"><h2>{{ '✏️ Modificar gasto' if e else '➕ Registrar gasto' }}</h2>
    <form method="post"><input type="hidden" name="id" value="{{ e.id if e else '' }}">
    <p>Fecha <input type="date" name="fecha" value="{{ e.fecha if e else hoy }}" required></p>
    <p>Concepto <input name="concepto" maxlength="180" value="{{ e.concepto if e else '' }}" required></p>
    <p>Categoría <select name="categoria">{% for c in categorias %}<option value="{{ c }}" {% if e and e.categoria == c %}selected{% endif %}>{{ c }}</option>{% endfor %}</select></p>
    <p>Importe $ <input type="number" min="0.01" step="0.01" name="importe" value="{{ e.importe if e else '' }}" required></p>
    <button>💾 Guardar gasto</button>{% if e %}<a class="button" href="{{ url_for('panel_gastos') }}">Cancelar edición</a>{% endif %}</form></div>
    <div class="box"><h2>Gastos registrados</h2><div class="tablewrap"><table class="table"><tr><th>Fecha</th><th>Concepto</th><th>Categoría</th><th>Importe</th><th>Acciones</th></tr>
    {% for g in gastos %}<tr><td>{{ g.fecha }}</td><td>{{ g.concepto }}</td><td>{{ g.categoria }}</td><td>{{ g.importe|precio }}</td>
    <td><a href="{{ url_for('panel_gastos', editar=g.id) }}">Editar</a>
    <form method="post" style="display:inline" onsubmit="return confirm('¿Eliminar este gasto?')"><input type="hidden" name="accion" value="eliminar"><input type="hidden" name="id" value="{{ g.id }}"><button>Eliminar</button></form></td></tr>
    {% else %}<tr><td colspan="5">Todavía no hay gastos.</td></tr>{% endfor %}</table></div></div>
    """, e=edicion, hoy=date.today().isoformat(), categorias=CATEGORIAS_GASTOS,
        gastos=sorted(gastos, key=lambda x: x.get("fecha", ""), reverse=True))
    return mostrar_panel("💸 Gastos", "Registro manual por categorías", "gastos", contenido)


@app.route("/admin/informe/<formato>")
def descargar_informe(formato):
    if not admin_requerido():
        return redirect(url_for("packs_login"))
    mes = validar_mes(request.args.get("mes", ""))
    if mes is None or formato not in ("pdf", "xlsx"):
        return "Informe inválido", 400
    from flask import send_file
    from datetime import datetime
    datos = resumen_financiero(mes)
    titulo = "Tinta y Alma - Informe " + (mes or "general")
    filas = [("Ventas registradas", datos["ventas_total"]), ("Dinero cobrado", datos["ingresos"]),
             ("Pendiente de cobro", datos["pendiente_total"]), ("Gastos", datos["egresos"]),
             ("Resultado", datos["resultado"])]
    salida = io.BytesIO()
    if formato == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Resumen"
        hoja.append([titulo])
        hoja.append(["Concepto", "Importe ARS"])
        for nombre, importe in filas:
            hoja.append([nombre, importe])
        hoja.append([])
        hoja.append(["Cobros por medio", "Importe ARS"])
        for medio, importe in datos["por_medio"].items():
            hoja.append([medio, importe])
        for fila in hoja:
            for celda in fila:
                if celda.column == 2 and isinstance(celda.value, (float, int)):
                    celda.number_format = '#,##0.00'
        for celda in hoja[2]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="713C5D")
        hoja.column_dimensions["A"].width = 42
        hoja.column_dimensions["B"].width = 20
        hoja2 = libro.create_sheet("Pedidos")
        hoja2.append(["ID", "Fecha", "Cliente", "Medio", "Estado de pago", "Importe ARS"])
        for p in datos["pedidos"]:
            hoja2.append([p.get("id", ""), p.get("creado", ""), p.get("nombre", ""),
                          p.get("medio_pago", ""), p.get("estado_pago", p.get("estado", "")), float(p.get("total") or 0)])
        for col, ancho in zip("ABCDEF", (16, 24, 30, 28, 25, 20)):
            hoja2.column_dimensions[col].width = ancho
        hoja3 = libro.create_sheet("Gastos")
        hoja3.append(["Fecha", "Concepto", "Categoría", "Importe ARS"])
        for g in datos["gastos"]:
            hoja3.append([g.get("fecha"), g.get("concepto"), g.get("categoria"), float(g.get("importe") or 0)])
        for col, ancho in zip("ABCD", (18, 42, 22, 20)):
            hoja3.column_dimensions[col].width = ancho
        libro.save(salida)
        tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.pagesizes import A4
        documento = SimpleDocTemplate(salida, pagesize=A4)
        estilos = getSampleStyleSheet()
        contenido = [Paragraph(titulo, estilos["Title"]), Spacer(1, 18)]
        tabla = Table([["Concepto", "Importe ARS"]] + [[n, precio_formateado(v)] for n, v in filas], colWidths=[300, 140])
        tabla.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#713C5D")),
                                   ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                                   ("GRID", (0,0), (-1,-1), .4, colors.grey),
                                   ("PADDING", (0,0), (-1,-1), 9)]))
        contenido.append(tabla)
        contenido.extend([Spacer(1, 22), Paragraph("Cobros por medio de pago", estilos["Heading2"])])
        for medio, importe in datos["por_medio"].items():
            contenido.append(Paragraph(medio + ": " + precio_formateado(importe), estilos["Normal"]))
        contenido.extend([Spacer(1, 18), Paragraph("Gastos", estilos["Heading2"])])
        for gasto in datos["gastos"]:
            from xml.sax.saxutils import escape
            contenido.append(Paragraph(escape(str(gasto.get("fecha", "")) + " - " + str(gasto.get("concepto", ""))) +
                                      " - " + precio_formateado(gasto.get("importe")), estilos["Normal"]))
        contenido.append(Spacer(1, 16))
        contenido.append(Paragraph("Resultado = cobros confirmados menos gastos registrados. Los cobros se agrupan por fecha del pedido.", estilos["Normal"]))
        documento.build(contenido)
        tipo = "application/pdf"
    salida.seek(0)
    return send_file(salida, mimetype=tipo, as_attachment=True,
                     download_name="tinta_y_alma_informe_{}.{}".format(mes or "general", formato))



# ===================== ENTREGA PRIVADA (PRUEBA LOCAL) =====================
def _buscar_pedido_token(token):
    return next((p for p in cargar_pedidos() if p.get("token_descarga") and secrets.compare_digest(p["token_descarga"], token)), None)


def _vence_pedido(pedido):
    try:
        return datetime.fromisoformat(pedido["descarga_vence_en"])
    except (ValueError, KeyError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


@app.route("/entrega/<token>")
def entrega_pedido(token):
    pedido = _buscar_pedido_token(token)
    if not pedido or pedido.get("estado_pago") != "Pagado":
        abort(404)
    vencido = datetime.now(timezone.utc) >= _vence_pedido(pedido)
    libros = [x for x in pedido.get("productos", []) if x.get("drive_id")]
    return render_template_string("""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Entrega | Tinta y Alma</title><style>body{background:#110e15;color:#fff0f8;font:17px Arial,sans-serif;max-width:750px;margin:50px auto;padding:20px}main{background:#291e2c;border:1px solid #845875;padding:25px;border-radius:20px}h1{color:#f3bdd7}a,button{color:white;background:#a45c82;padding:12px;border-radius:9px;display:inline-block;margin:8px 0;border:0;text-decoration:none;cursor:pointer}</style><main><h1>📚 Tu pedido de Tinta y Alma</h1><p>Pedido {{ p.id }} · {{ p.nombre }}</p>{% if vencido %}<p>⏳ El enlace venció.</p>{% if p.get('renovaciones_usadas',0) < 1 %}<form method="post" action="{{ url_for('renovar_entrega',token=token) }}"><button>🔄 Renovar una vez por 48 horas</button></form>{% else %}<p>La renovación gratuita ya fue utilizada.</p>{% endif %}{% else %}<p>🔐 Descarga disponible hasta {{ p.descarga_vence_en }} (UTC).</p>{% for libro in libros %}<p>📖 {{ libro.nombre }}<br><a href="{{ url_for('descargar_libro',token=token,drive_id=libro.drive_id) }}">📥 DESCARGAR LIBRO PDF</a></p>{% endfor %}{% if not libros %}<p>Este pedido no contiene libros individuales con identificador de descarga. Los packs o pedidos antiguos requieren preparación manual.</p>{% endif %}{% endif %}</main></html>""", p=pedido, token=token, vencido=vencido, libros=libros)


@app.route("/entrega/<token>/renovar", methods=["POST"])
def renovar_entrega(token):
    pedidos = cargar_pedidos()
    pedido = next((p for p in pedidos if p.get("token_descarga") and secrets.compare_digest(p["token_descarga"],token)),None)
    if not pedido or pedido.get("estado_pago") != "Pagado":
        abort(404)
    if pedido.get("renovaciones_usadas",0) >= 1:
        abort(403)
    if datetime.now(timezone.utc) < _vence_pedido(pedido):
        return redirect(url_for("entrega_pedido",token=token))
    pedido["renovaciones_usadas"] = 1
    pedido["descarga_vence_en"] = (datetime.now(timezone.utc)+timedelta(hours=48)).isoformat()
    guardar_pedidos(pedidos)
    return redirect(url_for("entrega_pedido",token=token))


@app.route("/entrega/<token>/pdf/<drive_id>")
def descargar_libro(token,drive_id):
    pedido = _buscar_pedido_token(token)
    if not pedido or pedido.get("estado_pago") != "Pagado" or datetime.now(timezone.utc) >= _vence_pedido(pedido):
        abort(403)
    if not any(p.get("drive_id") == drive_id for p in pedido.get("productos",[])):
        abort(403)
    try:
        servicio = get_drive()
        archivo = servicio.files().get(fileId=drive_id,fields="id,name,mimeType").execute()
        if archivo.get("mimeType") != "application/pdf":
            abort(404)
        contenido = servicio.files().get_media(fileId=drive_id).execute()
        return send_file(io.BytesIO(contenido),mimetype="application/pdf",as_attachment=True,download_name=secure_filename(archivo.get("name","libro.pdf")))
    except Exception:
        abort(502)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
