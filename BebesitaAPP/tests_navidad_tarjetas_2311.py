"""/navidad/: el pan de pascua no sale dos veces ni con la foto de la torta (23-11-2026).

Captura de Diego del 23-11: la tarjeta generica "Para compartir en la celebracion" mostraba
el pan con la foto de la torta y el boton "Ver la pan de pascua artesanal", ademas de su
tarjeta propia de la oferta; y la torta salia dos veces (la duplicada que recrea el build).
"""
import datetime as dt
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Producto


@override_settings(SITE_URL="https://dulcecita.cl", BRAND_NAME="Dulcecita")
@patch("django.utils.timezone.localdate", return_value=dt.date(2026, 11, 25))
class TarjetasDeNavidad(TestCase):

    def setUp(self):
        self._media = tempfile.mkdtemp(prefix="dulcecita-nav-")
        self._ajuste = override_settings(MEDIA_ROOT=self._media)
        self._ajuste.enable()
        crear = lambda nombre, slug, precio: Producto.objects.create(
            nombre=nombre, slug=slug, precio=precio, descripcion="x", visible=True, disponible=True,
            minimo=1, en_box=False, imagen=SimpleUploadedFile(f"{slug}.jpg", b"img", content_type="image/jpeg"))
        self.torta = crear("Torta de cuchuflís", "torta-de-cuchuflis", 14990)
        self.pan = crear("Pan de pascua", "pan-de-pascua", 8590)
        self.queque = crear("Queque navideño", "queque-navideno", 6990)

    def tearDown(self):
        self._ajuste.disable()
        shutil.rmtree(self._media, ignore_errors=True)

    def _html(self):
        return self.client.get(reverse("navidad")).content.decode()

    def test_el_pan_no_sale_en_las_tarjetas_de_celebracion(self, _):
        html = self._html()
        self.assertNotIn("Para compartir en la celebración: pan de pascua", html)
        self.assertEqual(html.count("Ver el pan de pascua artesanal"), 1)  # solo su tarjeta propia

    def test_ningun_boton_dice_ver_la_pan(self, _):
        self.assertNotIn("Ver la pan", self._html())

    def test_cada_tarjeta_usa_la_foto_de_su_producto(self, _):
        html = self._html()
        bloque = html.split("Para compartir en la celebración: queque navideño")[0].rsplit("<article", 1)[1]
        self.assertIn("queque-navideno", bloque)
        self.assertNotIn("torta-cuchuflis-cinta-rosada", bloque)

    def test_la_torta_conserva_su_foto_de_galeria(self, _):
        html = self._html()
        bloque = html.split("Para compartir en la celebración: torta de cuchuflís")[0].rsplit("<article", 1)[1]
        self.assertIn("torta-cuchuflis-cinta-rosada", bloque)
