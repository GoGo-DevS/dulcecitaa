"""Pan de pascua y Maipu (20-11-2026).

- La ficha del pan dice lo que se promociona (medio kilo, el precio del producto) y
  Maipu (retiro y entrega a domicilio; otras comunas por WhatsApp), y NO hereda las
  preguntas de los dulces ("duran aproximadamente un mes", por mayor, personalizar),
  que Tamara nunca confirmo para el pan.
- /navidad/ enlaza a la ficha del pan solo si existe y esta visible.
- /delivery/ y el schema del negocio nombran Maipu.
"""
import datetime as dt
import json
import re
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Producto
from .tests_tanda_0311 import _ld

EN_TEMPORADA = dt.date(2026, 11, 25)


def _title(html):
    return re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()


def _meta(html):
    return re.search(r'<meta name="description" content="([^"]*)"', html).group(1)


@override_settings(SITE_URL="https://dulcecita.cl", BRAND_NAME="Dulcecita", MINIMO_UNIDADES=10)
@patch("django.utils.timezone.localdate", return_value=EN_TEMPORADA)
class PanDePascuaYMaipu(TestCase):

    def setUp(self):
        self._media = tempfile.mkdtemp(prefix="dulcecita-pan-")
        self._ajuste = override_settings(MEDIA_ROOT=self._media)
        self._ajuste.enable()
        foto = SimpleUploadedFile("pan.jpg", b"img", content_type="image/jpeg")
        self.pan = Producto.objects.create(nombre="Pan de pascua", slug="pan-de-pascua", precio=8590, minimo=1,
                                           descripcion="Pan de pascua casero.", visible=True, imagen=foto)

    def tearDown(self):
        self._ajuste.disable()
        shutil.rmtree(self._media, ignore_errors=True)

    def _ficha(self):
        return self.client.get(reverse("producto_ficha", args=["pan-de-pascua"])).content.decode()

    def test_title_h1_y_description_dicen_pan_de_pascua_y_maipu(self, *_):
        html = self._ficha()
        self.assertEqual(_title(html), "Pan de pascua artesanal en Maipú desde $8.590 | Dulcecita")
        self.assertLessEqual(len(_title(html)), 60)
        self.assertIn('<h1 class="detail-titulo">Pan de pascua artesanal en Maipú</h1>', html)
        meta = _meta(html)
        self.assertLessEqual(len(meta), 155)
        for dato in ("medio kilo", "$8.590", "Maipú"):
            self.assertIn(dato, meta)

    def test_no_hereda_las_preguntas_de_los_dulces(self, *_):
        html = self._ficha()
        faq = [q["name"] for n in _ld(html) if n.get("@type") == "FAQPage" for q in n["mainEntity"]]
        self.assertIn("¿Cuánto vale el pan de pascua?", faq)
        for ajena in ("¿Cuánto duran y cómo se guardan?", "¿Se pueden personalizar?", "¿Venden por mayor?"):
            self.assertNotIn(ajena, faq)
        self.assertNotIn("aproximadamente un mes", html.split("<main")[1].split("</main>")[0])

    def test_la_ficha_cuenta_retiro_y_entrega_en_maipu(self, *_):
        html = self._ficha()
        self.assertIn("Si estás en Maipú, lo retiras o te lo llevamos a tu casa.", html)
        self.assertIn("pedidos de Navidad hasta el 20 de diciembre", html)

    def test_navidad_enlaza_a_la_ficha_del_pan(self, *_):
        html = self.client.get(reverse("navidad")).content.decode()
        # El boton de la tarjeta del pan (el pie ya enlaza a todas las fichas, no cuenta).
        self.assertIn('<a href="/productos/pan-de-pascua/" class="btn-main">Ver el pan de pascua artesanal</a>', html)

    def test_sin_pan_visible_navidad_no_enlaza_a_una_ficha_oculta(self, *_):
        Producto.objects.filter(pk=self.pan.pk).update(visible=False)
        html = self.client.get(reverse("navidad")).content.decode()
        self.assertNotIn("Ver el pan de pascua artesanal", html)
        self.assertIn("Encargar pan de pascua por WhatsApp", html)

    def test_delivery_nombra_maipu(self, *_):
        html = self.client.get(reverse("delivery")).content.decode()
        self.assertIn('<p class="entrega__eyebrow">Maipú</p>', html)
        self.assertIn("En Maipú puedes retirar tu pedido o recibirlo en tu casa.", html)
        self.assertLessEqual(len(_meta(html)), 155)

    def test_el_schema_del_negocio_esta_en_maipu_y_sirve_a_todo_chile(self, *_):
        html = self.client.get("/").content.decode()
        negocio = next(n for n in _ld(html) if n.get("@id", "").endswith("/#negocio"))
        self.assertEqual(negocio["address"]["addressLocality"], "Maipú")
        self.assertIn({"@type": "City", "name": "Maipú"}, negocio["areaServed"])
        self.assertIn({"@type": "Country", "name": "Chile"}, negocio["areaServed"])
        self.assertNotIn("streetAddress", negocio["address"])
