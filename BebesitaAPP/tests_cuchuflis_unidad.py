"""Los cuchuflis se venden por unidad (15-11-2026, pedido de la duena).

Antes: bolsita de 4 a $1.590 (bañados) y $1.190 (rellenos), desde 10 bolsitas.
Ahora: por unidad a $350 (con cobertura) y $300 (sin cobertura), desde 30.

Cada prueba parte de la base COMO ESTA HOY en produccion (bolsita de 4) y le
pasa la migracion 0018: lo que se comprueba es el camino real del cambio, no
un catalogo armado ya con los valores nuevos.

1. La migracion: que cambia, que no toca y que se puede repetir y deshacer.
2. El sitio despues: ficha, schema, catalogo, carrito, checkout, Navidad y box.
3. El carrito viejo: una linea bajo el minimo nuevo no se cobra tal cual.
"""
import importlib

from django.apps import apps as apps_reales
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Opcion, Pedido, PrecioCombinacion, PreguntaFrecuente, Producto
from .tests_tanda_0311 import _cuerpo, _faq, _ld, _meta, _title

migracion = importlib.import_module("BebesitaAPP.migrations.0018_cuchuflis_por_unidad")

PREGUNTA_MINIMO = "¿Cuál es el pedido mínimo?"
RESPUESTA_MINIMO = ("El mínimo es de 10 unidades por producto. Si quieres mezclar varios sabores, "
                    "en Arma tu box el mínimo baja a 3 unidades por producto.")


def _crear(nombre, precio, descripcion="Texto de la duena", coberturas=(), **extra):
    p = Producto.objects.create(
        nombre=nombre, descripcion=descripcion, precio=precio, visible=True,
        imagen=SimpleUploadedFile("a.jpg", b"img", content_type="image/jpeg"), **extra)
    if coberturas:
        p.opciones.add(*coberturas)
    return p


class _ProduccionAntes(TestCase):
    """El catalogo como estaba en dulcecita.cl el 15-11-2026, antes del cambio."""

    def setUp(self):
        self.choc = Opcion.objects.create(tipo="cobertura", nombre="Chocolate", orden=1)
        self.blanco = Opcion.objects.create(tipo="cobertura", nombre="Chocolate blanco", orden=2)
        cob = (self.choc, self.blanco)
        self.barquillos = _crear("Barquillos Rellenos Bañados en Chocolate", 1290, coberturas=cob, orden=0)
        self.alfajores = _crear("Alfajores", 1590, coberturas=cob, orden=1)
        self.banados = _crear(
            "Cuchuflís bañados", 1590, coberturas=cob, orden=3, unidades_por_pack=4,
            descripcion=("Cuchuflís crujientes rellenos de manjar y bañados enteros en chocolate. "
                         "Se venden en bolsita de 4 unidades."))
        self.rellenos = _crear(
            "Cuchuflís rellenos", 1190, orden=4, unidades_por_pack=4,
            descripcion=("Cuchuflís crujientes rellenos de manjar, sin baño de chocolate. "
                         "Se venden en bolsita de 4 unidades."))
        self.torta = _crear("Torta de cuchuflís", 14990, orden=5, minimo=1, en_box=False)
        t50 = Opcion.objects.create(tipo="tamano", nombre="50 cuchuflís", orden=1)
        sin = Opcion.objects.create(tipo="cobertura", nombre="Sin cobertura", orden=0)
        self.torta.opciones.add(t50, sin, self.choc)
        for cob_torta, precio in [(sin, 14990), (self.choc, 17990)]:
            pc = PrecioCombinacion.objects.create(producto=self.torta, precio=precio)
            pc.opciones.set([t50, cob_torta])
            pc.actualizar_clave()
        self.pregunta = PreguntaFrecuente.objects.create(
            pregunta=PREGUNTA_MINIMO, respuesta=RESPUESTA_MINIMO, orden=10)

    def _migrar(self):
        migracion.por_unidad(apps_reales, None)
        for p in (self.banados, self.rellenos, self.alfajores, self.barquillos, self.torta, self.pregunta):
            p.refresh_from_db()

    @staticmethod
    def _venta(p):
        return (p.precio, p.unidades_por_pack, p.minimo)


# --- 1. la migracion ----------------------------------------------------------

class MigracionCuchuflisTests(_ProduccionAntes):
    def test_los_cuchuflis_quedan_por_unidad_a_350_y_300_desde_30(self):
        self._migrar()
        self.assertEqual(self._venta(self.banados), (350, 1, 30))
        self.assertEqual(self._venta(self.rellenos), (300, 1, 30))

    def test_la_frase_de_la_bolsita_sale_de_la_descripcion(self):
        self._migrar()
        self.assertEqual(self.banados.descripcion,
                         "Cuchuflís crujientes rellenos de manjar y bañados enteros en chocolate. "
                         "Se venden por unidad, desde 30.")
        self.assertNotIn("bolsita", self.rellenos.descripcion)
        self.assertIn("Se venden por unidad, desde 30.", self.rellenos.descripcion)

    def test_una_descripcion_que_la_duena_reescribio_se_respeta(self):
        Producto.objects.filter(pk=self.banados.pk).update(descripcion="Mis cuchuflís, los mejores.")
        self._migrar()
        self.assertEqual(self.banados.descripcion, "Mis cuchuflís, los mejores.")
        self.assertEqual(self._venta(self.banados), (350, 1, 30))

    def test_no_toca_ningun_otro_producto_ni_la_torta(self):
        self._migrar()
        self.assertEqual(self._venta(self.alfajores), (1590, 1, 0))
        self.assertEqual(self._venta(self.barquillos), (1290, 1, 0))
        self.assertEqual(self._venta(self.torta), (14990, 1, 1))
        self.assertEqual(sorted(self.torta.precios_combinacion.values_list("precio", flat=True)),
                         [14990, 17990])

    def test_la_pregunta_del_minimo_ahora_nombra_a_los_cuchuflis(self):
        self._migrar()
        self.assertEqual(self.pregunta.respuesta,
                         RESPUESTA_MINIMO + " Los cuchuflís se venden por unidad, desde 30.")

    def test_correrla_dos_veces_da_lo_mismo(self):
        self._migrar()
        self._migrar()
        self.assertEqual(self._venta(self.banados), (350, 1, 30))
        self.assertEqual(self.banados.descripcion.count("Se venden por unidad, desde 30."), 1)
        self.assertEqual(self.pregunta.respuesta.count("cuchuflís"), 1)

    def test_se_puede_deshacer(self):
        antes = (self.banados.descripcion, self.rellenos.descripcion)
        self._migrar()
        migracion.a_bolsita(apps_reales, None)
        for p in (self.banados, self.rellenos, self.pregunta):
            p.refresh_from_db()
        self.assertEqual(self._venta(self.banados), (1590, 4, 0))
        self.assertEqual(self._venta(self.rellenos), (1190, 4, 0))
        self.assertEqual((self.banados.descripcion, self.rellenos.descripcion), antes)
        self.assertEqual(self.pregunta.respuesta, RESPUESTA_MINIMO)

    def test_los_encuentra_por_nombre_si_el_slug_cambio(self):
        Producto.objects.filter(pk=self.banados.pk).update(slug="cuchuflis-con-chocolate")
        self._migrar()
        self.assertEqual(self._venta(self.banados), (350, 1, 30))

    def test_en_una_base_sin_cuchuflis_no_hace_nada(self):
        Producto.objects.filter(pk__in=[self.banados.pk, self.rellenos.pk]).delete()
        migracion.por_unidad(apps_reales, None)
        self.pregunta.refresh_from_db()
        self.alfajores.refresh_from_db()
        # Sin cuchuflis que cambiar, la pregunta del minimo tampoco se toca.
        self.assertEqual(self.pregunta.respuesta, RESPUESTA_MINIMO)
        self.assertEqual(self._venta(self.alfajores), (1590, 1, 0))


# --- 2. el sitio despues del cambio ---------------------------------------------

@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1490, BOX_MINIMO_TOTAL=10000,
                   DESPACHO_HORAS=48, SHIPPING_COST=0, BRAND_NAME="Dulcecita",
                   SITE_URL="https://dulcecita.cl")
class SitioPorUnidadTests(_ProduccionAntes):
    def setUp(self):
        super().setUp()
        self._migrar()

    def _ficha(self, slug):
        respuesta = self.client.get(f"/productos/{slug}/")
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    def _oferta(self, html):
        return next(n for n in _ld(html) if n.get("@type") == "Product")["offers"]

    # -- fichas --
    def test_la_ficha_de_los_banados_dice_350_por_unidad_desde_30(self):
        html = self._ficha("cuchuflis-banados")
        self.assertEqual(_title(html), "Cuchuflís bañados en chocolate desde $350 | Dulcecita")
        self.assertEqual(_faq(html)["¿Cuánto cuestan los cuchuflís bañados en chocolate?"],
                         "$350 por unidad, con chocolate o chocolate blanco.")
        self.assertIn("Se venden por unidad, desde 30", _meta(html))
        self.assertLessEqual(len(_meta(html)), 155)
        self.assertIn("Se venden por unidad, desde 30, y también puedes sumarlos a tu box.", html)

    def test_la_ficha_de_los_rellenos_dice_300_por_unidad_desde_30(self):
        html = self._ficha("cuchuflis-rellenos")
        self.assertEqual(_title(html), "Cuchuflís rellenos de manjar desde $300 | Dulcecita")
        self.assertEqual(_faq(html)["¿Cuánto cuestan los cuchuflís rellenos?"], "$300 por unidad.")
        self.assertIn("Se venden por unidad, desde 30", _meta(html))
        self.assertLessEqual(len(_meta(html)), 155)
        self.assertFalse(_meta(html).endswith("…"), "la description quedo cortada")

    def test_ninguna_pagina_vuelve_a_decir_bolsita(self):
        rutas = ["/", "/productos/", "/productos/cuchuflis-banados/", "/productos/cuchuflis-rellenos/",
                 "/productos/torta-de-cuchuflis/", "/navidad/", "/arma-tu-box/", "/corporativo/",
                 "/delivery/", "/carrito/"]
        for ruta in rutas:
            respuesta = self.client.get(ruta)
            self.assertEqual(respuesta.status_code, 200, ruta)
            self.assertNotIn("bolsita", respuesta.content.decode().lower(), ruta)

    def test_el_schema_declara_el_precio_la_unidad_y_el_minimo_nuevos(self):
        oferta = self._oferta(self._ficha("cuchuflis-banados"))
        self.assertEqual(oferta["price"], "350")
        self.assertEqual(oferta["eligibleQuantity"], {"@type": "QuantitativeValue", "minValue": 30,
                                                      "unitText": "unidad"})
        self.assertEqual(self._oferta(self._ficha("cuchuflis-rellenos"))["price"], "300")

    def test_por_mayor_no_promete_menos_que_el_minimo_del_producto(self):
        pregunta = "¿Venden por mayor?"
        self.assertTrue(_faq(self._ficha("cuchuflis-banados"))[pregunta].startswith("Sí, desde 30 unidades."))
        # Los demas siguen como los respondio la duena: desde 20.
        self.assertTrue(_faq(self._ficha("alfajores"))[pregunta].startswith("Sí, desde 20 unidades."))
        self.assertTrue(_faq(self._ficha("torta-de-cuchuflis"))[pregunta].startswith("Sí, desde 20 unidades."))

    # -- catalogo --
    def test_el_catalogo_muestra_350_y_300_y_agrega_de_a_30(self):
        cuerpo = _cuerpo(self.client.get("/productos/").content.decode())
        self.assertIn('<span data-precio="350">$350</span>', cuerpo)
        self.assertIn('<span data-precio="300">$300</span>', cuerpo)
        self.assertEqual(cuerpo.count("Agregar 30"), 2)
        self.assertNotIn("4 cuchuflís", cuerpo)
        self.assertIn("Pedido mínimo de 10 unidades por producto "
                      "(cuchuflís bañados y cuchuflís rellenos, desde 30).", cuerpo)

    def test_decir_el_minimo_propio_no_agrega_consultas(self):
        with CaptureQueriesContext(connection) as c:
            self.assertEqual(self.client.get("/productos/").status_code, 200)
        de_productos = [q for q in c.captured_queries if 'FROM "BebesitaAPP_producto"' in q["sql"]]
        # Una del catalogo y una del pie (que tambien alimenta el minimo propio).
        self.assertEqual(len(de_productos), 2, [q["sql"][:120] for q in de_productos])

    # -- carrito --
    def test_al_carrito_entran_30_y_bajar_de_30_los_saca(self):
        linea = f"{self.banados.id}-{self.choc.id}"
        datos = self.client.post(reverse("agregar_carrito_ajax", args=[linea])).json()
        self.assertEqual((datos["qty"], datos["total"]), (30, 30 * 350))
        datos = self.client.post(reverse("agregar_carrito_ajax", args=[linea])).json()
        self.assertEqual((datos["qty"], datos["total"]), (31, 31 * 350))
        self.client.post(reverse("decrementar_carrito_ajax", args=[linea]))
        datos = self.client.post(reverse("decrementar_carrito_ajax", args=[linea])).json()
        self.assertEqual(datos["qty"], 0)
        self.assertEqual(self.client.session["cart"], {})

    def test_el_carrito_avisa_que_los_cuchuflis_van_desde_30(self):
        self.client.post(reverse("agregar_carrito_ajax", args=[str(self.rellenos.id)]))
        html = self.client.get("/carrito/").content.decode()
        self.assertIn("(cuchuflís bañados y cuchuflís rellenos, desde 30)", html)
        # 30 x $300. El carrito imprime el total sin punto de miles (lo pone cart.js).
        self.assertIn('<p id="cart-total" class="cart-summary-total">$9000</p>', html)

    def test_el_pedido_cobra_350_por_cada_cuchufli(self):
        linea = f"{self.banados.id}-{self.blanco.id}"
        self.client.post(reverse("agregar_carrito_ajax", args=[linea]))
        respuesta = self.client.post(reverse("checkout"), data={
            "nombre": "Cliente", "email": "c@example.com", "telefono": "+56 9 1111 1111",
            "tipo_entrega": "retiro", "comuna_sector": "Santiago", "direccion": "Ref"})
        self.assertEqual(respuesta.status_code, 302)
        pedido = Pedido.objects.get()
        item = pedido.items.get()
        self.assertEqual((item.cantidad, int(item.precio), int(pedido.total)), (30, 350, 10500))

    # -- Navidad y box --
    def test_navidad_lista_los_cuchuflis_por_unidad(self):
        cuerpo = _cuerpo(self.client.get("/navidad/").content.decode())
        self.assertIn("Cuchuflís bañados en chocolate</a>: $350 por unidad", cuerpo)
        self.assertIn("Cuchuflís rellenos de manjar</a>: $300 por unidad", cuerpo)
        self.assertIn("Se piden desde 10 por producto (cuchuflís bañados y cuchuflís rellenos, desde 30)",
                      cuerpo)

    def test_el_box_cobra_el_precio_por_unidad(self):
        linea = f"{self.banados.id}-{self.choc.id}"
        alfajor = f"{self.alfajores.id}-{self.choc.id}"
        # 3 cuchuflis ($1.050) + 6 alfajores ($9.540) + empaque ($1.490) = $12.080.
        respuesta = self.client.post(reverse("arma_tu_box"), data={f"q-{linea}": 3, f"q-{alfajor}": 6})
        self.assertRedirects(respuesta, reverse("carrito"), fetch_redirect_response=False)
        html = self.client.get("/carrito/").content.decode()
        self.assertIn('<p id="cart-total" class="cart-summary-total">$12080</p>', html)
        self.assertNotIn("4 cuchuflís", self.client.get("/arma-tu-box/").content.decode())


# --- 3. el carrito que ya estaba armado -----------------------------------------

@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1490, BOX_MINIMO_TOTAL=10000,
                   SHIPPING_COST=0, BRAND_NAME="Dulcecita")
class CarritoViejoTests(_ProduccionAntes):
    """Un cliente dejo 10 bolsitas en el carrito y el sitio cambio a unidades."""

    DATOS = {"nombre": "Cliente", "email": "c@example.com", "telefono": "+56 9 1111 1111",
             "tipo_entrega": "retiro", "comuna_sector": "Santiago", "direccion": "Ref"}

    def setUp(self):
        super().setUp()
        self.linea = f"{self.banados.id}-{self.choc.id}"
        self.client.post(reverse("agregar_carrito_ajax", args=[self.linea]))
        self.assertEqual(self.client.session["cart"], {self.linea: 10})  # 10 bolsitas, $15.900
        self._migrar()

    def test_no_se_cobran_10_cuchuflis_sueltos(self):
        respuesta = self.client.post(reverse("checkout"), data=self.DATOS)
        self.assertRedirects(respuesta, reverse("carrito"), fetch_redirect_response=False)
        self.assertEqual(Pedido.objects.count(), 0)
        # La linea sube al minimo nuevo y el cliente lo ve en el carrito.
        self.assertEqual(self.client.session["cart"], {self.linea: 30})
        html = self.client.get("/carrito/").content.decode()
        self.assertIn("Cuchuflís bañados se vende desde 30 unidades", html)

    def test_tampoco_al_abrir_la_pagina_de_pago(self):
        respuesta = self.client.get(reverse("checkout"))
        self.assertRedirects(respuesta, reverse("carrito"), fetch_redirect_response=False)

    def test_despues_del_ajuste_se_paga_por_30(self):
        self.client.post(reverse("checkout"), data=self.DATOS)
        respuesta = self.client.post(reverse("checkout"), data=self.DATOS)
        self.assertEqual(respuesta.status_code, 302)
        pedido = Pedido.objects.get()
        self.assertEqual(int(pedido.total), 30 * 350)

    def test_una_linea_que_cumple_su_minimo_se_paga_normal(self):
        self.client.post(reverse("checkout"), data=self.DATOS)       # ajusta los cuchuflis
        self.client.post(reverse("agregar_carrito_ajax", args=[f"{self.alfajores.id}-{self.choc.id}"]))
        self.client.post(reverse("checkout"), data=self.DATOS)
        pedido = Pedido.objects.get()
        self.assertEqual(int(pedido.total), 30 * 350 + 10 * 1590)
