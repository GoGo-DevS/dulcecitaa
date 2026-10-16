"""Memoria que dura UNA visita.

16-10-2026: Promocion.vigente() se consultaba una vez por cada precio dibujado
(la portada hacia 102 consultas y tardaba 3-4 s con la base en Neon). Con esto
se consulta una vez por visita y se olvida al terminarla: no hay cache
compartida entre visitas ni entre procesos, asi que una promocion guardada en
el panel se ve en la visita siguiente, como antes.
"""
from .models import _MEMORIA_VISITA


class MemoriaPorVisita:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _MEMORIA_VISITA.set({})
        try:
            return self.get_response(request)
        finally:
            _MEMORIA_VISITA.reset(token)
