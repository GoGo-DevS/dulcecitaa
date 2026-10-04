"""Formato de precios en pesos chilenos.

Por que no `intcomma` de humanize: con LANGUAGE_CODE "es-cl" agrupa con un
ESPACIO DURO (12 900), que no es el formato chileno y en pantalla se lee
como un numero cortado. Aca el separador se escribe explicito.
"""
from django import template

register = template.Library()


@register.filter
def pesos(valor):
    """12900 -> "12.900". Lo que no sea un numero vuelve tal cual."""
    if valor is None or valor == "":
        return ""
    try:
        entero = int(round(float(valor)))
    except (TypeError, ValueError):
        return valor
    signo = "-" if entero < 0 else ""
    return signo + "{:,}".format(abs(entero)).replace(",", ".")
