from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

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
        self.stdout.write(self.style.SUCCESS(
            f"Datos cargados: {Producto.objects.count()} productos."
        ))
