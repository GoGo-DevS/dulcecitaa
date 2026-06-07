"""
Sube los archivos de media locales a Cloudinary con public_id deterministico.

Uso (requiere CLOUDINARY_URL en el entorno):

    CLOUDINARY_URL=cloudinary://... python manage.py subir_media_cloudinary

Recorre MEDIA_ROOT local y sube cada archivo con el MISMO public_id que la app
pide al renderizar las imagenes ya guardadas en la base de datos. Asi una imagen
guardada como "productos/Alfajor1.jpg" se sirve desde Cloudinary sin cambiar la BD.

Mapeo (verificado): nombre en BD  ->  URL de la app
    productos/Alfajor1.jpg  ->  .../image/upload/v1/media/productos/Alfajor1.jpg
Por eso el public_id de Cloudinary es:  "media/" + ruta_sin_extension.

Es idempotente: usa overwrite=True y unique_filename=False, asi re-correrlo no
crea duplicados ni sufijos aleatorios.
"""

import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# Extensiones que Cloudinary entrega como resource_type "image".
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".avif", ".ico"}


class Command(BaseCommand):
    help = "Sube MEDIA_ROOT local a Cloudinary con public_id que coincide con la BD."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Lista lo que se subiria sin subir nada.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "USE_CLOUDINARY", False):
            raise CommandError(
                "CLOUDINARY_URL no esta definido. Defini la variable antes de correr."
            )

        import cloudinary.uploader

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            raise CommandError(f"No existe MEDIA_ROOT: {media_root}")

        dry_run = options["dry_run"]
        subidos = saltados = errores = 0

        for path in sorted(media_root.rglob("*")):
            if not path.is_file():
                continue

            rel = path.relative_to(media_root).as_posix()      # productos/Alfajor1.jpg
            stem, ext = os.path.splitext(rel)                    # productos/Alfajor1 , .jpg
            ext = ext.lower()
            public_id = f"media/{stem}"                           # media/productos/Alfajor1
            resource_type = "image" if ext in IMAGE_EXTS else "raw"
            # Para "raw" (pdf, etc.) el public_id conserva la extension.
            if resource_type == "raw":
                public_id = f"media/{rel}"

            if dry_run:
                subidos += 1
                self.stdout.write(f"  + {rel}  ->  {public_id} ({resource_type})")
                continue

            try:
                cloudinary.uploader.upload(
                    str(path),
                    public_id=public_id,
                    resource_type=resource_type,
                    overwrite=True,
                    unique_filename=False,
                    use_filename=False,
                    invalidate=True,
                )
                subidos += 1
                self.stdout.write(self.style.SUCCESS(f"  + {rel}"))
            except Exception as exc:  # pragma: no cover - log y seguir
                errores += 1
                self.stdout.write(self.style.ERROR(f"  ! {rel}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo. Subidos: {subidos} · Saltados: {saltados} · Errores: {errores}"
            )
        )
