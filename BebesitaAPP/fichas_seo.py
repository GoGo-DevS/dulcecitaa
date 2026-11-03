"""Textos de busqueda de cada ficha de producto (title, H1, description y un
parrafo propio).

Por que en codigo y no en la base: la descripcion del producto vive en la base
y la escribe la duena desde el panel. Lo que va aca es lo que Google lee para
decidir si muestra la ficha y si alguien la abre, y estaba armado con una
plantilla generica ("Alfajores artesanales, $1352"): sin la palabra que la
gente busca ("alfajores para regalar", "torta de cuchuflis", "barquillo
relleno") y con el precio sin separador de miles.

Ademas cuchuflis banados y cuchuflis rellenos tenian casi la misma
descripcion, y Google las dejo "descubiertas, sin indexar": dos paginas que
dicen lo mismo compiten entre si. Cada una lleva ahora un parrafo propio.

REGLA: cada frase sale de un dato que dulcecita.cl ya publica (la descripcion
de catalogo_inicial, las coberturas, el minimo, Paket, las 48 horas, la cinta
de la torta). Nada de anos, resenas ni plazos inventados. El minimo y las
horas se leen de settings para no quedar desfasados.

Si un producto no esta aca (la duena crea uno nuevo), la ficha usa el armado
generico de siempre: nada se rompe.
"""
from django.conf import settings

TITULO_MAX = 60
DESCRIPCION_MAX = 155


def _pesos(valor):
    return "{:,}".format(int(valor)).replace(",", ".")


def _fichas():
    minimo = getattr(settings, "MINIMO_UNIDADES", 10)
    horas = getattr(settings, "DESPACHO_HORAS", 48)
    return {
        "barquillos-rellenos-banados-en-chocolate": {
            # 03-11-2026: Search Console muestra la ficha para "barquillos
            # rellenos" (pos 19) y "barquillo relleno" (pos 49), y Google sugiere
            # "barquillos rellenos por mayor / santiago / chile / precio". La
            # ficha no decia ni Santiago, ni por mayor, ni cuanto cuestan.
            "ancla": "Barquillos rellenos",
            "pregunta_precio": "¿Cuánto cuestan los barquillos rellenos?",
            "titulo": "Barquillos rellenos de manjar",
            "h1": "Barquillos rellenos bañados en chocolate",
            "descripcion": (
                "Barquillos crujientes rellenos de manjar y bañados en chocolate o chocolate "
                f"blanco en sus puntas. Desde {minimo} unidades, despacho a todo Chile."),
            "parrafos": [
                "Barquillos crujientes rellenos de manjar cremoso y bañados en chocolate "
                "solo en los extremos. Eliges la cobertura al pedir: chocolate o chocolate "
                "blanco.",
                f"Se venden desde {minimo} unidades por producto. Si quieres mezclarlos con "
                "alfajores o cuchuflís, en Arma tu box combinas los que quieras en una sola caja.",
                f"Barquillos rellenos hechos a mano en Santiago: en la ciudad la entrega se "
                f"coordina por WhatsApp y a regiones van por Paket. Por mayor, desde "
                f"{POR_MAYOR_DESDE} unidades al mismo precio por unidad.",
            ],
        },
        "alfajores": {
            # 02-11-2026: "alfajores artesanales" es la variante con mas
            # sugerencias de Google (por mayor, precio, chile, santiago, premium,
            # para regalar) y Search Console ya la muestra aqui (pos 35, y
            # "alfajor artesanal" pos 41). El H1 la tenia; el title no.
            "ancla": "Alfajores artesanales",
            # 03-11-2026: "alfajores artesanales precio" y "alfajores navideños
            # precio" estan en el autocompletado; el precio se lee de la base.
            "pregunta_precio": "¿Cuánto cuesta un alfajor artesanal?",
            "titulo": "Alfajores artesanales para regalar",
            "h1": "Alfajores artesanales para regalar",
            "descripcion": (
                "Alfajores de triple capa con manjar y cobertura de chocolate o chocolate "
                f"blanco, ideales para regalar. Desde {minimo} unidades o en tu propio box."),
            "parrafos": [
                "Un alfajor de triple capa: galletas suaves, relleno cremoso de manjar y la "
                "cobertura que elijas, chocolate o chocolate blanco.",
                "Para un regalo puedes armar tu propio box mezclando alfajores con barquillos "
                "y cuchuflís. Si es para una empresa o un evento, lo cotizamos en venta "
                "corporativa.",
                # 19-10-2026: "alfajores artesanales chile / precio / por mayor" son
                # las busquedas con mas variantes del rubro; la ficha no decia ni
                # "Chile" ni "por mayor".
                f"Alfajores artesanales hechos en Santiago de Chile, con despacho a todo el "
                f"país. El precio es por unidad y se vende desde {minimo}; por mayor, desde "
                f"{POR_MAYOR_DESDE} unidades.",
            ],
        },
        "cuchuflis-banados": {
            # 03-11-2026: "cuchuflis bañados en chocolate" llega en pos 42 y Google
            # sugiere "... por mayor", "... precio" y "caja de cuchuflis bañados".
            "ancla": "Cuchuflís bañados en chocolate",
            "pregunta_precio": "¿Cuánto cuestan los cuchuflís bañados en chocolate?",
            "titulo": "Cuchuflís bañados en chocolate",
            "h1": "Cuchuflís bañados en chocolate",
            "descripcion": (
                "Cuchuflís rellenos de manjar y bañados enteros en chocolate o chocolate "
                "blanco, en bolsita de 4. Despacho a todo Chile por Paket."),
            "parrafos": [
                "A diferencia de los cuchuflís rellenos, que van sin cobertura, estos se "
                "bañan enteros en chocolate. Eliges la cobertura al pedir: chocolate o "
                "chocolate blanco.",
                "Vienen en bolsita de 4 unidades, y también puedes sumarlos a tu box. "
                f"Tu pedido sale {horas} horas después del pago.",
                "Cuchuflís bañados en chocolate hechos a mano en Santiago, con entrega "
                "coordinada por WhatsApp en la ciudad y despacho a regiones por Paket. "
                "Para un evento o un regalo por cantidad, también se venden por mayor al "
                "mismo precio del catálogo.",
            ],
        },
        "cuchuflis-rellenos": {
            "ancla": "Cuchuflís rellenos de manjar",
            # 03-11-2026: Google sugiere "cuchuflis rellenos por mayor" y
            # "cuchuflis con manjar por mayor"; el precio se lee de la base.
            "pregunta_precio": "¿Cuánto cuestan los cuchuflís rellenos?",
            "titulo": "Cuchuflís rellenos de manjar",
            "h1": "Cuchuflís rellenos de manjar",
            "descripcion": (
                "Cuchuflís crujientes rellenos de manjar, sin baño de chocolate, en bolsita "
                "de 4. La base de nuestra torta de cuchuflís. Despacho a todo Chile."),
            "parrafos": [
                "Cuchuflís crujientes rellenos de manjar y sin cobertura. Por eso cuestan "
                "menos que los bañados y no llevan chocolate a elegir.",
                "La torta de cuchuflís se arma con cuchuflís rellenos de manjar como estos. "
                "Vienen en bolsita de 4 unidades y se despachan a todo Chile por Paket.",
                "Se hacen a mano en Santiago, donde la entrega se coordina por WhatsApp, y "
                "también se venden por mayor al mismo precio del catálogo.",
            ],
        },
        "torta-de-cuchuflis": {
            "ancla": "Torta de cuchuflís",
            # 02-11-2026: Google sugiere "cuanto vale una torta de cuchuflis",
            # "valor torta de cuchufli" y "torta 50 cuchuflis", y la compiten
            # Jumbo, Tottus, Unimarc y Lider. La respuesta va en las preguntas
            # de la ficha con los precios de la BASE (ver _texto_precios).
            "pregunta_precio": "¿Cuánto vale una torta de cuchuflís?",
            "titulo": "Torta de cuchuflís decorada",
            "h1": "Torta de cuchuflís",
            "descripcion": (
                "Torta de cuchuflís rellenos de manjar, de 50 o 100 unidades, sin cobertura o "
                "bañados en chocolate. Con cinta y decoración en tus colores."),
            # 19-10-2026: Google muestra esta ficha para "torta de cuchufli para
            # niños", "50 unidades", "donde comprar" y "precio". Cada frase
            # responde una de esas, con lo que la ficha ya vende.
            "parrafos": [
                "La torta se arma con cuchuflís rellenos de manjar, en 50 o 100 unidades. "
                "Puedes pedirla sin cobertura o con los cuchuflís bañados en chocolate o "
                "chocolate blanco.",
                "Va terminada con cinta y decoración: al hacer el pedido nos cuentas los "
                "colores que quieres. Se vende desde una torta.",
                "Es la clásica de los cumpleaños infantiles y también se pide para "
                "celebraciones de oficina: con la cinta en los colores del homenajeado o "
                "de la empresa, llega lista para la mesa.",
                "El precio depende del tamaño (50 o 100 cuchuflís) y de si van bañados: lo "
                "ves arriba al elegir. Se compra aquí mismo, se despacha a todo Chile por "
                f"Paket y en Santiago se coordina la entrega por WhatsApp, {horas} horas "
                "después del pago.",
            ],
        },
    }


def ficha(producto):
    """El dict de la ficha, o None si el producto no tiene textos propios."""
    return _fichas().get(producto.slug or "")


def titulo(producto, marca=None):
    """Title de la ficha, siempre de 60 caracteres o menos.

    Con precio si cabe ("desde $1.352"): en el resultado de Google el precio
    responde la primera pregunta antes del clic. Si no cabe, se cae el precio,
    nunca la palabra clave.
    """
    marca = marca or settings.BRAND_NAME
    datos = ficha(producto)
    base = datos["titulo"] if datos else f"{producto.nombre} artesanales"
    precio = _pesos(producto.precio_desde())
    for candidato in (f"{base} desde ${precio} | {marca}", f"{base} | {marca}"):
        if len(candidato) <= TITULO_MAX:
            return candidato
    return f"{base} | {marca}"[:TITULO_MAX]


def h1(producto):
    datos = ficha(producto)
    return datos["h1"] if datos else producto.nombre


def ancla(producto):
    """Texto del enlace hacia la ficha desde el resto del sitio.

    03-11-2026: el pie de TODAS las paginas enlazaba con el nombre interno del
    producto ("Cuchuflís bañados", "Alfajores"), que no es la frase que se
    busca. Con la palabra de la ficha ("Cuchuflís bañados en chocolate",
    "Alfajores artesanales") cada enlace interno le dice a Google de que trata
    la pagina de destino. Sin ficha propia, el nombre de siempre.
    """
    datos = ficha(producto)
    return (datos or {}).get("ancla") or producto.nombre


def descripcion(producto):
    """Meta description de 155 caracteres o menos, cortada en una palabra."""
    from django.utils.html import strip_tags

    datos = ficha(producto)
    texto = datos["descripcion"] if datos else " ".join(strip_tags(producto.descripcion or "").split())
    if not texto:
        texto = f"{producto.nombre} hechos a mano por {settings.BRAND_NAME}. Despacho a todo Chile."
    if len(texto) <= DESCRIPCION_MAX:
        return texto
    corte = texto[:DESCRIPCION_MAX - 1].rsplit(" ", 1)[0].rstrip(",.;:")
    return corte + "…"


def parrafos(producto):
    datos = ficha(producto)
    return datos["parrafos"] if datos else []


# Respuestas de la duena (16-10-2026, por WhatsApp a Diego). Son las preguntas
# que la gente hace antes de comprar dulces para regalar o por mayor, y ninguna
# ficha las respondia. Van en TODAS las fichas, despues de las que ella cargue
# en el panel para ese producto.
POR_MAYOR_DESDE = 20
PREGUNTAS_COMUNES = [
    ("¿Cuánto duran y cómo se guardan?",
     "Duran aproximadamente un mes, guardados en un ambiente fresco y seco."),
    ("¿Se pueden personalizar?",
     "Sí. Se pueden personalizar para regalos y eventos: cuéntanos qué necesitas al hacer "
     "el pedido."),
    ("¿Venden por mayor?",
     f"Sí, desde {POR_MAYOR_DESDE} unidades. Si es para una empresa o un evento, también lo "
     "cotizamos en venta corporativa."),
]


class _Pregunta:
    def __init__(self, pregunta, respuesta):
        self.pregunta, self.respuesta = pregunta, respuesta


def _norma(texto):
    import unicodedata
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return "".join(c for c in t if c.isalnum())


MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")


def _texto_precios(producto):
    """Los precios de cada combinacion en una frase, con el precio que se COBRA.

    "50 cuchuflís: sin cobertura, $14.990; chocolate o chocolate blanco, $17.990."
    Agrupa por la primera opcion (el tamaño) y junta con "o" las que cuestan lo
    mismo.

    Cada precio sale de precio_para(), el mismo camino del carrito, el checkout
    y el pedido: si la duena cambia un precio en el panel o corre una
    promocion, la respuesta cambia sola. Escribir los precios a mano aqui seria
    publicar un numero que un dia deja de ser el que se cobra, y un precio
    publicado mal es el error mas caro de una tienda.
    """
    import itertools
    from .models import Promocion

    grupos = [opciones for _, _, opciones in producto.grupos_opciones()]
    if len(grupos) <= 1:
        texto = _texto_precio_simple(producto, grupos[0] if grupos else [])
    else:
        frases = []
        for primera in grupos[0]:
            por_precio = {}  # precio -> nombres, en el orden en que se eligen
            for resto in itertools.product(*grupos[1:]):
                precio = producto.precio_para([primera.id] + [o.id for o in resto])
                por_precio.setdefault(precio, []).append(" ".join(o.nombre for o in resto).lower())
            partes = [f"{' o '.join(n for n in nombres if n)}, ${_pesos(precio)}" if any(nombres)
                      else f"${_pesos(precio)}" for precio, nombres in por_precio.items()]
            frases.append(f"{primera.nombre}: {'; '.join(partes)}.")
        texto = " ".join(frases)
    promo = Promocion.vigente()
    if promo:
        texto += (f" Precios con {promo.porcentaje}% de descuento hasta el "
                  f"{promo.hasta.day} de {MESES[promo.hasta.month - 1]}.")
    return texto


def unidad_de_venta(producto):
    """A que corresponde el precio: "por unidad" o "la bolsita de 4"."""
    if producto.unidades_por_pack > 1:
        return f"la bolsita de {producto.unidades_por_pack}"
    return "por unidad"


def _texto_precio_simple(producto, opciones):
    """Precio de un producto con un solo grupo de opciones (la cobertura) o sin opciones.

    "$1.290 por unidad, con chocolate o chocolate blanco."
    "$1.590 la bolsita de 4, con chocolate o chocolate blanco."
    "$1.190 la bolsita de 4."
    Si una cobertura costara distinto, cada precio va con la suya. La unidad
    sale de unidades_por_pack: el precio de los cuchuflis es por bolsita.
    """
    unidad = unidad_de_venta(producto)
    if not opciones:
        return f"${_pesos(producto.precio_para([]))} {unidad}."
    por_precio = {}
    for op in opciones:
        por_precio.setdefault(producto.precio_para([op.id]), []).append(op.nombre.lower())
    partes = [f"${_pesos(precio)} {unidad if i == 0 else ''}".rstrip() + f", con {' o '.join(nombres)}"
              for i, (precio, nombres) in enumerate(por_precio.items())]
    return "; ".join(partes) + "."


def pregunta_precio(producto):
    """La pregunta del precio con los precios de la base, o None si la ficha no la pide."""
    datos = ficha(producto)
    if not datos or not datos.get("pregunta_precio"):
        return None
    return _Pregunta(datos["pregunta_precio"], _texto_precios(producto))


def preguntas(producto, limite=8):
    """Las de la duena para este producto, la del precio y las comunes, sin repetir.

    UNA sola lista para la pagina y para el FAQPage del schema: lo que se
    declara es exactamente lo que se ve.
    """
    propias = list(producto.preguntas.filter(activa=True)[:limite])
    vistas = {_norma(p.pregunta) for p in propias}
    precio = pregunta_precio(producto)
    generadas = [precio] if precio and _norma(precio.pregunta) not in vistas else []
    comunes = [_Pregunta(p, r) for p, r in PREGUNTAS_COMUNES if _norma(p) not in vistas]
    return (propias + generadas + comunes)[:limite]
