"""Textos de busqueda de las fichas, disponibles en las plantillas."""
from django import template

from .. import fichas_seo

register = template.Library()


@register.filter
def ancla(producto):
    """{{ p|ancla }} -> "Cuchuflís bañados en chocolate" (o el nombre si no tiene ficha)."""
    return fichas_seo.ancla(producto)
