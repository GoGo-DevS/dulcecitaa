"""Temporada de Navidad: cuando el sitio empuja /navidad/ desde el menu y la portada.

03-11-2026: la pagina /navidad/ queda publicada todo el año (una URL que vuelve
cada diciembre gana antiguedad), pero el enlace del menu y el aviso de la
portada solo tienen sentido mientras la gente esta comprando regalos. Se
encienden el 1 de noviembre y se apagan solos despues del 25 de diciembre: nadie
tiene que acordarse de sacarlos en enero.

11-11-2026: la oferta de CADA Navidad (lo que la duena confirmo para ese año)
vive aca, en un solo lugar, y se apaga sola despues del 25 de diciembre. Asi el
pan de pascua de $8.590 no sigue publicado en 2027 con el precio viejo: un año
sin entrada en OFERTAS_NAVIDAD muestra la pagina generica.
"""
import datetime

from django.utils import timezone

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")

# Audios de Tamara (duena) del 11-11-2026, respondiendo lo que quedo preguntado
# el 03-11:
#   - box navideño: SI, a pedido, igual que el Arma tu box (box + empaque), con
#     cinta y tarjeta navideña y sin eleccion de color.
#   - pan de pascua: solo medio kilo, $8.590, desde el 20 de noviembre. (El audio
#     se transcribio "8.500"; Tamara lo corrigio por WhatsApp el 11-11 a las 16:19:
#     "el precio del pan de pascua pone 8.590".)
#   - pedidos de Navidad: hasta el 20 (de diciembre: se le pregunto por entregar
#     antes del 24, y el pan recien parte el 20 de noviembre).
# Lo que NO dijo (no se publica): cupos, precio por cantidad del pan, despacho
# del pan distinto al de los dulces, cuanto dura el pan.
OFERTAS_NAVIDAD = {
    2026: {
        "pedidos_hasta": datetime.date(2026, 12, 20),
        "pan_de_pascua": {
            "formato": "medio kilo",
            "precio": 8590,
            "desde": datetime.date(2026, 11, 20),
        },
    },
}


def _hoy():
    return timezone.localdate()


def es_navidad(hoy=None):
    hoy = hoy or timezone.localdate()
    return hoy.month == 11 or (hoy.month == 12 and hoy.day <= 25)


def fecha_larga(fecha):
    """'20 de diciembre', sin depender del locale del servidor."""
    return f"{fecha.day} de {MESES[fecha.month - 1]}"


def oferta_navidad(hoy=None):
    """La oferta confirmada de esta Navidad, o None.

    None fuera de temporada (26-12 a 31-10) y en un año sin oferta cargada: la
    pagina vuelve a mostrar solo lo que se vende todo el año.
    """
    hoy = hoy or _hoy()
    oferta = OFERTAS_NAVIDAD.get(hoy.year)
    if not oferta or not es_navidad(hoy):
        return None
    pan = oferta["pan_de_pascua"]
    return {
        "pedidos_hasta": oferta["pedidos_hasta"],
        "pedidos_hasta_texto": fecha_larga(oferta["pedidos_hasta"]),
        "cerrado": hoy > oferta["pedidos_hasta"],
        "pan": {**pan, "desde_texto": fecha_larga(pan["desde"])},
    }
