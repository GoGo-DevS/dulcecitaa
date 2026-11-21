"""Migracion 0021: un solo pan de pascua y sin duplicados (20-11-2026).

Parte del estado de PRODUCCION del 20-11, visto en el sitio: dos "PAN DE PASCUA" a
$8.500 (pan-de-pascua oculto, pan-de-pascua-2 a la vista) y dos tortas (la original
y torta-de-cuchuflis-2), y le pasa la migracion.
"""
import importlib
import shutil
import tempfile

from django.apps import apps as apps_reales
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Pedido, PedidoItem, Producto, ProductoImagen, RedireccionProducto

migracion = importlib.import_module("BebesitaAPP.migrations.0021_pan_de_pascua_unico")
TEXTO_DUENA = ("Disfruta el sabor de la Navidad con nuestro delicioso Pan de Pascua, preparado con "
               "dedicación, cariño y ese toque casero que lo hace especial.")


def _foto(nombre="x.jpg"):
    return SimpleUploadedFile(nombre, b"img", content_type="image/jpeg")


@override_settings(SITE_URL="https://dulcecita.cl", BRAND_NAME="Dulcecita")
class PanUnicoTests(TestCase):

    def setUp(self):
        self._media = tempfile.mkdtemp(prefix="dulcecita-mig-pan-")
        self._ajuste = override_settings(MEDIA_ROOT=self._media)
        self._ajuste.enable()
        crear = lambda **k: Producto.objects.create(minimo=1, imagen=_foto(), **k)
        self.pan = crear(nombre="PAN DE PASCUA", slug="pan-de-pascua", precio=8500, descripcion=TEXTO_DUENA,
                         visible=False)
        self.pan2 = crear(nombre="PAN DE PASCUA", slug="pan-de-pascua-2", precio=8500,
                          descripcion=TEXTO_DUENA, visible=True)
        self.torta = crear(nombre="Torta de cuchuflís", slug="torta-de-cuchuflis", precio=14990,
                           descripcion="Torta armada con cuchuflís.", visible=True)
        self.torta2 = crear(nombre="Torta de cuchuflís", slug="torta-de-cuchuflis-2", precio=14990,
                            descripcion="Torta armada con cuchuflís.", visible=True)

    def tearDown(self):
        self._ajuste.disable()
        shutil.rmtree(self._media, ignore_errors=True)

    def _migrar(self):
        migracion.adelante(apps_reales, None)

    def test_queda_un_solo_pan_igual_a_lo_que_se_promociona(self):
        self._migrar()
        panes = Producto.objects.filter(slug__startswith="pan-de-pascua")
        self.assertEqual([p.slug for p in panes], ["pan-de-pascua"])
        pan = panes.get()
        self.assertEqual(pan.nombre, "Pan de pascua")
        self.assertEqual(pan.precio, 8590)
        self.assertTrue(pan.visible)
        self.assertTrue(pan.descripcion.startswith("Pan de pascua artesanal en formato de medio kilo."))
        self.assertIn(TEXTO_DUENA, pan.descripcion)  # el texto de la duena se conserva

    def test_el_pan_queda_con_su_foto_y_tres_extras(self):
        self._migrar()
        pan = Producto.objects.get(slug="pan-de-pascua")
        self.assertIn("pan-de-pascua-artesanal", pan.imagen.name)
        extras = sorted(i.imagen.name for i in ProductoImagen.objects.filter(producto=pan))
        self.assertEqual(len(extras), 3)
        for parte in ("en-su-molde", "envasado", "pesado"):
            self.assertTrue(any(parte in e for e in extras), parte)

    def test_las_direcciones_duplicadas_redirigen_301(self):
        self._migrar()
        for viejo, queda in (("pan-de-pascua-2", "pan-de-pascua"), ("torta-de-cuchuflis-2", "torta-de-cuchuflis")):
            r = self.client.get(reverse("producto_ficha", args=[viejo]))
            self.assertEqual(r.status_code, 301, viejo)
            self.assertEqual(r["Location"], reverse("producto_ficha", args=[queda]), viejo)
        self.assertEqual(RedireccionProducto.objects.count(), 2)

    def test_el_catalogo_muestra_un_pan_y_una_torta(self):
        self._migrar()
        html = self.client.get("/productos/").content.decode()
        self.assertEqual(html.count('href="/productos/pan-de-pascua/"') > 0, True)
        self.assertNotIn('href="/productos/pan-de-pascua-2/"', html)
        self.assertNotIn('href="/productos/torta-de-cuchuflis-2/"', html)

    def test_un_duplicado_con_ventas_se_oculta_y_no_se_borra(self):
        pedido = Pedido.objects.create(nombre_cliente="Ana", email_cliente="a@example.com",
                                       telefono="+56911111111", direccion="x", total=8500)
        linea = PedidoItem.objects.create(pedido=pedido, producto=self.pan2, cantidad=1, precio=8500)
        self._migrar()
        self.assertTrue(PedidoItem.objects.filter(pk=linea.pk, producto=self.pan2).exists())
        self.assertFalse(Producto.objects.get(pk=self.pan2.pk).visible)
        self.assertFalse(RedireccionProducto.objects.filter(slug="pan-de-pascua-2").exists())
        self.assertTrue(Producto.objects.get(slug="pan-de-pascua").visible)

    def test_correrla_dos_veces_no_duplica_nada(self):
        self._migrar()
        self._migrar()
        pan = Producto.objects.get(slug="pan-de-pascua")
        self.assertEqual(ProductoImagen.objects.filter(producto=pan).count(), 3)
        self.assertEqual(pan.descripcion.count("formato de medio kilo"), 1)
        self.assertEqual(RedireccionProducto.objects.count(), 2)

    def test_si_solo_existe_el_dos_se_arregla_ese_y_no_se_borra(self):
        Producto.objects.filter(pk=self.pan.pk).delete()
        self._migrar()
        pan2 = Producto.objects.get(pk=self.pan2.pk)
        self.assertEqual((pan2.nombre, pan2.precio, pan2.visible), ("Pan de pascua", 8590, True))
