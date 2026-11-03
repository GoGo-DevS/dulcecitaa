"""Temporada de Navidad: cuando el sitio empuja /navidad/ desde el menu y la portada.

03-11-2026: la pagina /navidad/ queda publicada todo el año (una URL que vuelve
cada diciembre gana antiguedad), pero el enlace del menu y el aviso de la
portada solo tienen sentido mientras la gente esta comprando regalos. Se
encienden el 1 de noviembre y se apagan solos despues del 25 de diciembre: nadie
tiene que acordarse de sacarlos en enero.
"""
from django.utils import timezone


def es_navidad(hoy=None):
    hoy = hoy or timezone.localdate()
    return hoy.month == 11 or (hoy.month == 12 and hoy.day <= 25)
