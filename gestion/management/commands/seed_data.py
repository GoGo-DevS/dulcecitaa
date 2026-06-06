from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connection

from BebesitaAPP.models import Producto


class Command(BaseCommand):
    help = "Carga datadump.json en la base SOLO si está vacía (idempotente, seguro en cada deploy)."

    def handle(self, *args, **options):
        if Producto.objects.exists():
            self.stdout.write("Ya existen productos: se omite la carga de datos (seed).")
            return

        fixture = Path(settings.BASE_DIR) / "datadump.json"
        if not fixture.exists():
            self.stdout.write(self.style.WARNING(f"No se encontró {fixture}, nada que cargar."))
            return

        self.stdout.write("Base vacía: cargando datadump.json…")
        call_command("loaddata", str(fixture))

        # Reset de secuencias (Postgres): evita choques de ID al crear nuevos registros
        self._reset_sequences()

        self.stdout.write(self.style.SUCCESS(
            f"Datos cargados: {Producto.objects.count()} productos."
        ))

    def _reset_sequences(self):
        models = [m for app in ("BebesitaAPP", "gestion", "auth") for m in apps.get_app_config(app).get_models()]
        sql_list = connection.ops.sequence_reset_sql(no_style(), models)
        if not sql_list:
            return
        with connection.cursor() as cursor:
            for sql in sql_list:
                cursor.execute(sql)
        self.stdout.write("Secuencias de la base reseteadas.")
