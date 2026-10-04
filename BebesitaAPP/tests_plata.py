"""El filtro de precios: lo que ve la clienta en la portada y Tamara en el panel."""
from django.template import Context, Template
from django.test import TestCase

from BebesitaAPP.templatetags.plata import pesos


class PesosTests(TestCase):

    def test_agrupa_con_punto_y_no_con_espacio_duro(self):
        # intcomma con es-cl devuelve "12 900": se lee como numero cortado
        self.assertEqual(pesos(12900), "12.900")
        self.assertNotIn(" ", pesos(12900))

    def test_los_tramos(self):
        self.assertEqual(pesos(0), "0")
        self.assertEqual(pesos(999), "999")
        self.assertEqual(pesos(1000), "1.000")
        self.assertEqual(pesos(1234567), "1.234.567")

    def test_negativo_conserva_el_signo(self):
        self.assertEqual(pesos(-12900), "-12.900")

    def test_lo_que_no_es_numero_vuelve_igual(self):
        self.assertEqual(pesos(None), "")
        self.assertEqual(pesos(""), "")
        self.assertEqual(pesos("Consultar"), "Consultar")

    def test_en_una_plantilla(self):
        t = Template("{% load plata %}${{ v|pesos }}")
        self.assertEqual(t.render(Context({"v": 12900})), "$12.900")


class PreciosEnTodasLasPantallasTests(TestCase):
    """Un mismo producto no puede verse "$12.900" en la portada y "$12900" en
    el catalogo. Pasaba: la portada usaba el filtro y el catalogo floatformat."""

    def setUp(self):
        from BebesitaAPP.models import Producto
        Producto.objects.create(nombre="Caja grande", descripcion="x", precio=12900,
                                stock=5, visible=True, destacado=True,
                                imagen="productos/x.jpg")

    def test_ninguna_pantalla_publica_un_precio_de_5_cifras_sin_separador(self):
        import re
        for ruta in ("/", "/productos/"):
            html = self.client.get(ruta).content.decode()
            # $ seguido de 5 o mas digitos sin punto = sin formatear
            sueltos = re.findall(r"\$\d{5,}(?!\d)", html)
            self.assertEqual(sueltos, [], f"{ruta}: {sueltos[:5]}")

    def test_el_precio_sale_con_punto(self):
        html = self.client.get("/productos/").content.decode()
        self.assertIn("$12.900", html)
