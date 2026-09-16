"""Crea o actualiza el usuario de /panel desde variables de entorno.

Por que existe: la clave del panel se guarda encriptada, asi que no hay forma de
"verla" ni de recuperarla; solo se puede reemplazar. Y en el plan Free de Render
no hay consola para correr `changepassword`. Esto corre en el build del deploy y
solo hace algo si estan PANEL_USER y PANEL_PASSWORD; si faltan, no toca nada y
el deploy sigue igual.

Uso (15-09-2026): poner las dos variables en Render, desplegar, entrar al panel
y despues BORRAR PANEL_PASSWORD del dashboard. La clave no se escribe nunca en
la salida del comando ni en el repositorio.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea o actualiza el usuario del panel con PANEL_USER y PANEL_PASSWORD."

    def handle(self, *args, **options):
        usuario = (os.environ.get("PANEL_USER") or "").strip()
        clave = os.environ.get("PANEL_PASSWORD") or ""
        if not usuario or not clave:
            self.stdout.write("PANEL_USER/PANEL_PASSWORD no estan: no se toca ningun usuario.")
            return

        Usuario = get_user_model()
        cuenta, creada = Usuario.objects.get_or_create(
            **{Usuario.USERNAME_FIELD: usuario},
            defaults={"is_staff": True, "is_superuser": True},
        )
        cuenta.set_password(clave)
        # Un usuario que no es staff no puede entrar al admin de Django, que es
        # donde la duena revisa los pedidos web.
        cuenta.is_staff = True
        cuenta.is_superuser = True
        cuenta.is_active = True
        cuenta.save()
        self.stdout.write(self.style.SUCCESS(
            f"Usuario del panel {'creado' if creada else 'actualizado'}: {usuario} "
            "(acuerdate de borrar PANEL_PASSWORD del dashboard)."))
