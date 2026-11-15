"""/navidad/ con menos texto y con las fotos de Tamara (15-11-2026).

Pedido de Diego: "siento que hay mucho, mucho texto", usar las fotos que mando
Tamara y optimizarlas para Google.

- Menos texto A LA VISTA: cada regalo es una tarjeta; el ejemplo de box y las
  preguntas quedan plegados, pero siguen en la pagina (Google y el FAQPage).
- Fotos: con nombre que dice lo que son, alt, ancho y alto, WebP liviano; la de
  portada sin carga diferida y una propia para cuando se comparte el enlace.
- Las fotos navideñas (empaque con cinta y tarjeta) solo con oferta confirmada.

Lo que la pagina DICE (precios, fechas, lo que la duena no confirmo) sigue
probado en tests_tanda_0311.py y tests_navidad_1111.py.
"""
import datetime
import html as html_lib
import re
from pathlib import Path
from unittest import mock

from django.test import override_settings
from PIL import Image

from .tests_tanda_0311 import _Catalogo, _cuerpo, _faq

ESTATICOS = Path(__file__).parent / "static"
CON_OFERTA = datetime.date(2026, 11, 15)
SIN_OFERTA = datetime.date(2027, 11, 5)
FOTOS_NAVIDENAS = ("regalos-de-navidad-dulcecita", "regalo-navideno-cinta-y-tarjeta",
                   "box-navideno-bolsas-kraft", "og-navidad")


def _palabras(trozo, solo_a_la_vista):
    trozo = re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<svg\b.*?</svg>", " ", trozo, flags=re.S)
    if solo_a_la_vista:
        # De un bloque plegado solo se ve su encabezado (<summary>) hasta que se abre.
        trozo = re.sub(r"<details\b[^>]*>(.*?)</details>",
                       lambda m: " ".join(re.findall(r"<summary\b.*?</summary>", m.group(1), flags=re.S)),
                       trozo, flags=re.S)
    return len(re.findall(r"\w+", html_lib.unescape(re.sub(r"<[^>]+>", " ", trozo))))


def _imagenes(trozo):
    return [dict(re.findall(r'([\w-]+)="([^"]*)"', etiqueta)) for etiqueta in re.findall(r"<img\b[^>]*>", trozo)]


@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1490, BOX_MINIMO_TOTAL=10000, DESPACHO_HORAS=48,
                   BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl",
                   WHATSAPP_URL="https://wa.me/56900000000")
class NavidadMenosTextoTests(_Catalogo):
    def _html(self, dia=CON_OFERTA):
        with mock.patch("BebesitaAPP.temporada._hoy", return_value=dia):
            respuesta = self.client.get("/navidad/")
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    # -- menos texto --
    def test_a_la_vista_queda_menos_de_la_mitad_del_texto_de_antes(self):
        cuerpo = _cuerpo(self._html())
        a_la_vista, total = _palabras(cuerpo, True), _palabras(cuerpo, False)
        # La pagina anterior mostraba 674 palabras de corrido (medido en vivo el 15-11).
        self.assertLess(a_la_vista, 674 // 2, a_la_vista)
        # Lo plegado sigue en la pagina: es texto que Google lee y que el cliente abre.
        self.assertGreater(total - a_la_vista, 120, (total, a_la_vista))

    def test_cada_regalo_es_una_tarjeta_con_su_titulo(self):
        cuerpo = _cuerpo(self._html())
        tarjetas = cuerpo.split('<article class="nav-card">')[1:]
        self.assertEqual(len(tarjetas), 4)   # box, pan de pascua, detalle por unidad, torta
        for tarjeta in tarjetas:
            self.assertEqual(tarjeta.split("</article>", 1)[0].count("<h2>"), 1)
        for titulo in ("Box navideño para regalar", "Pan de pascua artesanal", "Un detalle para cada persona",
                       "Para compartir en la celebración: torta de cuchuflís"):
            self.assertIn(f"<h2>{titulo}</h2>", cuerpo)

    def test_las_preguntas_van_plegadas_y_estan_todas(self):
        html = self._html()
        plegadas = re.findall(r'<details class="faq-item surface-card nav-faq"([^>]*)>', html)
        self.assertEqual(len(plegadas), len(_faq(html)))
        self.assertTrue(all("open" not in atributos for atributos in plegadas))

    def test_el_ejemplo_de_box_sigue_en_la_pagina_pero_plegado(self):
        cuerpo = _cuerpo(self._html())
        plegado = cuerpo.split('<details class="nav-mas">', 1)[1].split("</details>", 1)[0]
        self.assertRegex(plegado, r"cuesta \$[\d.]+ con el empaque")
        self.assertIn("no se elige color", plegado)
        self.assertIn("box a pedido", plegado)

    # -- fotos --
    def test_la_foto_de_portada_carga_primero_y_las_demas_esperan(self):
        fotos = _imagenes(_cuerpo(self._html()))
        self.assertEqual(len(fotos), 5)
        portada, demas = fotos[0], fotos[1:]
        self.assertIn("regalos-de-navidad-dulcecita", portada["src"])
        self.assertEqual(portada.get("fetchpriority"), "high")
        self.assertNotIn("loading", portada)
        self.assertTrue(all(foto.get("loading") == "lazy" for foto in demas), demas)

    def test_cada_foto_dice_que_muestra_y_cuanto_mide(self):
        for dia in (CON_OFERTA, SIN_OFERTA):
            for foto in _imagenes(_cuerpo(self._html(dia))):
                self.assertGreater(len(foto.get("alt", "")), 25, foto)
                self.assertTrue(foto.get("width", "").isdigit() and foto.get("height", "").isdigit(), foto)

    def test_los_archivos_existen_pesan_poco_y_miden_lo_declarado(self):
        vistos = set()
        for dia in (CON_OFERTA, SIN_OFERTA):
            for foto in _imagenes(_cuerpo(self._html(dia))):
                archivo = ESTATICOS / foto["src"].split("/static/", 1)[1].split("?", 1)[0]
                self.assertTrue(archivo.is_file(), archivo)
                self.assertTrue(archivo.name.endswith(".webp"), archivo.name)
                self.assertLess(archivo.stat().st_size, 100 * 1024, archivo.name)
                with Image.open(archivo) as imagen:
                    self.assertEqual(imagen.size, (int(foto["width"]), int(foto["height"])), archivo.name)
                vistos.add(archivo.name)
        self.assertGreaterEqual(len(vistos), 6)

    def test_al_compartir_el_enlace_sale_la_foto_navidena(self):
        html = self._html()
        esperado = "https://dulcecita.cl/static/img/og-navidad.jpg"
        self.assertIn(f'<meta property="og:image" content="{esperado}">', html)
        self.assertIn(f'<meta name="twitter:image" content="{esperado}">', html)
        self.assertIn('<meta property="og:image:alt" content="Regalos de Navidad de Dulcecita', html)
        with Image.open(ESTATICOS / "img" / "og-navidad.jpg") as imagen:
            self.assertEqual(imagen.size, (1200, 630))

    # -- un año sin oferta confirmada --
    def test_sin_oferta_no_se_muestra_el_empaque_navideno(self):
        html = self._html(SIN_OFERTA)
        for foto in FOTOS_NAVIDENAS:
            self.assertNotIn(foto, html, foto)
        cuerpo = _cuerpo(html)
        self.assertEqual(cuerpo.count('<article class="nav-card">'), 3)   # sin pan de pascua
        self.assertIn("<h2>Un box de dulces para regalar</h2>", cuerpo)
        self.assertIn("cajas-cuchuflis-para-regalar", _imagenes(cuerpo)[0]["src"])
