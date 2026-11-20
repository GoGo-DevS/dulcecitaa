"""Eliminar productos y fotos extra desde el panel; noindex de los ocultos (20-11-2026).

Tamara no podia borrar productos y creaba duplicados (pan-de-pascua-2,
torta-de-cuchuflis-2). Lo que se prueba:

- Lo que NO tiene historia se borra con sus fotos, precios, variantes y
  carritos, y su direccion vieja queda con 301 al destino elegido.
- Lo que SI tiene historia (pedidos de la web, cajas o componentes del panel,
  costo cargado) se ARCHIVA y la linea de pedido sigue con su producto. Esta es
  la prueba de la plata: si la vista llamara delete() a secas, la linea de
  pedido se iria con el producto (CASCADE) y la prueba falla.
- Nunca un 500, ni con PROTECT. Un GET no borra nada.
- Las fotos extra se suben, se achican como la principal, salen en el carrusel
  de la ficha y se pueden quitar.
- Un producto oculto responde 200 con noindex y no va en el sitemap.
"""
import shutil
import tempfile
from io import BytesIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from BebesitaAPP.models import (
    Carrito,
    CarritoItem,
    Opcion,
    Pedido,
    PedidoItem,
    PrecioCombinacion,
    PreguntaFrecuente,
    Producto,
    ProductoImagen,
    RedireccionProducto,
)

from .models import Cliente, Componente, CostoProducto
from .models import Pedido as PedidoPanel
from .models import PedidoItem as CajaPanel

MEDIA_PRUEBA = tempfile.mkdtemp(prefix="dulcecita-borrar-fotos-")
NOINDEX = '<meta name="robots" content="noindex, follow">'
INDEX = '<meta name="robots" content="index, follow, max-image-preview:large">'


def tearDownModule():
    shutil.rmtree(MEDIA_PRUEBA, ignore_errors=True)


def _foto(ancho=40, alto=30, nombre="foto.jpg", formato="JPEG"):
    salida = BytesIO()
    Image.new("RGB", (ancho, alto), (200, 120, 160)).save(salida, formato)
    return SimpleUploadedFile(nombre, salida.getvalue(),
                              content_type="image/jpeg" if formato == "JPEG" else "image/png")


@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1490, BOX_MINIMO_TOTAL=0, SHIPPING_COST=0,
                   BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl", MEDIA_ROOT=MEDIA_PRUEBA)
class _Base(TestCase):
    def setUp(self):
        self.duena = get_user_model().objects.create_user("tamara", "t@example.com", "clave-larga-123")
        self.client.force_login(self.duena)
        self.alfajores = self._crear("Alfajores", 1590, orden=1)
        self.barquillos = self._crear("Barquillos", 990, orden=2)
        # Como en produccion: el original oculto y el duplicado a la vista.
        self.pan = self._crear("Pan de pascua", 8990, orden=3, visible=False)
        self.pan2 = self._crear("Pan de pascua", 8990, orden=4)
        self.assertEqual((self.pan.slug, self.pan2.slug), ("pan-de-pascua", "pan-de-pascua-2"))

    @staticmethod
    def _crear(nombre, precio, **extra):
        return Producto.objects.create(nombre=nombre, descripcion="Texto de la duena", precio=precio,
                                       imagen=_foto(nombre="original.jpg"), **extra)

    def _url(self, producto):
        return reverse("gestion:producto_eliminar", args=[producto.pk])

    def _eliminar(self, producto, **datos):
        return self.client.post(self._url(producto), data={"confirmar": "si", **datos}, follow=True)

    def _existe(self, producto):
        return Producto.objects.filter(pk=producto.pk).exists()

    def _pedido_web(self, producto):
        pedido = Pedido.objects.create(nombre_cliente="Ana", email_cliente="a@example.com",
                                       telefono="+56911111111", direccion="x", total=89900)
        return PedidoItem.objects.create(pedido=pedido, producto=producto, cantidad=10, precio=8990)


class AccesoTests(_Base):
    def test_las_rutas_nuevas_piden_login_y_no_cambian_nada(self):
        foto = ProductoImagen.objects.create(producto=self.pan2, imagen=_foto())
        self.client.logout()
        rutas = [("get", self._url(self.pan2), None),
                 ("post", self._url(self.pan2), {"confirmar": "si"}),
                 ("post", reverse("gestion:producto_editar", args=[self.pan2.pk]), {"quitar_foto": foto.pk})]
        for metodo, url, datos in rutas:
            respuesta = getattr(self.client, metodo)(url, data=datos)
            self.assertEqual(respuesta.status_code, 302, url)
            self.assertIn("/panel/login/", respuesta["Location"], url)
        self.assertTrue(self._existe(self.pan2))
        self.assertTrue(ProductoImagen.objects.filter(pk=foto.pk).exists())
        self.assertFalse(RedireccionProducto.objects.exists())

    def test_una_variante_no_tiene_pantalla_de_eliminar(self):
        variante = self._crear("Pan chico", 4990, variante_de=self.pan2, variante_nombre="Chico")
        self.assertEqual(self.client.get(self._url(variante)).status_code, 404)
        self.assertEqual(self.client.post(self._url(variante), {"confirmar": "si"}).status_code, 404)
        self.assertTrue(self._existe(variante))


class BorrarSinHistoriaTests(_Base):
    def setUp(self):
        super().setUp()
        self.fotos = [ProductoImagen.objects.create(producto=self.pan2, imagen=_foto()) for _ in range(2)]
        self.grande = Opcion.objects.create(tipo="tamano", nombre="1 kilo", orden=1)
        self.chico = Opcion.objects.create(tipo="tamano", nombre="500 g", orden=2)
        self.pan2.opciones.add(self.grande, self.chico)
        self.combos = []
        for opcion, precio in [(self.grande, 8990), (self.chico, 4990)]:
            combo = PrecioCombinacion.objects.create(producto=self.pan2, precio=precio)
            combo.opciones.set([opcion])
            combo.actualizar_clave()
            self.combos.append(combo)
        self.variante = self._crear("Pan de pascua sin pasas", 8990, variante_de=self.pan2,
                                    variante_nombre="Sin pasas")
        self.pregunta = PreguntaFrecuente.objects.create(producto=self.pan2, pregunta="¿Trae pasas?",
                                                         respuesta="Sí, y nueces.")
        self.carrito = CarritoItem.objects.create(carrito=Carrito.objects.create(), producto=self.pan2,
                                                  cantidad=10)

    def test_get_dice_lo_que_va_a_pasar_y_no_borra(self):
        respuesta = self.client.get(self._url(self.pan2))
        self.assertContains(respuesta, "Se va a borrar para siempre")
        self.assertContains(respuesta, "su foto principal, 2 fotos extra, 2 precios por combinación, "
                                       "1 variante, 1 pregunta frecuente de su ficha y "
                                       "1 línea de un carrito guardado")
        self.assertContains(respuesta, "/productos/pan-de-pascua-2/")
        self.assertContains(respuesta, 'name="confirmar" value="si"')
        self.assertContains(respuesta, '<option value="catalogo" selected>')
        # El oculto no se ofrece como destino: la direccion vieja no lleva a algo que no se vende.
        self.assertNotContains(respuesta, f'<option value="{self.pan.pk}"')
        self.assertTrue(self._existe(self.pan2))

    def test_post_sin_confirmar_no_borra(self):
        self.assertEqual(self.client.post(self._url(self.pan2), {"destino": "catalogo"}).status_code, 200)
        self.assertTrue(self._existe(self.pan2))
        self.assertFalse(RedireccionProducto.objects.exists())

    def test_se_borra_con_fotos_precios_variantes_preguntas_y_carritos(self):
        respuesta = self._eliminar(self.pan2, destino=self.alfajores.pk)
        self.assertContains(respuesta, "«Pan de pascua» eliminado, junto con 2 fotos extra, "
                                       "2 precios por combinación, 1 variante")
        self.assertContains(respuesta, "Quien entre a /productos/pan-de-pascua-2/ llega a «Alfajores» "
                                       "(/productos/alfajores/)")
        self.assertFalse(self._existe(self.pan2))
        self.assertFalse(self._existe(self.variante))
        self.assertFalse(ProductoImagen.objects.filter(pk__in=[f.pk for f in self.fotos]).exists())
        self.assertFalse(PrecioCombinacion.objects.filter(pk__in=[c.pk for c in self.combos]).exists())
        self.assertFalse(PreguntaFrecuente.objects.filter(pk=self.pregunta.pk).exists())
        self.assertFalse(CarritoItem.objects.filter(pk=self.carrito.pk).exists())
        # Lo compartido y lo ajeno no se toca.
        self.assertEqual(Opcion.objects.filter(pk__in=[self.grande.pk, self.chico.pk]).count(), 2)
        self.assertTrue(all(self._existe(p) for p in (self.alfajores, self.barquillos, self.pan)))
        registro = RedireccionProducto.objects.get()
        self.assertEqual((registro.slug, registro.pk_antiguo, registro.nombre, registro.destino,
                          registro.borrado_por),
                         ("pan-de-pascua-2", self.pan2.pk, "Pan de pascua", self.alfajores, "tamara"))

    def test_la_direccion_vieja_responde_301_al_destino_elegido(self):
        self._eliminar(self.pan2, destino=self.alfajores.pk)
        publico = self.client_class()
        respuesta = publico.get("/productos/pan-de-pascua-2/")
        self.assertEqual(respuesta.status_code, 301)
        self.assertEqual(respuesta["Location"], "/productos/alfajores/")
        # La direccion vieja con numero tampoco cae en un 404.
        respuesta = publico.get(f"/producto/{self.pan2.pk}/")
        self.assertEqual((respuesta.status_code, respuesta["Location"]), (301, "/productos/alfajores/"))
        # Los ?utm= de un enlace compartido se conservan.
        respuesta = publico.get("/productos/pan-de-pascua-2/?utm_source=whatsapp")
        self.assertEqual(respuesta["Location"], "/productos/alfajores/?utm_source=whatsapp")

    def test_sin_elegir_lleva_al_catalogo(self):
        self._eliminar(self.pan2)
        respuesta = self.client_class().get("/productos/pan-de-pascua-2/")
        self.assertEqual((respuesta.status_code, respuesta["Location"]), (301, "/productos/"))

    def test_un_destino_que_no_vale_no_borra(self):
        for malo in (self.pan.pk, self.pan2.pk, self.variante.pk, "abc", 999999):
            respuesta = self._eliminar(self.pan2, destino=malo)
            self.assertContains(respuesta, "Elige a dónde lleva la dirección antigua")
        self.assertTrue(self._existe(self.pan2))
        self.assertFalse(RedireccionProducto.objects.exists())

    def test_si_el_destino_se_oculta_la_direccion_cae_al_catalogo(self):
        self._eliminar(self.pan2, destino=self.alfajores.pk)
        Producto.objects.filter(pk=self.alfajores.pk).update(visible=False)
        self.assertEqual(self.client_class().get("/productos/pan-de-pascua-2/")["Location"], "/productos/")

    def test_borrar_el_destino_mueve_las_direcciones_que_llevaban_a_el(self):
        self._eliminar(self.pan2, destino=self.alfajores.pk)
        self._eliminar(self.alfajores, destino=self.barquillos.pk)
        publico = self.client_class()
        # Un solo salto, sin cadena de 301 ni flecha a la nada.
        self.assertEqual(publico.get("/productos/pan-de-pascua-2/")["Location"], "/productos/barquillos/")
        self.assertEqual(publico.get("/productos/alfajores/")["Location"], "/productos/barquillos/")

    def test_una_direccion_que_nunca_existio_sigue_en_404(self):
        publico = self.client_class()
        self.assertEqual(publico.get("/productos/no-existe/").status_code, 404)
        self.assertEqual(publico.get("/producto/999999/").status_code, 404)


class NoSeBorraConHistoriaTests(_Base):
    """La plata: un producto vendido NUNCA se borra, se archiva."""

    def test_con_un_pedido_web_se_archiva_y_la_linea_queda_con_su_producto(self):
        linea = self._pedido_web(self.pan2)
        respuesta = self._eliminar(self.pan2, destino=self.alfajores.pk)
        # Primero la plata: si el producto se hubiera borrado, la linea se fue con
        # el (CASCADE) y esto falla con DoesNotExist.
        linea.refresh_from_db()
        self.assertEqual((linea.producto_id, linea.cantidad, linea.precio), (self.pan2.pk, 10, 8990))
        self.assertEqual(Pedido.objects.get(pk=linea.pedido_id).total, 89900)
        self.assertTrue(self._existe(self.pan2))
        self.pan2.refresh_from_db()
        self.assertFalse(self.pan2.visible)
        self.assertContains(respuesta, "«Pan de pascua» no se borró porque está en 1 pedido de la web")
        self.assertContains(respuesta, "Quedó archivado")
        self.assertFalse(RedireccionProducto.objects.exists())
        # Archivado no es 404: su pagina sigue, pero fuera de Google.
        ficha = self.client_class().get("/productos/pan-de-pascua-2/")
        self.assertEqual(ficha.status_code, 200)
        self.assertContains(ficha, NOINDEX)

    def test_el_pedido_de_una_variante_tambien_cuenta(self):
        variante = self._crear("Pan de pascua sin pasas", 8990, variante_de=self.pan2, variante_nombre="Sin pasas")
        linea = self._pedido_web(variante)
        self._eliminar(self.pan2)
        self.assertTrue(self._existe(self.pan2))
        self.assertTrue(self._existe(variante))
        self.assertTrue(PedidoItem.objects.filter(pk=linea.pk, producto=variante).exists())

    def test_get_explica_por_que_y_ofrece_archivar(self):
        self._pedido_web(self.pan2)
        CostoProducto.objects.create(producto=self.pan2, costo_unidad=3000)
        respuesta = self.client.get(self._url(self.pan2))
        self.assertContains(respuesta, "No se puede borrar: se va a archivar")
        self.assertContains(respuesta, "está en 1 pedido de la web y tiene su costo por unidad cargado")
        self.assertContains(respuesta, ">Archivar</button>")
        self.assertNotContains(respuesta, "Sí, eliminar para siempre")

    def test_la_caja_de_un_pedido_del_panel_se_conserva(self):
        pedido = PedidoPanel.objects.create(cliente=Cliente.objects.create(nombre="AZA"))
        caja = CajaPanel.objects.create(pedido=pedido, producto=self.pan2, descripcion="Caja navidad",
                                        cantidad=5, precio_unitario=12000)
        respuesta = self._eliminar(self.pan2)
        self.assertContains(respuesta, "es la caja de 1 pedido del panel")
        caja.refresh_from_db()
        self.assertEqual(caja.producto_id, self.pan2.pk)  # SET_NULL lo habria dejado en None

    def test_el_costo_cargado_se_conserva(self):
        costo = CostoProducto.objects.create(producto=self.pan2, costo_unidad=3000)
        self._eliminar(self.pan2)
        self.assertTrue(CostoProducto.objects.filter(pk=costo.pk, producto=self.pan2).exists())
        self.pan2.refresh_from_db()
        self.assertFalse(self.pan2.visible)

    def test_un_componente_protegido_se_archiva_sin_500(self):
        pedido = PedidoPanel.objects.create(cliente=Cliente.objects.create(nombre="AZA"))
        caja = CajaPanel.objects.create(pedido=pedido, descripcion="Caja mixta", cantidad=1)
        componente = Componente.objects.create(item=caja, producto=self.pan2, cantidad=4)
        respuesta = self.client.post(self._url(self.pan2), {"confirmar": "si"})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Componente.objects.filter(pk=componente.pk, producto=self.pan2).exists())
        self.pan2.refresh_from_db()
        self.assertFalse(self.pan2.visible)

    def test_si_django_levanta_protectederror_no_hay_500(self):
        # Se apaga historial() para que el borrado llegue hasta Django y el
        # PROTECT del componente levante ProtectedError de verdad.
        pedido = PedidoPanel.objects.create(cliente=Cliente.objects.create(nombre="AZA"))
        caja = CajaPanel.objects.create(pedido=pedido, descripcion="Caja mixta", cantidad=1)
        Componente.objects.create(item=caja, producto=self.pan2, cantidad=4)
        with mock.patch("gestion.productos.historial", return_value=[]):
            respuesta = self._eliminar(self.pan2)
        self.assertEqual(respuesta.redirect_chain, [(reverse("gestion:productos"), 302)])
        self.assertContains(respuesta, "no se borró porque hay datos que dependen de él")
        self.assertTrue(self._existe(self.pan2))
        self.assertFalse(RedireccionProducto.objects.exists())

    def test_la_red_de_seguridad_ve_lo_que_historial_no_ve(self):
        # Si historial() se olvidara de un modelo, el recolector de Django igual
        # ve que la linea de pedido se iria con el producto, y se archiva.
        linea = self._pedido_web(self.pan2)
        with mock.patch("gestion.productos.historial", return_value=[]):
            self._eliminar(self.pan2)
        self.assertTrue(self._existe(self.pan2))
        self.assertTrue(PedidoItem.objects.filter(pk=linea.pk, producto=self.pan2).exists())
        self.assertFalse(RedireccionProducto.objects.exists())

    def test_uno_ya_oculto_sigue_oculto_y_lo_dice(self):
        self._pedido_web(self.pan)
        respuesta = self._eliminar(self.pan)
        self.assertContains(respuesta, "Ya estaba oculto y así sigue")
        self.assertTrue(self._existe(self.pan))


class FotosExtraTests(_Base):
    def _datos(self, producto, **cambios):
        datos = {"nombre": producto.nombre, "descripcion": producto.descripcion, "precio": producto.precio,
                 "unidades_por_pack": producto.unidades_por_pack, "minimo": producto.minimo,
                 "orden": producto.orden}
        for campo in ("visible", "disponible", "destacado", "en_box", "pide_nota"):
            if getattr(producto, campo):
                datos[campo] = "on"
        datos.update(cambios)
        return datos

    def _editar(self, producto, **cambios):
        return self.client.post(reverse("gestion:producto_editar", args=[producto.pk]),
                                data=self._datos(producto, **cambios), follow=True)

    @staticmethod
    def _carrusel(html):
        return html.count('class="carousel-item')

    def test_dos_fotos_extra_salen_en_el_carrusel_de_la_ficha(self):
        respuesta = self._editar(self.alfajores, fotos_extra=[_foto(nombre="a.jpg"), _foto(nombre="b.jpg")])
        self.assertContains(respuesta, "«Alfajores» guardado: 2 fotos extra agregadas.")
        fotos = list(self.alfajores.imagenes.order_by("pk"))
        self.assertEqual(len(fotos), 2)
        html = self.client_class().get("/productos/alfajores/").content.decode()
        self.assertIn('id="carouselProd"', html)
        self.assertEqual(self._carrusel(html), 3)  # la principal + las 2 extra
        # En el orden en que se subieron, despues de la principal.
        posiciones = [html.index(self.alfajores.imagen.url)] + [html.index(f.imagen.url) for f in fotos]
        self.assertEqual(posiciones, sorted(posiciones))

    def test_quitar_una_foto_la_saca_de_la_ficha(self):
        primera, segunda = (ProductoImagen.objects.create(producto=self.alfajores, imagen=_foto()) for _ in range(2))
        respuesta = self._editar(self.alfajores, quitar_foto=[primera.pk])
        self.assertContains(respuesta, "1 foto extra quitada")
        self.assertEqual(list(self.alfajores.imagenes.values_list("pk", flat=True)), [segunda.pk])
        html = self.client_class().get("/productos/alfajores/").content.decode()
        self.assertEqual(self._carrusel(html), 2)
        self.assertNotIn(primera.imagen.url, html)
        self.assertIn(segunda.imagen.url, html)

    def test_quitar_la_ultima_deja_la_foto_sola_sin_carrusel(self):
        foto = ProductoImagen.objects.create(producto=self.alfajores, imagen=_foto())
        self._editar(self.alfajores, quitar_foto=[foto.pk])
        html = self.client_class().get("/productos/alfajores/").content.decode()
        self.assertNotIn('id="carouselProd"', html)
        self.assertIn("single-detail-image", html)

    def test_no_se_puede_quitar_la_foto_de_otro_producto(self):
        ajena = ProductoImagen.objects.create(producto=self.barquillos, imagen=_foto())
        self._editar(self.alfajores, quitar_foto=[ajena.pk])
        self.assertTrue(ProductoImagen.objects.filter(pk=ajena.pk, producto=self.barquillos).exists())

    def test_se_achican_igual_que_la_principal(self):
        self._editar(self.alfajores, fotos_extra=[_foto(3000, 2000, nombre="celular.png", formato="PNG")])
        guardada = self.alfajores.imagenes.get()
        self.assertTrue(guardada.imagen.name.endswith(".jpg"))
        with Image.open(guardada.imagen.path) as imagen:
            self.assertEqual((imagen.format, max(imagen.size)), ("JPEG", 1400))

    def test_un_archivo_que_no_es_foto_no_guarda_nada(self):
        malo = SimpleUploadedFile("lista.jpg", b"no soy una foto", content_type="image/jpeg")
        respuesta = self._editar(self.alfajores, precio=990, fotos_extra=[malo])
        self.assertContains(respuesta, "No se guardó")
        self.assertContains(respuesta, "«lista.jpg»: Ese archivo no es una foto")
        self.alfajores.refresh_from_db()
        self.assertEqual(self.alfajores.precio, 1590)
        self.assertFalse(self.alfajores.imagenes.exists())

    def test_tope_de_fotos_extra(self):
        for _ in range(8):
            ProductoImagen.objects.create(producto=self.alfajores, imagen=_foto())
        respuesta = self._editar(self.alfajores, fotos_extra=[_foto()])
        self.assertContains(respuesta, "Caben hasta 8 fotos extra")
        self.assertEqual(self.alfajores.imagenes.count(), 8)
        # Quitando una, si entra.
        primera = self.alfajores.imagenes.order_by("pk").first()
        self._editar(self.alfajores, quitar_foto=[primera.pk], fotos_extra=[_foto()])
        self.assertEqual(self.alfajores.imagenes.count(), 8)
        self.assertFalse(ProductoImagen.objects.filter(pk=primera.pk).exists())

    def test_un_producto_nuevo_puede_traer_fotos_extra(self):
        datos = {"nombre": "Galletas", "descripcion": "Galletas de mantequilla.", "precio": 500,
                 "unidades_por_pack": 1, "minimo": 0, "orden": 9, "visible": "on", "disponible": "on",
                 "imagen": _foto(nombre="principal.jpg"), "fotos_extra": [_foto(), _foto()]}
        respuesta = self.client.post(reverse("gestion:producto_nuevo"), data=datos, follow=True)
        self.assertContains(respuesta, "con 2 fotos extra.")
        self.assertEqual(Producto.objects.get(nombre="Galletas").imagenes.count(), 2)

    def test_el_formulario_muestra_las_fotos_y_el_campo_multiple(self):
        foto = ProductoImagen.objects.create(producto=self.alfajores, imagen=_foto())
        html = self.client.get(reverse("gestion:producto_editar", args=[self.alfajores.pk])).content.decode()
        self.assertIn('name="fotos_extra"', html)
        self.assertRegex(html, r'name="fotos_extra"[^>]*multiple')
        self.assertIn(f'name="quitar_foto" value="{foto.pk}"', html)
        self.assertIn("(1 de 8)", html)
        self.assertIn(reverse("gestion:producto_eliminar", args=[self.alfajores.pk]), html)


class OcultoNoSeIndexaTests(_Base):
    def test_un_producto_oculto_responde_200_con_noindex_y_no_va_en_el_sitemap(self):
        publico = self.client_class()
        ficha = publico.get("/productos/pan-de-pascua/")
        self.assertEqual(ficha.status_code, 200)
        self.assertContains(ficha, NOINDEX)
        self.assertNotContains(ficha, INDEX)
        sitemap = publico.get("/sitemap.xml").content.decode()
        self.assertNotIn("https://dulcecita.cl/productos/pan-de-pascua/<", sitemap)
        self.assertIn("https://dulcecita.cl/productos/pan-de-pascua-2/<", sitemap)

    def test_uno_a_la_vista_sigue_indexable(self):
        ficha = self.client_class().get("/productos/pan-de-pascua-2/")
        self.assertContains(ficha, INDEX)
        self.assertNotContains(ficha, NOINDEX)

    def test_al_volver_a_mostrarlo_vuelve_a_indexarse(self):
        self.client.post(reverse("gestion:producto_visible", args=[self.pan.pk]))
        publico = self.client_class()
        self.assertContains(publico.get("/productos/pan-de-pascua/"), INDEX)
        self.assertIn("https://dulcecita.cl/productos/pan-de-pascua/<", publico.get("/sitemap.xml").content.decode())
