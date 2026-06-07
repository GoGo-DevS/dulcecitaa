"""Protege toda la app de gestión (/panel/) con login.

En vez de decorar vista por vista, exige usuario autenticado para cualquier
ruta bajo el prefijo de gestión, salvo el propio login/logout. Así cualquier
vista nueva queda protegida automáticamente.
"""

from django.shortcuts import redirect
from django.urls import reverse


class GestionLoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Se resuelven una vez; reverse necesita el resolver listo, así que
        # se calculan de forma perezosa en la primera request.
        self._login_url = None
        self._logout_url = None

    def _urls(self):
        if self._login_url is None:
            self._login_url = reverse("gestion:login")
            self._logout_url = reverse("gestion:logout")
        return self._login_url, self._logout_url

    def __call__(self, request):
        login_url, logout_url = self._urls()
        path = request.path

        # Solo nos importa el área de gestión (mismo prefijo que el login).
        prefijo = login_url.rsplit("login/", 1)[0]  # ej: "/panel/"
        if path.startswith(prefijo) and not path.startswith((login_url, logout_url)):
            if not request.user.is_authenticated:
                return redirect(f"{login_url}?next={path}")

        return self.get_response(request)
