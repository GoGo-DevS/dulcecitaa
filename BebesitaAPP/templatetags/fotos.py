"""Sirve las fotos de producto en el tamano y formato que corresponde.

Las fotos de producto viven en Cloudinary y se subian SIN procesar: PNG de 2 a
3 MB generados con ChatGPT, servidos completos en tarjetas de 300 px. Eso se
paga dos veces, en el ranking (LCP) y en la cuota de Cloudinary, que ya se paso
del cupo dos veces y el 20-08-2026 dejo a otro cliente sin una sola foto.

La transformacion va en la URL, no en el archivo: no hay que re-subir nada, no
se pierde el original, y el dia que se quiera otro tamano se cambia un numero.

Fuera de Cloudinary (disco local en desarrollo) devuelve la URL tal cual, para
que el sitio se comporte igual en las dos partes.
"""
from django import template

register = template.Library()

# Insertar despues de este segmento es lo que Cloudinary entiende como
# "aplicame estas transformaciones".
MARCA = "/image/upload/"

# f_auto  -> WebP o AVIF segun lo que soporte el navegador que pide
# q_auto  -> calidad que Cloudinary considera indistinguible a ojo
PREFIJO = "f_auto,q_auto"


@register.filter
def foto(url, ancho=800):
    """{{ p.imagen.url|foto:600 }} -> la misma foto, servida a 600 px de ancho."""
    if not url:
        return ""
    url = str(url)
    if MARCA not in url:
        return url  # disco local, o un storage que no es Cloudinary

    cabeza, cola = url.split(MARCA, 1)

    # Si alguien ya dejo transformaciones puestas, no se pisan: Cloudinary
    # aplicaria las dos y el resultado deja de ser predecible.
    if cola.split("/", 1)[0].startswith(("f_", "q_", "w_", "c_", "t_")):
        return url

    try:
        ancho = int(ancho)
    except (TypeError, ValueError):
        ancho = 800

    return f"{cabeza}{MARCA}{PREFIJO},w_{ancho}/{cola}"
