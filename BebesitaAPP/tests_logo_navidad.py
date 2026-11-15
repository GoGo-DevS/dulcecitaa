"""Logo navideño (15-11-2026, diseño que mando Diego).

En temporada (1-11 al 25-12) el logo del menu y el de la portada son el mismo
logotipo con el gorro del Viejito Pascuero en la "a" final. Reemplaza al gorro
dibujado en CSS sobre la "d". Fuera de temporada vuelve el logo de siempre,
solo: nadie tiene que acordarse de sacarlo en enero.
"""
import datetime
from pathlib import Path
from unittest import mock

from django.test import override_settings

from .tests_tanda_0311 import _Catalogo

ESTATICOS = Path(__file__).parent / "static"
EN_TEMPORADA = datetime.date(2026, 11, 15)
FUERA = (datetime.date(2026, 10, 31), datetime.date(2026, 12, 26), datetime.date(2027, 1, 10))


@override_settings(BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl")
class LogoNavidadTests(_Catalogo):
    def _get(self, ruta, dia):
        with mock.patch("BebesitaAPP.temporada.timezone.localdate", return_value=dia):
            respuesta = self.client.get(ruta)
        self.assertEqual(respuesta.status_code, 200, ruta)
        return respuesta.content.decode()

    @staticmethod
    def _logo_menu(html):
        return html.split('class="navbar-brand dr-brand"', 1)[1].split("</a>", 1)[0]

    def test_en_temporada_el_menu_lleva_el_logo_con_gorro_en_todo_el_sitio(self):
        for ruta in ("/", "/productos/", "/navidad/", "/arma-tu-box/", "/carrito/"):
            logo = self._logo_menu(self._get(ruta, EN_TEMPORADA))
            self.assertIn("img/logo-dulcecita-navidad", logo, ruta)
            self.assertNotIn("logo-dulcecita-rosado", logo, ruta)
            self.assertEqual(logo.count("<img"), 1, ruta)
            # La MISMA caja que el logo de siempre: no mueve el menu ni un pixel.
            self.assertIn('width="879" height="331"', logo, ruta)
            self.assertIn('alt="Dulcecita"', logo, ruta)

    def test_en_temporada_la_portada_tambien(self):
        html = self._get("/", EN_TEMPORADA)
        hero = html.split('class="ig-hero__logo"', 1)[1].split(">", 1)[0]
        self.assertIn("img/logo-dulcecita-navidad", hero)
        self.assertEqual(html.count('class="ig-hero__logo"'), 1)

    def test_fuera_de_temporada_vuelve_el_logo_de_siempre(self):
        for dia in FUERA:
            for ruta in ("/", "/productos/"):
                html = self._get(ruta, dia)
                self.assertNotIn("logo-dulcecita-navidad", html, f"{dia} {ruta}")
                self.assertIn("img/logo-dulcecita-rosado", self._logo_menu(html), f"{dia} {ruta}")

    def test_el_pie_sigue_con_el_logo_blanco(self):
        html = self._get("/", EN_TEMPORADA)
        self.assertIn("img/logo-dulcecita-blanco", html.split("<footer", 1)[1])

    def test_un_solo_gorro_el_css_ya_no_dibuja_el_suyo_sobre_el_logo(self):
        css = (ESTATICOS / "css" / "navidad.css").read_text(encoding="utf-8")
        self.assertNotIn(".dr-brand::before", css)

    def test_el_archivo_mide_lo_que_declara_es_transparente_y_pesa_poco(self):
        from PIL import Image

        archivo = ESTATICOS / "img" / "logo-dulcecita-navidad.webp"
        self.assertLess(archivo.stat().st_size, 100 * 1024)
        with Image.open(archivo) as im:
            self.assertEqual(im.size, (879, 331))
            im = im.convert("RGBA")
            # Fondo transparente (esquina) y gorro rojo donde va, sobre la "a" final.
            self.assertEqual(im.getpixel((2, 2))[3], 0)
            rojo, verde, azul, alfa = im.getpixel((818, 118))
            self.assertTrue(alfa > 200 and rojo > 150 and verde < 90 and azul < 90, (rojo, verde, azul, alfa))
