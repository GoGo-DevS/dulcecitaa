"""La seccion Productos del panel (15-11-2026).

Tamara cambia precios, fotos y minimos desde el telefono, sin pasar por Diego
ni por /admin/. Lo que se prueba es el camino completo: lo que ella guarda en
el panel es lo que la web muestra Y lo que el carrito cobra. Un formulario que
guarda bien y una ficha que sigue con el precio viejo seria el peor resultado.
"""
import shutil
import tempfile
from io import BytesIO

from django import forms
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from BebesitaAPP.models import Opcion, Pedido, PedidoItem, PrecioCombinacion, Producto

from .forms import achicar_foto

MEDIA_PRUEBA = tempfile.mkdtemp(prefix="dulcecita-pruebas-")


def tearDownModule():
    shutil.rmtree(MEDIA_PRUEBA, ignore_errors=True)


def _foto(ancho=40, alto=30, formato="JPEG", modo="RGB", nombre="foto.jpg"):
    salida = BytesIO()
    Image.new(modo, (ancho, alto), (200, 120, 160) if modo == "RGB" else (200, 120, 160, 128)).save(salida, formato)
    tipo = "image/jpeg" if formato == "JPEG" else "image/png"
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type=tipo)


@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1490, BOX_MINIMO_TOTAL=0, SHIPPING_COST=0,
                   BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl", MEDIA_ROOT=MEDIA_PRUEBA)
class _Panel(TestCase):
    def setUp(self):
        self.duena = get_user_model().objects.create_user("tamara", "t@example.com", "clave-larga-123")
        self.choc = Opcion.objects.create(tipo="cobertura", nombre="Chocolate", orden=1)
        self.blanco = Opcion.objects.create(tipo="cobertura", nombre="Chocolate blanco", orden=2)
        self.alfajores = self._crear("Alfajores", 1590, orden=1,
                                     descripcion="Alfajor de triple capa con manjar y cobertura de chocolate.")
        self.alfajores.opciones.add(self.choc, self.blanco)
        self.banados = self._crear("Cuchuflís bañados", 350, orden=3, minimo=30)
        self.banados.opciones.add(self.choc, self.blanco)
        self.torta = self._crear("Torta de cuchuflís", 14990, orden=5, minimo=1, en_box=False)
        self.t50 = Opcion.objects.create(tipo="tamano", nombre="50 cuchuflís", orden=1)
        self.sin = Opcion.objects.create(tipo="cobertura", nombre="Sin cobertura", orden=0)
        self.torta.opciones.add(self.t50, self.sin, self.choc)
        self.combos = {}
        for cobertura, precio in [(self.sin, 14990), (self.choc, 17990)]:
            combo = PrecioCombinacion.objects.create(producto=self.torta, precio=precio)
            combo.opciones.set([self.t50, cobertura])
            combo.actualizar_clave()
            self.combos[cobertura.nombre] = combo
        self.viejo = self._crear("Brownie antiguo", 2500, visible=False)

    @staticmethod
    def _crear(nombre, precio, descripcion="Texto de la duena", **extra):
        return Producto.objects.create(nombre=nombre, descripcion=descripcion, precio=precio,
                                       imagen=_foto(nombre="original.jpg"), **extra)

    def _datos(self, producto, **cambios):
        """Lo que manda el formulario de editar, tal como esta el producto."""
        datos = {
            "nombre": producto.nombre, "descripcion": producto.descripcion, "precio": producto.precio,
            "unidades_por_pack": producto.unidades_por_pack, "minimo": producto.minimo, "orden": producto.orden,
            "opciones": [op.pk for op in producto.opciones.all()],
        }
        for campo in ("visible", "disponible", "destacado", "en_box", "pide_nota"):
            if getattr(producto, campo):
                datos[campo] = "on"
        for combo in producto.precios_combinacion.all():
            datos[f"combo_{combo.pk}"] = combo.precio
        datos.update(cambios)
        return {clave: valor for clave, valor in datos.items() if valor is not None}

    def _editar(self, producto, **cambios):
        return self.client.post(reverse("gestion:producto_editar", args=[producto.pk]),
                                data=self._datos(producto, **cambios), follow=True)


class AccesoTests(_Panel):
    def test_todas_las_rutas_piden_login_y_no_cambian_nada(self):
        rutas = [("get", reverse("gestion:productos")),
                 ("get", reverse("gestion:producto_nuevo")),
                 ("get", reverse("gestion:producto_editar", args=[self.alfajores.pk])),
                 ("post", reverse("gestion:producto_editar", args=[self.alfajores.pk])),
                 ("post", reverse("gestion:producto_visible", args=[self.alfajores.pk])),
                 ("post", reverse("gestion:producto_disponible", args=[self.alfajores.pk]))]
        for metodo, url in rutas:
            respuesta = getattr(self.client, metodo)(url, data={"precio": 1} if metodo == "post" else None)
            self.assertEqual(respuesta.status_code, 302, url)
            self.assertIn("/panel/login/", respuesta["Location"], url)
        self.alfajores.refresh_from_db()
        self.assertEqual((self.alfajores.precio, self.alfajores.visible, self.alfajores.disponible),
                         (1590, True, True))

    def test_no_existe_ninguna_ruta_para_borrar_un_producto(self):
        self.client.force_login(self.duena)
        for sufijo in ("eliminar", "borrar", "delete"):
            url = f"/panel/productos/{self.alfajores.pk}/{sufijo}/"
            self.assertEqual(self.client.post(url).status_code, 404, url)
        self.assertTrue(Producto.objects.filter(pk=self.alfajores.pk).exists())

    def test_el_menu_tiene_productos_en_las_dos_barras_y_en_el_mismo_orden(self):
        self.client.force_login(self.duena)
        html = self.client.get(reverse("gestion:productos")).content.decode()
        arriba = html.split('class="top-links"', 1)[1].split("</div>", 1)[0]
        abajo = html.split('class="bottom-nav"', 1)[1].split("</nav>", 1)[0]
        orden = ["Inicio", "Ventas", "Productos", "Promos", "Google"]
        for barra in (arriba, abajo):
            posiciones = [barra.index(nombre) for nombre in orden]
            self.assertEqual(posiciones, sorted(posiciones))
        self.assertIn('class="active"', abajo.split("Productos", 1)[0].rsplit("<a", 1)[1])


class ListaTests(_Panel):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.duena)

    def test_dice_como_se_cobra_cada_producto_y_desde_cuantos(self):
        html = self.client.get(reverse("gestion:productos")).content.decode()
        self.assertIn("$350 por unidad · desde 30", html)
        self.assertIn("$1.590 por unidad · desde 10", html)
        self.assertIn("desde $14.990 (2 precios) · desde 1", html)

    def test_un_paquete_se_muestra_como_paquete(self):
        Producto.objects.filter(pk=self.banados.pk).update(precio=1590, unidades_por_pack=4, minimo=0)
        html = self.client.get(reverse("gestion:productos")).content.decode()
        self.assertIn("$1.590 la bolsita de 4 · desde 10", html)

    def test_los_ocultos_van_aparte_y_se_pueden_volver_a_mostrar(self):
        html = self.client.get(reverse("gestion:productos")).content.decode()
        en_web, ocultos = html.split("Ocultos", 1)
        self.assertNotIn("Brownie antiguo", en_web)
        self.assertIn("Brownie antiguo", ocultos)
        self.assertIn(reverse("gestion:producto_visible", args=[self.viejo.pk]), ocultos)


class EditarTests(_Panel):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.duena)

    def test_el_precio_nuevo_es_el_que_muestra_la_web_y_cobra_el_carrito(self):
        respuesta = self._editar(self.banados, precio=400)
        self.assertRedirects(respuesta, reverse("gestion:productos"))
        self.assertContains(respuesta, "precio $350 → $400")
        self.banados.refresh_from_db()
        self.assertEqual(self.banados.precio, 400)

        publico = self.client_class()
        self.assertIn('<span data-precio="400">$400</span>', publico.get("/productos/").content.decode())
        ficha = publico.get("/productos/cuchuflis-banados/").content.decode()
        self.assertIn("$400 por unidad, con chocolate o chocolate blanco.", ficha)
        linea = f"{self.banados.pk}-{self.choc.pk}"
        datos = publico.post(reverse("agregar_carrito_ajax", args=[linea])).json()
        self.assertEqual((datos["qty"], datos["total"]), (30, 30 * 400))

    def test_el_minimo_y_la_unidad_tambien_llegan_al_carrito(self):
        self._editar(self.banados, minimo=50)
        publico = self.client_class()
        datos = publico.post(reverse("agregar_carrito_ajax", args=[f"{self.banados.pk}-{self.choc.pk}"])).json()
        self.assertEqual(datos["qty"], 50)
        self.assertIn("Agregar 50", publico.get("/productos/").content.decode())

    def test_un_precio_en_cero_negativo_o_vacio_no_se_guarda(self):
        for malo in (0, -100, ""):
            respuesta = self._editar(self.banados, precio=malo)
            self.assertEqual(respuesta.status_code, 200, malo)
            self.assertContains(respuesta, "No se guardó")
            self.banados.refresh_from_db()
            self.assertEqual(self.banados.precio, 350, malo)

    def test_guardar_sin_elegir_foto_conserva_la_que_tenia(self):
        antes = self.banados.imagen.name
        self._editar(self.banados, descripcion="Cuchuflís bañados enteros en chocolate, por unidad.")
        self.banados.refresh_from_db()
        self.assertEqual(self.banados.imagen.name, antes)
        self.assertEqual(self.banados.descripcion, "Cuchuflís bañados enteros en chocolate, por unidad.")

    def test_una_foto_nueva_se_guarda_achicada(self):
        grande = _foto(3000, 2000, formato="PNG", modo="RGBA", nombre="celular.png")
        self._editar(self.banados, imagen=grande)
        self.banados.refresh_from_db()
        self.assertTrue(self.banados.imagen.name.endswith(".jpg"), self.banados.imagen.name)
        with Image.open(self.banados.imagen.path) as guardada:
            self.assertEqual(guardada.format, "JPEG")
            self.assertEqual(max(guardada.size), 1400)

    def test_un_archivo_que_no_es_foto_se_rechaza(self):
        falso = SimpleUploadedFile("lista.jpg", b"esto no es una imagen", content_type="image/jpeg")
        antes = self.banados.imagen.name
        respuesta = self._editar(self.banados, imagen=falso)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se guardó")
        self.banados.refresh_from_db()
        self.assertEqual(self.banados.imagen.name, antes)

    def test_dos_productos_no_pueden_llamarse_igual(self):
        respuesta = self._editar(self.banados, nombre="alfajores")
        self.assertContains(respuesta, "Ya hay un producto con ese nombre.")
        self.banados.refresh_from_db()
        self.assertEqual(self.banados.nombre, "Cuchuflís bañados")

    def test_la_direccion_web_no_cambia_aunque_cambie_el_nombre(self):
        self._editar(self.banados, nombre="Cuchuflís con chocolate", slug="otra-direccion")
        self.banados.refresh_from_db()
        self.assertEqual(self.banados.nombre, "Cuchuflís con chocolate")
        self.assertEqual(self.banados.slug, "cuchuflis-banados")

    def test_las_opciones_que_se_desmarcan_dejan_de_ofrecerse(self):
        self._editar(self.banados, opciones=[self.choc.pk])
        self.assertEqual([op.nombre for op in self.banados.opciones.all()], ["Chocolate"])

    def test_una_variante_no_se_edita_desde_aqui(self):
        variante = self._crear("Alfajor blanco", 1590, variante_de=self.alfajores, visible=False)
        self.assertEqual(self.client.get(reverse("gestion:producto_editar", args=[variante.pk])).status_code, 404)


class PreciosPorCombinacionTests(_Panel):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.duena)
        self.combo_sin, self.combo_choc = self.combos["Sin cobertura"], self.combos["Chocolate"]

    def test_el_formulario_nombra_cada_combinacion_con_el_tamano_primero(self):
        html = self.client.get(reverse("gestion:producto_editar", args=[self.torta.pk])).content.decode()
        self.assertIn("50 cuchuflís · Sin cobertura", html)
        self.assertIn("50 cuchuflís · Chocolate", html)
        self.assertIn(f'name="combo_{self.combo_choc.pk}" value="17990"', html)

    def test_cada_precio_se_guarda_y_es_el_que_cobra_el_carrito(self):
        respuesta = self._editar(self.torta, **{f"combo_{self.combo_choc.pk}": 17500})
        self.assertContains(respuesta, "50 cuchuflís · Chocolate: $17.990 → $17.500")
        self.combo_choc.refresh_from_db()
        self.combo_sin.refresh_from_db()
        self.assertEqual((self.combo_choc.precio, self.combo_sin.precio), (17500, 14990))

        publico = self.client_class()
        linea = f"{self.torta.pk}-{self.choc.pk}-{self.t50.pk}"
        datos = publico.post(reverse("agregar_carrito_ajax", args=[linea])).json()
        self.assertEqual((datos["qty"], datos["total"]), (1, 17500))
        self.assertIn("chocolate, $17.500", publico.get("/productos/torta-de-cuchuflis/").content.decode())

    def test_si_un_precio_viene_mal_no_se_guarda_ninguno(self):
        respuesta = self._editar(self.torta, descripcion="Cambio que no debe quedar",
                                 **{f"combo_{self.combo_choc.pk}": 0, f"combo_{self.combo_sin.pk}": 15990})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "escribe un precio mayor que cero")
        self.combo_choc.refresh_from_db()
        self.combo_sin.refresh_from_db()
        self.torta.refresh_from_db()
        self.assertEqual((self.combo_choc.precio, self.combo_sin.precio), (17990, 14990))
        self.assertEqual(self.torta.descripcion, "Texto de la duena")


class CrearTests(_Panel):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.duena)

    def _nuevo(self, **cambios):
        datos = {"nombre": "Pan de pascua", "descripcion": "Pan de pascua artesanal de medio kilo, con frutos secos.",
                 "precio": 8590, "unidades_por_pack": 1, "minimo": 1, "orden": 6,
                 "visible": "on", "disponible": "on", "imagen": _foto(nombre="pan.jpg")}
        datos.update(cambios)
        return self.client.post(reverse("gestion:producto_nuevo"),
                                data={k: v for k, v in datos.items() if v is not None}, follow=True)

    def test_un_producto_nuevo_queda_en_el_catalogo_con_su_ficha(self):
        respuesta = self._nuevo()
        self.assertRedirects(respuesta, reverse("gestion:productos"))
        self.assertContains(respuesta, "«Pan de pascua» creado: $8.590 por unidad, desde 1.")
        pan = Producto.objects.get(nombre="Pan de pascua")
        self.assertEqual((pan.slug, pan.precio, pan.minimo, pan.visible), ("pan-de-pascua", 8590, 1, True))
        publico = self.client_class()
        self.assertIn("Pan de pascua", publico.get("/productos/").content.decode())
        self.assertEqual(publico.get("/productos/pan-de-pascua/").status_code, 200)
        datos = publico.post(reverse("agregar_carrito_ajax", args=[str(pan.pk)])).json()
        self.assertEqual((datos["qty"], datos["total"]), (1, 8590))

    def test_sin_foto_no_se_crea(self):
        respuesta = self._nuevo(imagen=None)
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Producto.objects.filter(nombre="Pan de pascua").exists())

    def test_el_formulario_propone_el_orden_siguiente_y_visible(self):
        html = self.client.get(reverse("gestion:producto_nuevo")).content.decode()
        self.assertIn('name="orden" value="6"', html)
        self.assertRegex(html, r'name="visible"[^>]*checked')


class MostrarYOcultarTests(_Panel):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.duena)

    def test_ocultar_lo_saca_de_la_web_y_no_toca_los_pedidos(self):
        pedido = Pedido.objects.create(nombre_cliente="Ana", email_cliente="a@example.com",
                                       telefono="+56911111111", direccion="x", total=15900)
        PedidoItem.objects.create(pedido=pedido, producto=self.alfajores, cantidad=10, precio=1590)
        respuesta = self.client.post(reverse("gestion:producto_visible", args=[self.alfajores.pk]), follow=True)
        self.assertContains(respuesta, "quedó oculto")
        self.alfajores.refresh_from_db()
        self.assertFalse(self.alfajores.visible)
        publico = self.client_class()
        catalogo = publico.get("/productos/").content.decode()
        self.assertNotIn(f'data-pid="{self.alfajores.pk}"', catalogo)       # sin tarjeta
        self.assertIn(f'data-pid="{self.banados.pk}"', catalogo)            # los demas siguen
        self.assertNotIn("/productos/alfajores/", publico.get("/sitemap.xml").content.decode())
        self.assertEqual(PedidoItem.objects.filter(producto=self.alfajores).count(), 1)
        # Y no se puede comprar por un enlace viejo.
        agregado = publico.post(reverse("agregar_carrito_ajax", args=[f"{self.alfajores.pk}-{self.choc.pk}"]))
        self.assertEqual(agregado.status_code, 400)

    def test_volver_a_mostrarlo_lo_devuelve_al_catalogo(self):
        self.client.post(reverse("gestion:producto_visible", args=[self.viejo.pk]))
        self.viejo.refresh_from_db()
        self.assertTrue(self.viejo.visible)
        self.assertIn("Brownie antiguo", self.client_class().get("/productos/").content.decode())

    def test_no_disponible_se_ve_pero_no_se_compra(self):
        respuesta = self.client.post(reverse("gestion:producto_disponible", args=[self.alfajores.pk]), follow=True)
        self.assertContains(respuesta, "no disponible")
        publico = self.client_class()
        self.assertIn("No disponible", publico.get("/productos/").content.decode())
        agregado = publico.post(reverse("agregar_carrito_ajax", args=[f"{self.alfajores.pk}-{self.choc.pk}"]))
        self.assertEqual(agregado.status_code, 400)

    def test_mostrar_y_ocultar_solo_por_post(self):
        self.assertEqual(self.client.get(reverse("gestion:producto_visible", args=[self.alfajores.pk])).status_code, 405)
        self.alfajores.refresh_from_db()
        self.assertTrue(self.alfajores.visible)


class AchicarFotoTests(TestCase):
    def test_una_foto_de_celular_queda_en_1400_y_jpeg(self):
        chica = achicar_foto(_foto(4000, 3000, nombre="IMG_2031.jpg"))
        with Image.open(chica) as imagen:
            self.assertEqual((imagen.format, imagen.size), ("JPEG", (1400, 1050)))
        self.assertEqual(chica.name, "IMG_2031.jpg")
        self.assertLess(chica.size, 200 * 1024)

    def test_una_foto_chica_no_se_agranda(self):
        with Image.open(achicar_foto(_foto(600, 400))) as imagen:
            self.assertEqual(imagen.size, (600, 400))

    def test_la_transparencia_queda_sobre_blanco(self):
        transparente = BytesIO()
        Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(transparente, "PNG")
        archivo = SimpleUploadedFile("logo.png", transparente.getvalue(), content_type="image/png")
        with Image.open(achicar_foto(archivo)) as imagen:
            self.assertEqual(imagen.mode, "RGB")
            self.assertGreater(min(imagen.getpixel((25, 25))), 245)

    def test_lo_que_no_es_imagen_avisa_en_palabras(self):
        with self.assertRaises(forms.ValidationError) as error:
            achicar_foto(SimpleUploadedFile("nota.jpg", b"hola", content_type="image/jpeg"))
        self.assertIn("no es una foto", error.exception.messages[0])
