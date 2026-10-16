"""Ninguna pagina hace una consulta por producto (16-10-2026).

La portada hacia 102 consultas con 12 productos (Promocion.vigente() una vez por
precio + los precios por combinacion uno por uno) y tardaba 3-4 s con la base
en Neon. Estas pruebas fallan si el numero vuelve a crecer con los productos.
"""
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from .models import CategoriaProducto, Opcion, Producto, Promocion


class PocasConsultas(TestCase):
    def setUp(self):
        cat = CategoriaProducto.objects.create(nombre="Dulces", slug="dulces")
        ops = [Opcion.objects.create(nombre="Op%d" % i) for i in range(3)]
        for i in range(12):
            p = Producto.objects.create(
                nombre="Producto %d" % i, precio=1000 + i, visible=True, destacado=i < 4,
                categoria=cat, imagen=SimpleUploadedFile("a.jpg", b"img", content_type="image/jpeg"))
            p.opciones.set(ops)

    def _consultas(self, ruta):
        with CaptureQueriesContext(connection) as c:
            self.assertEqual(self.client.get(ruta).status_code, 200)
        return len(c.captured_queries)

    def test_portada_y_catalogo_no_crecen_con_los_productos(self):
        self.assertLessEqual(self._consultas("/"), 15)
        self.assertLessEqual(self._consultas("/productos/"), 10)

    def test_la_promocion_se_consulta_una_vez_por_visita(self):
        hoy = timezone.localdate()
        Promocion.objects.create(nombre="Prueba", porcentaje=10, desde=hoy - timedelta(days=1),
                                 hasta=hoy + timedelta(days=1), activa=True)
        with CaptureQueriesContext(connection) as c:
            self.client.get("/productos/")
        de_promo = [q for q in c.captured_queries if "promocion" in q["sql"].lower()]
        self.assertEqual(len(de_promo), 1)

    def test_una_promocion_nueva_se_ve_en_la_visita_siguiente(self):
        self.assertNotIn("10%", self.client.get("/productos/").content.decode())
        hoy = timezone.localdate()
        Promocion.objects.create(nombre="Prueba", porcentaje=10, desde=hoy, hasta=hoy, activa=True,
                                 mensaje="10% en todo")
        self.assertIn("10% en todo", self.client.get("/productos/").content.decode())
