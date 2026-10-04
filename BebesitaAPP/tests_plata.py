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
