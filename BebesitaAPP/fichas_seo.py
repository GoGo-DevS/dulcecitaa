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
            ],
        },
        "alfajores": {
            "titulo": "Alfajores para regalar",
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
            ],
        },
        "cuchuflis-banados": {
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
            ],
        },
        "cuchuflis-rellenos": {
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
            ],
        },
        "torta-de-cuchuflis": {
            "titulo": "Torta de cuchuflís decorada",
            "h1": "Torta de cuchuflís",
            "descripcion": (
                "Torta de cuchuflís rellenos de manjar, de 50 o 100 unidades, sin cobertura o "
                "bañados en chocolate. Con cinta y decoración en tus colores."),
            "parrafos": [
                "La torta se arma con cuchuflís rellenos de manjar, en 50 o 100 unidades. "
                "Puedes pedirla sin cobertura o con los cuchuflís bañados en chocolate o "
                "chocolate blanco.",
                "Va terminada con cinta y decoración: al hacer el pedido nos cuentas los "
                "colores que quieres. Se vende desde una torta.",
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
