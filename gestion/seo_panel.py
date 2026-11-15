"""Como sale cada pagina de dulcecita.cl en Google, para el panel (15-11-2026).

La duena no tiene por que abrir Search Console para saber si una ficha esta
bien presentada. Esta pantalla arma, para cada pagina publica, lo mismo que
Google muestra en el resultado (titulo, direccion y descripcion) y revisa lo
que se puede medir sin salir del sitio.

Como se hace: cada pagina se ARMA de verdad, llamando a su vista como si la
pidiera un visitante sin carrito, y se lee el HTML que saldria. No se copia el
titulo de una tabla: si mañana una plantilla cambia, esta pantalla lo refleja.
Por eso hace varias consultas (las de cada pagina publica); es una revision
que se abre de vez en cuando, no una pantalla de trabajo diario.

Lo que NO esta aca: clics, impresiones y posicion. Esos numeros solo los tiene
Google (Search Console); la pantalla enlaza al informe.
"""
import html as html_lib
import json
import re
from importlib import import_module
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.shortcuts import render
from django.urls import resolve, reverse
from django.utils.html import strip_tags

from BebesitaAPP import fichas_seo
from BebesitaAPP.models import Producto

TITULO_MAX = 60
DESCRIPCION_MAX = 155
DESCRIPCION_MIN = 70
DESCRIPCION_PRODUCTO_MIN = 80

# (nombre para la duena, nombre de la ruta). Las mismas del sitemap.
PAGINAS_FIJAS = [
    ("Portada", "home"),
    ("Catálogo", "productos"),
    ("Navidad", "navidad"),
    ("Arma tu box", "arma_tu_box"),
    ("Venta corporativa", "corporativo"),
    ("Delivery y retiro", "delivery"),
    ("Contacto", "contacto"),
]

TU = "tu"          # lo arregla la duena desde Productos
DIEGO = "diego"    # vive en el codigo del sitio


def _pedir(ruta, pedido):
    """El HTML de una pagina publica, como lo recibe un visitante nuevo.

    Se llama a la vista directamente, con un pedido armado a mano: anonimo y
    con una sesion vacia que nunca se guarda. No pasa por la red ni cuenta
    como visita en ninguna medicion.
    """
    falso = HttpRequest()
    falso.method = "GET"
    falso.path = falso.path_info = ruta
    falso.META = {clave: pedido.META[clave] for clave in
                  ("SERVER_NAME", "SERVER_PORT", "HTTP_HOST", "wsgi.url_scheme", "HTTP_X_FORWARDED_PROTO")
                  if clave in pedido.META}
    falso.META.update({"REQUEST_METHOD": "GET", "PATH_INFO": ruta, "QUERY_STRING": ""})
    falso.user = AnonymousUser()
    falso.session = import_module(settings.SESSION_ENGINE).SessionStore()
    destino = resolve(ruta)
    respuesta = destino.func(falso, *destino.args, **destino.kwargs)
    if hasattr(respuesta, "render") and callable(respuesta.render):
        respuesta = respuesta.render()
    if respuesta.status_code != 200:
        raise ValueError(f"respondió {respuesta.status_code}")
    return respuesta.content.decode("utf-8", errors="replace")


def _limpio(texto):
    return " ".join(html_lib.unescape(strip_tags(texto or "")).split())


def leer(html):
    """Lo que Google lee de una pagina: titulo, descripcion, H1, canonica y datos estructurados."""
    titulo = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    descripcion = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html, re.I)
    canonica = re.search(r'<link\s+rel="canonical"\s+href="([^"]*)"', html, re.I)
    robots = re.search(r'<meta\s+name="robots"\s+content="([^"]*)"', html, re.I)
    tipos = set()
    for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            dato = json.loads(bloque)
        except ValueError:
            continue
        for nodo in (dato.get("@graph", [dato]) if isinstance(dato, dict) else dato):
            if isinstance(nodo, dict) and nodo.get("@type"):
                tipos.add(nodo["@type"])
    return {
        "titulo": _limpio(titulo.group(1)) if titulo else "",
        "descripcion": html_lib.unescape(descripcion.group(1)).strip() if descripcion else "",
        "h1": [_limpio(h) for h in re.findall(r"<h1\b[^>]*>(.*?)</h1>", html, re.S | re.I)],
        "canonica": canonica.group(1) if canonica else "",
        "noindex": bool(robots and "noindex" in robots.group(1).lower()),
        "tipos": tipos,
    }


def _aviso(texto, quien):
    return {"texto": texto, "quien": quien}


def revisar_pagina(datos, url, quien_textos=DIEGO, espera_producto=False):
    """Los avisos de una pagina a partir de lo leido. Lista vacia = esta lista."""
    avisos = []
    largo_titulo = len(datos["titulo"])
    if not datos["titulo"]:
        avisos.append(_aviso("No tiene título.", DIEGO))
    elif largo_titulo > TITULO_MAX:
        avisos.append(_aviso(f"El título tiene {largo_titulo} caracteres: Google muestra unos {TITULO_MAX} "
                             "y corta el resto.", DIEGO))
    largo_desc = len(datos["descripcion"])
    if not datos["descripcion"]:
        avisos.append(_aviso("No tiene descripción: Google arma una con un trozo cualquiera de la página.",
                             quien_textos))
    elif largo_desc > DESCRIPCION_MAX:
        avisos.append(_aviso(f"La descripción tiene {largo_desc} caracteres: Google corta después de "
                             f"{DESCRIPCION_MAX}.", quien_textos))
    elif largo_desc < DESCRIPCION_MIN:
        avisos.append(_aviso(f"La descripción es corta ({largo_desc} caracteres): hay espacio para decir "
                             "más de lo que vendes.", quien_textos))
    if len(datos["h1"]) != 1:
        cuantos = len(datos["h1"])
        avisos.append(_aviso("No tiene un título principal dentro de la página." if not cuantos
                             else f"Tiene {cuantos} títulos principales; debería ser uno.", DIEGO))
    if datos["canonica"] != url:
        avisos.append(_aviso("La dirección oficial que declara no es la suya.", DIEGO))
    if datos["noindex"]:
        avisos.append(_aviso("Le pide a Google que NO la muestre (noindex).", DIEGO))
    if espera_producto and "Product" not in datos["tipos"]:
        avisos.append(_aviso("No le declara a Google el producto ni su precio.", DIEGO))
    return avisos


def revisar_producto(producto):
    """Avisos de la ficha que la duena arregla sola, desde Productos."""
    avisos = []
    if not producto.imagen:
        avisos.append(_aviso("No tiene foto.", TU))
    largo = len(_limpio(producto.descripcion))
    if largo < DESCRIPCION_PRODUCTO_MIN:
        avisos.append(_aviso(f"La descripción del producto es corta ({largo} letras). Cuenta de qué es, "
                             "cómo se vende y para qué ocasión sirve.", TU))
    if not producto.disponible:
        avisos.append(_aviso("Está marcado como no disponible: Google lo muestra «agotado».", TU))
    if not fichas_seo.ficha(producto):
        avisos.append(_aviso("Usa el título genérico. Avísale a Diego para escribirle uno con las palabras "
                             "que la gente busca.", DIEGO))
    return avisos


def _herramientas(url):
    return {
        "google": f"https://search.google.com/test/rich-results?url={quote(url, safe='')}",
        "velocidad": f"https://pagespeed.web.dev/analysis?url={quote(url, safe='')}",
    }


def auditar(pedido):
    """Todas las paginas publicas, cada una con su vista previa de Google y sus avisos."""
    sitio = settings.SITE_URL
    paginas = []

    def agregar(nombre, ruta, producto=None):
        url = sitio + ruta
        fila = {"nombre": nombre, "ruta": ruta, "url": url, "producto": producto,
                "herramientas": _herramientas(url), "avisos": [], "error": ""}
        try:
            datos = leer(_pedir(ruta, pedido))
        except Exception as error:  # noqa: BLE001 - una pagina rota no puede tumbar el panel
            fila["error"] = f"No se pudo revisar ({error})."
            fila["avisos"] = [_aviso("La página no cargó al revisarla. Avísale a Diego.", DIEGO)]
            paginas.append(fila)
            return
        tiene_ficha = bool(producto and fichas_seo.ficha(producto))
        fila.update(titulo=datos["titulo"], descripcion=datos["descripcion"],
                    largo_titulo=len(datos["titulo"]), largo_descripcion=len(datos["descripcion"]))
        # Sin textos propios, la descripcion de la ficha sale de la del producto: la escribe la duena.
        quien = TU if producto and not tiene_ficha else DIEGO
        fila["avisos"] = revisar_pagina(datos, url, quien_textos=quien, espera_producto=bool(producto))
        if producto:
            fila["avisos"] += revisar_producto(producto)
        paginas.append(fila)

    for nombre, nombre_ruta in PAGINAS_FIJAS:
        agregar(nombre, reverse(nombre_ruta))
    productos = (Producto.objects.filter(visible=True, variante_de__isnull=True)
                 .prefetch_related("opciones", "precios_combinacion").order_by("orden", "nombre"))
    for producto in productos:
        agregar(producto.nombre, producto.get_absolute_url(), producto)

    for fila in paginas:
        fila["lista"] = not fila["avisos"]
        fila["para_ti"] = [a for a in fila["avisos"] if a["quien"] == TU]
        fila["para_diego"] = [a for a in fila["avisos"] if a["quien"] == DIEGO]
    return paginas


def seo(request):
    paginas = auditar(request)
    dominio = settings.SITE_URL.split("://", 1)[-1]
    propiedad = quote(f"sc-domain:{dominio}", safe="")
    return render(request, "gestion/seo.html", {
        "paginas": paginas,
        "listas": sum(1 for p in paginas if p["lista"]),
        "total": len(paginas),
        "pendientes_tuyos": sum(len(p["para_ti"]) for p in paginas),
        "pendientes_diego": sum(len(p["para_diego"]) for p in paginas),
        "titulo_max": TITULO_MAX,
        "descripcion_max": DESCRIPCION_MAX,
        "sitio": settings.SITE_URL,
        "enlaces": [
            {"nombre": "Qué buscan para encontrarte", "para": "Búsquedas, clics y posición en Google (Search Console)",
             "url": f"https://search.google.com/search-console/performance/search-analytics?resource_id={propiedad}"},
            {"nombre": "Qué páginas conoce Google", "para": "Cuáles están en el buscador y cuáles todavía no",
             "url": f"https://search.google.com/search-console/index?resource_id={propiedad}"},
            {"nombre": "Mapa del sitio", "para": "La lista de páginas que el sitio le entrega a Google",
             "url": f"{settings.SITE_URL}/sitemap.xml"},
        ],
    })
