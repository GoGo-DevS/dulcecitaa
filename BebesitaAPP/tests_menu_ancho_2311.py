"""El menú de escritorio cabe en todos los anchos (23-11-2026).

Con "Navidad" en el menú, en 1366 px la página se corría 141 px hacia el lado y el
logo quedaba cortado. El comportamiento real solo se ve en un navegador y lo mide
docs/pruebas-visuales/menu_sin_desborde.py (sitio en vivo: 27 combinaciones con
problemas; con el CSS de esta rama: 0). Acá se fija el CSS que lo arregla, para que
nadie lo borre sin enterarse.
"""
import re

from django.test import SimpleTestCase

from .tests_ficha_cabecera_2011 import _estatico


MARCA = '23-11-2026: con "Navidad" en el menú'


def _bloque(css, media):
    # Busca después del comentario de hoy: ya existe otro "@media (min-width: 1400px)"
    # (el que agranda .container a 1340px) y no es este.
    inicio = css.index(media, css.index(MARCA))
    return css[inicio:css.index("\n}\n", inicio)]


class MenuCabeEnEscritorio(SimpleTestCase):

    def setUp(self):
        self.css = _estatico("css/style.css")

    def test_de_1280_a_1399_el_menu_es_compacto_y_el_gap_le_gana_a_bootstrap(self):
        b = _bloque(self.css, "@media (min-width: 1280px) and (max-width: 1399.98px)")
        # gap-lg-4 de Bootstrap trae !important: sin el nuestro, el espacio no se achica.
        self.assertIn(".dr-nav .navbar-nav { gap: .9rem !important; }", b)
        self.assertIn(".dr-nav .nav-link { font-size: .85rem;", b)
        self.assertIn(".dr-nav .dr-logo-img { height: 52px; }", b)

    def test_desde_1400_tamano_completo_con_menos_espacio(self):
        b = _bloque(self.css, "@media (min-width: 1400px)")
        self.assertIn(".dr-nav .navbar-nav { gap: 1rem !important; }", b)

    def test_de_992_a_1099_los_enlaces_tienen_menos_relleno(self):
        b = _bloque(self.css, "@media (min-width: 992px) and (max-width: 1099.98px)")
        self.assertIn(".dr-nav .nav-link:not(.dr-pedido) { padding-inline: .35rem !important; }", b)

    def test_ningun_tramo_de_escritorio_queda_sin_regla(self):
        # 992-1279 lo cubre la regla del 03-11; 1280-1399 y 1400+ las de hoy.
        self.assertRegex(self.css, r"@media \(min-width: 992px\) and \(max-width: 1279\.98px\)")
        self.assertRegex(self.css, re.escape("@media (min-width: 1280px) and (max-width: 1399.98px)"))
        self.assertRegex(self.css, re.escape("@media (min-width: 1400px)"))
