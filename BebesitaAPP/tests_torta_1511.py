"""Precios de la torta de cuchuflis confirmados por la duena (15-11-2026).

    50 cuchuflis    sin cobertura $14.990    con cobertura $17.490
    100 cuchuflis   sin cobertura $29.990    con cobertura $34.990

Cambia uno solo (50 con cobertura: $17.990 -> $17.490). Las pruebas parten de
la torta COMO ESTA HOY en produccion y le pasan la migracion 0019: lo que se
comprueba es el precio que queda publicado y el que cobra el carrito.
"""
import importlib
import io
import shutil
import tempfile

from django.apps import apps as apps_reales
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Opcion, PrecioCombinacion, Producto
from .tests_tanda_0311 import _faq, _ld

migracion = importlib.import_module("BebesitaAPP.migrations.0019_torta_precios_confirmados")

HOY_EN_PRODUCCION = {"50 sin": 14990, "50 chocolate": 17990, "50 blanco": 17990,
                     "100 sin": 29990, "100 chocolate": 34990, "100 blanco": 34990}
CONFIRMADOS = {"50 sin": 14990, "50 chocolate": 17490, "50 blanco": 17490,
               "100 sin": 29990, "100 chocolate": 34990, "100 blanco": 34990}


@override_settings(MINIMO_UNIDADES=10, DESPACHO_HORAS=48, SHIPPING_COST=0, BRAND_NAME="Dulcecita",
                   SITE_URL="https://dulcecita.cl")
class TortaPreciosTests(TestCase):
    def setUp(self):
        foto = SimpleUploadedFile("a.jpg", b"img", content_type="image/jpeg")
        self.torta = Producto.objects.create(
            nombre="Torta de cuchuflís", descripcion="Torta armada con cuchuflís.", precio=14990,
            visible=True, minimo=1, en_box=False, pide_nota=True, imagen=foto)
        self.tamanos = {"50": Opcion.objects.create(tipo="tamano", nombre="50 cuchuflís", orden=1),
                        "100": Opcion.objects.create(tipo="tamano", nombre="100 cuchuflís", orden=2)}
        self.coberturas = {"sin": Opcion.objects.create(tipo="cobertura", nombre="Sin cobertura", orden=0),
                           "chocolate": Opcion.objects.create(tipo="cobertura", nombre="Chocolate", orden=1),
                           "blanco": Opcion.objects.create(tipo="cobertura", nombre="Chocolate blanco", orden=2)}
        self.torta.opciones.add(*self.tamanos.values(), *self.coberturas.values())
        self.combos = {}
        for clave, precio in HOY_EN_PRODUCCION.items():
            tamano, cobertura = clave.split()
            combo = PrecioCombinacion.objects.create(producto=self.torta, precio=precio)
            combo.opciones.set([self.tamanos[tamano], self.coberturas[cobertura]])
            combo.actualizar_clave()
            self.combos[clave] = combo
        self.alfajores = Producto.objects.create(nombre="Alfajores", descripcion="x", precio=1590,
                                                 visible=True, imagen=foto)

    def _precios(self):
        return {clave: PrecioCombinacion.objects.get(pk=combo.pk).precio for clave, combo in self.combos.items()}

    def _linea(self, tamano, cobertura):
        ids = sorted([self.tamanos[tamano].pk, self.coberturas[cobertura].pk])
        return "-".join(str(x) for x in [self.torta.pk, *ids])

    # -- la migracion --
    def test_deja_los_cuatro_precios_confirmados(self):
        migracion.confirmados(apps_reales, None)
        self.assertEqual(self._precios(), CONFIRMADOS)

    def test_el_unico_que_cambia_es_la_de_50_con_cobertura(self):
        migracion.confirmados(apps_reales, None)
        cambiados = {clave for clave, precio in self._precios().items() if precio != HOY_EN_PRODUCCION[clave]}
        self.assertEqual(cambiados, {"50 chocolate", "50 blanco"})

    def test_corrige_un_precio_que_se_hubiera_movido_a_mano(self):
        PrecioCombinacion.objects.filter(pk=self.combos["100 sin"].pk).update(precio=27990)
        migracion.confirmados(apps_reales, None)
        self.assertEqual(self._precios(), CONFIRMADOS)

    def test_dos_veces_da_lo_mismo_y_se_puede_deshacer(self):
        migracion.confirmados(apps_reales, None)
        migracion.confirmados(apps_reales, None)
        self.assertEqual(self._precios(), CONFIRMADOS)
        migracion.anteriores(apps_reales, None)
        self.assertEqual(self._precios(), HOY_EN_PRODUCCION)

    def test_un_tamano_que_no_esta_en_la_tabla_no_se_toca(self):
        t200 = Opcion.objects.create(tipo="tamano", nombre="200 cuchuflís", orden=3)
        self.torta.opciones.add(t200)
        especial = PrecioCombinacion.objects.create(producto=self.torta, precio=65000)
        especial.opciones.set([t200, self.coberturas["chocolate"]])
        especial.actualizar_clave()
        migracion.confirmados(apps_reales, None)
        especial.refresh_from_db()
        self.assertEqual(especial.precio, 65000)

    def test_no_toca_otros_productos_ni_falla_sin_torta(self):
        migracion.confirmados(apps_reales, None)
        self.alfajores.refresh_from_db()
        self.torta.refresh_from_db()
        self.assertEqual((self.alfajores.precio, self.torta.precio), (1590, 14990))
        Producto.objects.filter(pk=self.torta.pk).delete()
        migracion.confirmados(apps_reales, None)  # base sin torta: no hace nada

    # -- lo que queda publicado y lo que se cobra --
    def test_la_ficha_publica_los_cuatro_precios(self):
        migracion.confirmados(apps_reales, None)
        html = self.client.get("/productos/torta-de-cuchuflis/").content.decode()
        self.assertEqual(
            _faq(html)["¿Cuánto vale una torta de cuchuflís?"],
            "50 cuchuflís: sin cobertura, $14.990; chocolate o chocolate blanco, $17.490. "
            "100 cuchuflís: sin cobertura, $29.990; chocolate o chocolate blanco, $34.990.")
        self.assertNotIn("17.990", html)
        oferta = next(n for n in _ld(html) if n.get("@type") == "Product")["offers"]
        self.assertEqual(oferta["price"], "14990")

    def test_el_carrito_cobra_cada_combinacion_a_su_precio(self):
        migracion.confirmados(apps_reales, None)
        esperado = {("50", "sin"): 14990, ("50", "chocolate"): 17490, ("50", "blanco"): 17490,
                    ("100", "sin"): 29990, ("100", "chocolate"): 34990, ("100", "blanco"): 34990}
        for (tamano, cobertura), precio in esperado.items():
            cliente = self.client_class()
            datos = cliente.post(reverse("agregar_carrito_ajax", args=[self._linea(tamano, cobertura)])).json()
            self.assertEqual((datos["qty"], datos["total"]), (1, precio), (tamano, cobertura))

    def test_el_selector_de_la_ficha_lleva_los_precios_nuevos(self):
        migracion.confirmados(apps_reales, None)
        self.torta.refresh_from_db()
        precios = set(__import__("json").loads(self.torta.precios_json()).values())
        self.assertEqual(precios, {14990, 17490, 29990, 34990})


class CatalogoInicialTortaTests(TestCase):
    """Una base nueva nace con los mismos precios que deja la migracion."""

    def setUp(self):
        self._media = tempfile.mkdtemp(prefix="dulcecita-torta-")
        self._ajuste = override_settings(MEDIA_ROOT=self._media)
        self._ajuste.enable()

    def tearDown(self):
        self._ajuste.disable()
        shutil.rmtree(self._media, ignore_errors=True)

    def test_la_torta_nueva_trae_los_precios_confirmados(self):
        call_command("catalogo_inicial", stdout=io.StringIO())
        torta = Producto.objects.get(nombre="Torta de cuchuflís")
        self.assertEqual(sorted(torta.precios_combinacion.values_list("precio", flat=True)),
                         [14990, 17490, 17490, 29990, 34990, 34990])
        antes = sorted(torta.precios_combinacion.values_list("precio", flat=True))
        migracion.confirmados(apps_reales, None)
        self.assertEqual(sorted(torta.precios_combinacion.values_list("precio", flat=True)), antes)
