"""catalogo_inicial no recrea productos ni oculta la tienda (21-11-2026), y la migracion 0022.

Lo que paso: el build de Render corre `catalogo_inicial` en CADA deploy. Buscaba la
torta por su nombre exacto y, como la duena la llamo "TORTA CUCHUFLIS", la creaba otra
vez (torta-de-cuchuflis-2, dos veces). Y decidia si "el catalogo ya estaba cargado" por
los nombres de los 4 productos de fabrica: con los 4 renombrados, ocultaba toda la
tienda y recreaba el catalogo viejo. Ya iban 2 de 4 en mayusculas.
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

from BebesitaAPP.models import Pedido, PedidoItem, Producto, RedireccionProducto

migracion = importlib.import_module("BebesitaAPP.migrations.0022_torta_unica_y_nombres")


def _foto():
    return SimpleUploadedFile("x.jpg", b"img", content_type="image/jpeg")


class _Base(TestCase):
    def setUp(self):
        self._media = tempfile.mkdtemp(prefix="dulcecita-catalogo-")
        self._ajuste = override_settings(MEDIA_ROOT=self._media)
        self._ajuste.enable()

    def tearDown(self):
        self._ajuste.disable()
        shutil.rmtree(self._media, ignore_errors=True)

    def _crear(self, nombre, slug, **k):
        return Producto.objects.create(nombre=nombre, slug=slug, precio=k.pop("precio", 1000), descripcion="x",
                                       visible=k.pop("visible", True), minimo=1, imagen=_foto(), **k)

    def _correr(self):
        call_command("catalogo_inicial", stdout=io.StringIO())


class CatalogoInicialNoPisaLaTienda(_Base):

    def setUp(self):
        super().setUp()
        # Los 4 de fabrica renombrados en mayusculas + la torta renombrada + el pan.
        for nombre, slug in (("BARQUILLOS RELLENOS", "barquillos-rellenos-banados-en-chocolate"),
                             ("ALFAJORES", "alfajores"), ("CUCHUFLIS BAÑADOS", "cuchuflis-banados"),
                             ("CUCHUFLIS RELLENOS", "cuchuflis-rellenos"), ("TORTA CUCHUFLIS", "torta-de-cuchuflis"),
                             ("Pan de pascua", "pan-de-pascua")):
            self._crear(nombre, slug)

    def test_con_todos_los_nombres_cambiados_no_oculta_ni_crea_nada(self):
        antes = list(Producto.objects.order_by("pk").values_list("pk", "nombre", "visible"))
        self._correr()
        self.assertEqual(list(Producto.objects.order_by("pk").values_list("pk", "nombre", "visible")), antes)

    def test_la_torta_renombrada_no_se_vuelve_a_crear(self):
        self._correr()
        self._correr()
        self.assertEqual(Producto.objects.filter(slug__startswith="torta-de-cuchuflis").count(), 1)


class TortaBorradaAProposito(_Base):

    def test_si_la_borraron_desde_el_panel_no_vuelve(self):
        self._crear("Alfajores", "alfajores")
        RedireccionProducto.objects.create(slug="torta-de-cuchuflis", nombre="Torta de cuchuflís")
        self._correr()
        self.assertFalse(Producto.objects.filter(slug__startswith="torta-de-cuchuflis").exists())


class FabricaBorradaAProposito(_Base):

    def test_si_borraron_los_cuatro_desde_el_panel_no_se_recarga_el_catalogo_viejo(self):
        pan = self._crear("Pan de pascua", "pan-de-pascua")
        for slug in ("barquillos-rellenos-banados-en-chocolate", "alfajores", "cuchuflis-banados", "cuchuflis-rellenos"):
            RedireccionProducto.objects.create(slug=slug, nombre=slug, destino=pan)
        self._correr()
        self.assertTrue(Producto.objects.get(pk=pan.pk).visible)
        self.assertFalse(Producto.objects.filter(slug="alfajores").exists())


class Migracion0022(_Base):

    def setUp(self):
        super().setUp()
        self.torta = self._crear("TORTA CUCHUFLIS", "torta-de-cuchuflis", precio=14990)
        self.dup = self._crear("Torta de cuchuflís", "torta-de-cuchuflis-2", precio=14990)
        self.alfajores = self._crear("ALFAJORES", "alfajores")
        self.rellenos = self._crear("CUCHUFLIS RELLENOS", "cuchuflis-rellenos")
        self.banados = self._crear("Cuchuflís bañados premium", "cuchuflis-banados")  # nombre propio de ella

    def _migrar(self):
        migracion.adelante(apps_reales, None)

    def test_borra_la_torta_duplicada_y_su_direccion_redirige(self):
        self._migrar()
        self.assertFalse(Producto.objects.filter(pk=self.dup.pk).exists())
        r = self.client.get(reverse("producto_ficha", args=["torta-de-cuchuflis-2"]))
        self.assertEqual((r.status_code, r["Location"]), (301, reverse("producto_ficha", args=["torta-de-cuchuflis"])))

    def test_los_nombres_en_mayusculas_vuelven_a_escribirse_normal(self):
        self._migrar()
        nombres = dict(Producto.objects.values_list("slug", "nombre"))
        self.assertEqual(nombres["torta-de-cuchuflis"], "Torta de cuchuflís")
        self.assertEqual(nombres["alfajores"], "Alfajores")
        self.assertEqual(nombres["cuchuflis-rellenos"], "Cuchuflís rellenos")
        self.assertEqual(nombres["cuchuflis-banados"], "Cuchuflís bañados premium")  # no estaba en mayusculas

    def test_una_torta_duplicada_con_ventas_se_oculta_y_no_se_borra(self):
        pedido = Pedido.objects.create(nombre_cliente="Ana", email_cliente="a@example.com",
                                       telefono="+56911111111", direccion="x", total=14990)
        linea = PedidoItem.objects.create(pedido=pedido, producto=self.dup, cantidad=1, precio=14990)
        self._migrar()
        self.assertTrue(PedidoItem.objects.filter(pk=linea.pk, producto=self.dup).exists())
        self.assertFalse(Producto.objects.get(pk=self.dup.pk).visible)

    def test_despues_de_migrar_el_build_no_la_recrea(self):
        self._migrar()
        call_command("catalogo_inicial", stdout=io.StringIO())
        self.assertEqual(Producto.objects.filter(slug__startswith="torta-de-cuchuflis").count(), 1)
