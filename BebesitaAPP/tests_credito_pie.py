"""Credito del pie (02-11-2026, consejo SEO de Jorge Urzua).

El enlace a GoGoDevS lleva la palabra clave como texto ("Desarrollo web") y no
la marca, apunta a https://www.gogodevs.cl/ (con www, sin utm ni nofollow) y la
marca queda fuera del enlace: "<a>Desarrollo web</a> por GoGoDevS".
"""
import re

from django.test import TestCase

ANCLA = "Desarrollo web"


class CreditoDelPie(TestCase):
    def test_el_pie_enlaza_con_la_palabra_clave(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()

        self.assertRegex(
            html,
            r'<a href="https://www\.gogodevs\.cl/" target="_blank" rel="noopener"[^>]*>'
            + re.escape(ANCLA) + r"</a> por GoGoDevS",
        )
        enlaces = re.findall(r'<a [^>]*href="https?://[^"]*gogodevs\.cl[^"]*"[^>]*>', html)
        self.assertTrue(enlaces, "el pie no enlaza a gogodevs.cl")
        for a in enlaces:
            self.assertIn('href="https://www.gogodevs.cl/"', a)
            self.assertNotIn("utm_", a)
            self.assertNotIn("nofollow", a)
        # El texto antiguo usaba la marca como ancla.
        self.assertNotIn(">GoGoDevS</a>", html)
        self.assertNotIn("Sitio desarrollado por", html)
