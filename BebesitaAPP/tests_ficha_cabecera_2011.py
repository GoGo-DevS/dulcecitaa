"""Ficha, cabecera y validFrom (20-11-2026).

Tres arreglos medidos en vivo antes de tocar nada
(GoGoCRM/docs/seo-semanal/dulcecita/2026-11-20-ficha-navbar-validfrom.md):

1. En la PAGINA de la ficha los botones quedaban al fondo de la columna (451 px
   vacios en el pan de pascua a 1440 de ancho) por un margin-top:auto pensado
   para el modal. El arreglo va con la clase --pagina y no toca el modal.
2. La cabecera titilaba: umbral unico de 120 px + cabecera sticky que se achica
   + scroll anchoring = bucle. Ahora tiene histeresis (encoge >120, vuelve <60).
   El comportamiento real lo prueba el script de Playwright
   (docs/pruebas-visuales/ficha_y_cabecera.py); aca se fija el codigo.
3. Search Console pidio validFrom en las ofertas: sale de Promocion.desde y solo
   cuando hay promocion vigente, igual que priceValidUntil.
"""
import datetime as dt
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Producto, Promocion
from .tests_tanda_0311 import _ld


def _estatico(ruta):
    encontrado = finders.find(ruta)
    assert encontrado, ruta
    return Path(encontrado).read_text(encoding="utf-8")


class _ConProducto(TestCase):
    def setUp(self):
        self._media = tempfile.mkdtemp(prefix="dulcecita-ficha-")
        self._ajuste = override_settings(MEDIA_ROOT=self._media)
        self._ajuste.enable()
        foto = SimpleUploadedFile("pan.jpg", b"img", content_type="image/jpeg")
        self.pan = Producto.objects.create(nombre="Pan de pascua", descripcion="Pan de pascua casero.",
                                           precio=8500, visible=True, imagen=foto)

    def tearDown(self):
        self._ajuste.disable()
        shutil.rmtree(self._media, ignore_errors=True)


class FichaComoPagina(_ConProducto):

    def test_la_pagina_de_la_ficha_lleva_la_clase_pagina(self):
        html = self.client.get(reverse("producto_ficha", args=[self.pan.slug])).content.decode()
        self.assertIn('class="product-detail-wrap product-detail-wrap--pagina"', html)

    def test_el_modal_no_la_lleva(self):
        html = self.client.get(reverse("producto_detalle", args=[self.pan.pk]) + "?modal=1").content.decode()
        self.assertIn('class="product-detail-wrap"', html)
        self.assertNotIn("product-detail-wrap--pagina", html)

    def test_el_css_corrige_solo_la_pagina_y_el_modal_conserva_sus_botones_abajo(self):
        css = _estatico("css/style.css")
        self.assertIn(".product-detail-wrap--pagina .product-detail-content { justify-content: center; }", css)
        self.assertIn(".product-detail-wrap--pagina .detail-actions { margin-top: .4rem; }", css)
        # El modal de escritorio sigue con los botones pegados abajo (regla propia).
        self.assertRegex(css, r"#modalProducto \.detail-actions \{\s*position: sticky; bottom: 0;[^}]*margin-top: auto;")


class CabeceraConHisteresis(TestCase):

    def test_encoge_sobre_120_y_vuelve_bajo_60(self):
        js = _estatico("js/main.js")
        self.assertIn("if (!encogida && y > 120) cabecera.classList.add('encogida');", js)
        self.assertIn("else if (encogida && y < 60) cabecera.classList.remove('encogida');", js)

    def test_ya_no_hay_umbral_unico(self):
        self.assertNotIn("toggle('encogida'", _estatico("js/main.js"))


@override_settings(SITE_URL="https://dulcecita.cl")
class ValidFromEnLaOferta(_ConProducto):

    def _oferta(self):
        html = self.client.get(reverse("producto_ficha", args=[self.pan.slug])).content.decode()
        return next(n for n in _ld(html) if n.get("@type") == "Product")["offers"]

    def _promo(self, desde, hasta, activa=True):
        return Promocion.objects.create(nombre="prueba", porcentaje=10, etiqueta="Navidad", activa=activa,
                                        desde=desde, hasta=hasta)

    def test_con_promocion_vigente_declara_inicio_y_termino_de_esa_promocion(self):
        hoy = timezone.localdate()
        promo = self._promo(hoy - dt.timedelta(days=2), hoy + dt.timedelta(days=5))
        oferta = self._oferta()
        self.assertEqual(oferta["validFrom"], promo.desde.isoformat())
        self.assertEqual(oferta["priceValidUntil"], promo.hasta.isoformat())

    def test_sin_promocion_no_declara_ninguna_fecha(self):
        oferta = self._oferta()
        self.assertNotIn("validFrom", oferta)
        self.assertNotIn("priceValidUntil", oferta)

    def test_una_promocion_vencida_o_apagada_no_cuenta(self):
        hoy = timezone.localdate()
        self._promo(hoy - dt.timedelta(days=20), hoy - dt.timedelta(days=10))
        self._promo(hoy - dt.timedelta(days=1), hoy + dt.timedelta(days=3), activa=False)
        oferta = self._oferta()
        self.assertNotIn("validFrom", oferta)
        self.assertNotIn("priceValidUntil", oferta)
