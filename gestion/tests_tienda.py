"""El panel como el de una tienda online (15-11-2026, pedido de Diego).

"Dejar el panel como un e-commerce más, pero oculta lo de Pedidos y Clientes
de momento."

- El menu y el inicio son los de una tienda: ventas, productos, promociones.
- "Pedidos" y "Clientes" (cotizaciones corporativas) se OCULTAN, no se borran:
  sus pantallas y sus datos siguen, y vuelven con PANEL_VENTA_CORPORATIVA.
- Cada pedido de dulcecita.cl se abre dentro del panel (antes iba a /admin/).
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from BebesitaAPP.models import Pedido as PedidoWeb
from BebesitaAPP.models import PedidoItem as PedidoItemWeb
from BebesitaAPP.models import Producto, Promocion

from .models import Cliente, Pedido
from .tienda import whatsapp_del_cliente


def _pedido_web(total, hace_dias=0, **extra):
    datos = dict(nombre_cliente="Ana Soto", email_cliente="ana@example.com", telefono="+56 9 1234 5678",
                 direccion="Av. Siempre Viva 123", total=total)
    datos.update(extra)
    pedido = PedidoWeb.objects.create(**datos)
    PedidoWeb.objects.filter(pk=pedido.pk).update(creado=timezone.now() - timedelta(days=hace_dias))
    return pedido


@override_settings(BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl", MINIMO_UNIDADES=10)
class _Panel(TestCase):
    def setUp(self):
        self.duena = get_user_model().objects.create_user("tamara", "t@example.com", "clave-larga-123")
        foto = SimpleUploadedFile("a.jpg", b"img", content_type="image/jpeg")
        self.alfajores = Producto.objects.create(nombre="Alfajores", descripcion="x", precio=1590,
                                                 visible=True, imagen=foto)
        self.oculto = Producto.objects.create(nombre="Brownie antiguo", descripcion="x", precio=2500,
                                              visible=False, imagen=foto)
        self.client.force_login(self.duena)

    def _menus(self, html):
        arriba = html.split('class="top-links"', 1)[1].split("</div>", 1)[0]
        abajo = html.split('class="bottom-nav"', 1)[1].split("</nav>", 1)[0]
        return arriba, abajo


class MenuTests(_Panel):
    def test_el_menu_es_el_de_una_tienda_sin_pedidos_ni_clientes(self):
        html = self.client.get(reverse("gestion:productos")).content.decode()
        for barra in self._menus(html):
            self.assertNotIn("Pedidos", barra)
            self.assertNotIn("Clientes", barra)
            self.assertNotIn(reverse("gestion:pedidos"), barra)
            self.assertNotIn(reverse("gestion:clientes"), barra)
            posiciones = [barra.index(nombre) for nombre in ("Inicio", "Ventas", "Productos", "Promos", "Google")]
            self.assertEqual(posiciones, sorted(posiciones))
            self.assertEqual(barra.count("<a "), 5)

    def test_las_dos_barras_tienen_los_mismos_enlaces_en_el_mismo_orden(self):
        import re
        for corporativo in (False, True):
            with override_settings(PANEL_VENTA_CORPORATIVA=corporativo):
                arriba, abajo = self._menus(self.client.get(reverse("gestion:productos")).content.decode())
            self.assertEqual(re.findall(r'href="([^"]+)"', arriba), re.findall(r'href="([^"]+)"', abajo), corporativo)

    @override_settings(PANEL_VENTA_CORPORATIVA=True)
    def test_con_el_modulo_corporativo_vuelven_pedidos_y_clientes(self):
        html = self.client.get(reverse("gestion:productos")).content.decode()
        for barra in self._menus(html):
            self.assertIn(reverse("gestion:pedidos"), barra)
            self.assertIn(reverse("gestion:clientes"), barra)
            self.assertEqual(barra.count("<a "), 7)

    def test_cada_seccion_marca_su_boton(self):
        casos = {reverse("gestion:dashboard"): "Inicio", reverse("gestion:web"): "Ventas",
                 reverse("gestion:ventas"): "Ventas", reverse("gestion:productos"): "Productos",
                 reverse("gestion:promos"): "Promos", reverse("gestion:seo"): "Google"}
        for url, nombre in casos.items():
            _, abajo = self._menus(self.client.get(url).content.decode())
            activo = [trozo for trozo in abajo.split("<a ")[1:] if 'class="active"' in trozo]
            self.assertEqual(len(activo), 1, url)
            self.assertIn(nombre, activo[0], url)


class OcultoNoEsBorradoTests(_Panel):
    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(nombre="AZA", whatsapp="+56911112222")
        self.cotizacion = Pedido.objects.create(cliente=self.cliente, descripcion="Cajas día del padre",
                                                fecha_pedido=date(2026, 6, 1))

    def test_las_pantallas_corporativas_siguen_respondiendo(self):
        for nombre, args in (("pedidos", []), ("clientes", []), ("pedido_detalle", [self.cotizacion.pk]),
                             ("cliente_editar", [self.cliente.pk]), ("costos", [])):
            self.assertEqual(self.client.get(reverse(f"gestion:{nombre}", args=args)).status_code, 200, nombre)

    def test_los_datos_corporativos_no_se_tocaron(self):
        self.client.get(reverse("gestion:dashboard"))
        self.assertEqual((Pedido.objects.count(), Cliente.objects.count()), (1, 1))

    def test_el_inicio_de_tienda_no_muestra_la_utilidad_de_las_cotizaciones(self):
        html = self.client.get(reverse("gestion:dashboard")).content.decode()
        self.assertNotIn("Utilidad del mes", html)
        self.assertNotIn("Cajas día del padre", html)
        self.assertNotIn(reverse("gestion:pedido_nuevo"), html)

    @override_settings(PANEL_VENTA_CORPORATIVA=True)
    def test_con_el_modulo_corporativo_vuelve_el_inicio_de_antes(self):
        html = self.client.get(reverse("gestion:dashboard")).content.decode()
        self.assertIn("Utilidad del mes", html)
        self.assertIn(reverse("gestion:pedido_nuevo"), html)


class InicioTiendaTests(_Panel):
    def test_resume_la_semana_contra_la_anterior(self):
        _pedido_web(15900, hace_dias=0)
        _pedido_web(9000, hace_dias=4)
        _pedido_web(12450, hace_dias=10)
        html = self.client.get(reverse("gestion:dashboard")).content.decode()
        self.assertIn("Hoy entró 1 pedido por $15.900.", html)
        self.assertIn('<div class="kpi-value">$24.900</div>', html)
        self.assertIn("▲ 100%", html)
        self.assertIn("($12.450 en 1 pedido)", html)

    def test_sin_pedidos_lo_dice_sin_inventar_porcentajes(self):
        html = self.client.get(reverse("gestion:dashboard")).content.decode()
        self.assertIn("Hoy todavía no entran pedidos.", html)
        self.assertIn("En los 7 días anteriores no hubo ventas.", html)
        self.assertIn("Aún no llegan pedidos por la web.", html)
        self.assertNotIn("▲", html)

    def test_cuenta_solo_los_productos_que_se_ven_y_dice_si_hay_promo(self):
        html = self.client.get(reverse("gestion:dashboard")).content.decode()
        self.assertIn('<div class="stat-value">1</div>', html)        # el oculto no cuenta
        self.assertIn("Sin promoción hoy", html)
        hoy = timezone.localdate()
        Promocion.objects.create(nombre="Navidad", porcentaje=10, desde=hoy, hasta=hoy + timedelta(days=3))
        html = self.client.get(reverse("gestion:dashboard")).content.decode()
        self.assertIn("−10%", html)
        self.assertIn("Navidad, hasta el", html)

    def test_los_ultimos_pedidos_se_abren_en_el_panel_no_en_el_admin(self):
        pedido = _pedido_web(15900)
        for url in (reverse("gestion:dashboard"), reverse("gestion:web"), reverse("gestion:ventas")):
            html = self.client.get(url).content.decode()
            self.assertIn(reverse("gestion:venta_detalle", args=[pedido.pk]), html, url)
            self.assertNotIn("/admin/", html, url)

    def test_los_accesos_de_todos_los_dias(self):
        html = self.client.get(reverse("gestion:dashboard")).content.decode()
        for nombre in ("producto_nuevo", "promo_nueva", "productos", "promos", "web", "seo"):
            self.assertIn(reverse(f"gestion:{nombre}"), html, nombre)
        self.assertIn('href="https://dulcecita.cl"', html)


class PedidoDeLaTiendaTests(_Panel):
    def setUp(self):
        super().setUp()
        self.pedido = _pedido_web(18890, tipo_entrega="despacho", comuna_sector="Maipú", cantidad_cajas=1,
                                  costo_caja=1490, comentario_ocasion="Navideño, por favor")
        PedidoItemWeb.objects.create(pedido=self.pedido, producto=self.alfajores, cantidad=10, precio=1590,
                                     detalle="Box #1 · Cobertura: Chocolate")
        PedidoItemWeb.objects.create(pedido=self.pedido, producto=self.oculto, cantidad=1, precio=1500)

    def test_pide_login(self):
        self.client.logout()
        for url in (reverse("gestion:ventas"), reverse("gestion:venta_detalle", args=[self.pedido.pk])):
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn("/panel/login/", respuesta["Location"])

    def test_muestra_que_pidio_quien_y_como_se_entrega(self):
        html = self.client.get(reverse("gestion:venta_detalle", args=[self.pedido.pk])).content.decode()
        self.assertIn(f"Pedido #{self.pedido.pk}", html)
        self.assertIn("Ana Soto", html)
        self.assertIn("Despacho a domicilio · Maipú", html)
        self.assertIn("Av. Siempre Viva 123", html)
        self.assertIn("Navideño, por favor", html)
        self.assertIn("10 × Alfajores", html)
        self.assertIn("Box #1 · Cobertura: Chocolate", html)
        self.assertIn("$15.900", html)      # 10 x 1.590
        self.assertIn("$17.400", html)      # productos: 15.900 + 1.500
        self.assertIn("Empaque (1 box)", html)
        self.assertIn('<span class="item-title num">$18.890</span>', html)

    def test_el_boton_de_whatsapp_lleva_al_numero_del_cliente(self):
        html = self.client.get(reverse("gestion:venta_detalle", args=[self.pedido.pk])).content.decode()
        self.assertIn("https://wa.me/56912345678?text=Hola%20Ana%2C%20te%20escribo%20de%20Dulcecita", html)

    def test_un_pedido_que_no_existe_da_404(self):
        self.assertEqual(self.client.get(reverse("gestion:venta_detalle", args=[99999])).status_code, 404)

    def test_el_pedido_es_de_solo_lectura(self):
        url = reverse("gestion:venta_detalle", args=[self.pedido.pk])
        self.client.post(url, data={"total": 1, "nombre_cliente": "Otro"})
        self.pedido.refresh_from_db()
        self.assertEqual((int(self.pedido.total), self.pedido.nombre_cliente), (18890, "Ana Soto"))
        self.assertNotIn("<form", self.client.get(url).content.decode().split("<main", 1)[1].split("</main>", 1)[0])

    def test_la_lista_va_del_mas_nuevo_al_mas_antiguo_y_pagina(self):
        for i in range(30):
            _pedido_web(1000 + i, hace_dias=i + 1, nombre_cliente=f"Cliente {i:02d}")
        primera = self.client.get(reverse("gestion:ventas")).content.decode()
        self.assertIn("31 pedidos hechos en dulcecita.cl", primera)
        self.assertEqual(primera.count('class="list-group-item list-group-item-action'), 25)
        self.assertLess(primera.index("Ana Soto"), primera.index("Cliente 00"))
        self.assertIn("?pagina=2", primera)
        segunda = self.client.get(reverse("gestion:ventas") + "?pagina=2").content.decode()
        self.assertEqual(segunda.count('class="list-group-item list-group-item-action'), 6)
        self.assertIn("Cliente 29", segunda)


class WhatsAppDelClienteTests(TestCase):
    def _enlace(self, telefono):
        return whatsapp_del_cliente(PedidoWeb(pk=7, nombre_cliente="María José Pérez", telefono=telefono))

    @override_settings(BRAND_NAME="Dulcecita")
    def test_acepta_las_formas_en_que_la_gente_escribe_su_celular(self):
        for telefono in ("+56 9 1234 5678", "56912345678", "912345678", "9 1234 5678", "+56-9-1234-5678"):
            self.assertTrue(self._enlace(telefono).startswith("https://wa.me/56912345678?text=Hola%20Mar%C3%ADa"),
                            telefono)

    def test_un_telefono_incompleto_no_arma_un_enlace_roto(self):
        for telefono in ("", "1234", "abc", "22345678"):
            self.assertEqual(self._enlace(telefono), "", telefono)
