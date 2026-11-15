"""La pestaña Web del panel: ventas comparadas y "Como sales en Google" (15-11-2026).

- Ventas: el numero va contra el periodo anterior y por dia, porque un monto
  solo no dice si la semana fue buena o mala.
- Google: cada pagina publica se arma de verdad y se muestra como la mostraria
  Google, con lo que la duena puede mejorar sola separado de lo que es codigo.
"""
from datetime import date, datetime, timedelta
from datetime import timezone as zona_horaria
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from BebesitaAPP.models import ClicEnlace, Opcion, Pedido as PedidoWeb, Producto

from . import seo_panel
from .views import _serie_ventas, _variacion


def _producto(nombre, precio, descripcion, **extra):
    return Producto.objects.create(
        nombre=nombre, descripcion=descripcion, precio=precio, visible=True,
        imagen=SimpleUploadedFile("a.jpg", b"img", content_type="image/jpeg"), **extra)


def _pedido(total, hace_dias, **extra):
    pedido = PedidoWeb.objects.create(nombre_cliente="Ana", email_cliente="a@example.com",
                                      telefono="+56911111111", direccion="x", total=total, **extra)
    PedidoWeb.objects.filter(pk=pedido.pk).update(creado=timezone.now() - timedelta(days=hace_dias))
    return pedido


@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1490, DESPACHO_HORAS=48,
                   BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl")
class _Panel(TestCase):
    def setUp(self):
        self.duena = get_user_model().objects.create_user("tamara", "t@example.com", "clave-larga-123")
        choc = Opcion.objects.create(tipo="cobertura", nombre="Chocolate", orden=1)
        self.alfajores = _producto(
            "Alfajores", 1590, orden=1,
            descripcion="Alfajor de triple capa: galletas suaves, relleno cremoso de manjar y cobertura de chocolate.")
        self.alfajores.opciones.add(choc)
        self.banados = _producto("Cuchuflís bañados", 350, "Ricos.", orden=3, minimo=30)
        self.nuevo = _producto("Pan de pascua", 8590, orden=6, minimo=1,
                               descripcion="Pan de pascua artesanal de medio kilo, con frutos secos y fruta confitada.")
        self.client.force_login(self.duena)


class GoogleTests(_Panel):
    def _html(self):
        respuesta = self.client.get(reverse("gestion:seo"))
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    def _tarjeta(self, html, nombre):
        return next(t for t in html.split('<article class="card mb-3 seo-pagina">')[1:]
                    if f"</i> {nombre}</span>" in t).split("</article>", 1)[0]

    def test_pide_login(self):
        self.client.logout()
        respuesta = self.client.get(reverse("gestion:seo"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/panel/login/", respuesta["Location"])

    def test_muestra_cada_pagina_como_la_muestra_google(self):
        html = self._html()
        catalogo = self._tarjeta(html, "Catálogo")
        self.assertIn("https://dulcecita.cl/productos/", catalogo)
        self.assertIn("Alfajores y cuchuflís por mayor en Santiago | Dulcecita", catalogo)
        ficha = self._tarjeta(html, "Alfajores")
        self.assertIn("https://dulcecita.cl/productos/alfajores/", ficha)
        self.assertIn("Alfajores artesanales para regalar desde $1.590 | Dulcecita", ficha)
        self.assertIn("ideales para regalar", ficha)
        # Las 7 paginas fijas y las 3 fichas visibles.
        self.assertEqual(html.count('<article class="card mb-3 seo-pagina">'), 10)

    def test_el_titulo_y_la_descripcion_son_los_de_la_pagina_real(self):
        publica = self.client_class().get("/productos/alfajores/").content.decode()
        datos = seo_panel.leer(publica)
        ficha = self._tarjeta(self._html(), "Alfajores")
        self.assertIn(datos["titulo"], ficha)
        self.assertIn(f"Título: {len(datos['titulo'])} de 60 caracteres", ficha)
        self.assertIn(f"Descripción: {len(datos['descripcion'])} de 155", ficha)

    def test_lo_que_la_duena_puede_arreglar_va_aparte_y_se_va_al_arreglarlo(self):
        ficha = self._tarjeta(self._html(), "Cuchuflís bañados")
        self.assertIn("Revisar", ficha)
        self.assertIn("<b>Lo arreglas tú:</b> La descripción del producto es corta (6 letras).", ficha)
        self.assertIn(reverse("gestion:producto_editar", args=[self.banados.pk]), ficha)

        Producto.objects.filter(pk=self.banados.pk).update(
            descripcion="Cuchuflís crujientes rellenos de manjar y bañados enteros en chocolate. Se venden por unidad.")
        ficha = self._tarjeta(self._html(), "Cuchuflís bañados")
        self.assertNotIn("Lo arreglas tú", ficha)
        self.assertIn('<span class="badge bg-success flex-shrink-0">Lista</span>', ficha)

    def test_un_producto_sin_textos_propios_usa_su_descripcion_y_lo_dice(self):
        ficha = self._tarjeta(self._html(), "Pan de pascua")
        self.assertIn("Pan de pascua artesanales desde $8.590 | Dulcecita", ficha)
        self.assertIn("Pan de pascua artesanal de medio kilo", ficha)
        self.assertIn("<b>Para Diego:</b> Usa el título genérico.", ficha)

    def test_un_producto_oculto_no_se_revisa(self):
        Producto.objects.filter(pk=self.nuevo.pk).update(visible=False)
        self.assertNotIn("Pan de pascua", self._html())

    def test_el_resumen_cuenta_listas_y_pendientes(self):
        html = self._html()
        paginas = seo_panel.auditar(self.client.get(reverse("gestion:seo")).wsgi_request)
        listas = sum(1 for p in paginas if p["lista"])
        self.assertIn(f'<div class="kpi-value">{listas} de {len(paginas)}</div>', html)
        self.assertGreaterEqual(sum(len(p["para_ti"]) for p in paginas), 1)

    def test_revisar_no_deja_rastro_ni_cuenta_como_visita(self):
        sesiones, clics, pedidos = Session.objects.count(), ClicEnlace.objects.count(), PedidoWeb.objects.count()
        self._html()
        self.assertEqual((Session.objects.count(), ClicEnlace.objects.count(), PedidoWeb.objects.count()),
                         (sesiones, clics, pedidos))
        # El carrito de quien revisa no se mezcla con la pagina revisada.
        self.assertNotIn("cart", self.client.session)

    def test_una_pagina_que_falla_no_tumba_el_panel(self):
        real = seo_panel._pedir

        def falla_navidad(ruta, pedido):
            if ruta == "/navidad/":
                raise RuntimeError("plantilla rota")
            return real(ruta, pedido)

        with mock.patch.object(seo_panel, "_pedir", side_effect=falla_navidad):
            html = self._html()
        navidad = self._tarjeta(html, "Navidad")
        self.assertIn("No se pudo revisar (plantilla rota).", navidad)
        self.assertIn("Alfajores artesanales para regalar", self._tarjeta(html, "Alfajores"))

    def test_enlaza_a_lo_que_solo_sabe_google(self):
        html = self._html()
        self.assertIn("search-console/performance/search-analytics?resource_id=sc-domain%3Adulcecita.cl", html)
        self.assertIn("https://dulcecita.cl/sitemap.xml", html)


class LeerYRevisarTests(TestCase):
    PAGINA = """<html><head><title> Torta de cuchufl&iacute;s | Dulcecita </title>
      <meta name="description" content="Torta de cuchufl&iacute;s rellenos de manjar, de 50 o 100 unidades, con cinta.">
      <link rel="canonical" href="https://dulcecita.cl/productos/torta/">
      <script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Product"},{"@type":"FAQPage"}]}</script>
      </head><body><h1>Torta de <em>cuchuflís</em></h1></body></html>"""

    def test_lee_lo_que_lee_google(self):
        datos = seo_panel.leer(self.PAGINA)
        self.assertEqual(datos["titulo"], "Torta de cuchuflís | Dulcecita")
        self.assertEqual(datos["descripcion"],
                         "Torta de cuchuflís rellenos de manjar, de 50 o 100 unidades, con cinta.")
        self.assertEqual(datos["h1"], ["Torta de cuchuflís"])
        self.assertEqual(datos["canonica"], "https://dulcecita.cl/productos/torta/")
        self.assertEqual(datos["tipos"], {"Product", "FAQPage"})
        self.assertFalse(datos["noindex"])

    def test_una_pagina_bien_armada_no_tiene_avisos(self):
        datos = seo_panel.leer(self.PAGINA)
        self.assertEqual(seo_panel.revisar_pagina(datos, "https://dulcecita.cl/productos/torta/",
                                                  espera_producto=True), [])

    def test_avisa_titulo_largo_descripcion_larga_y_direccion_equivocada(self):
        datos = seo_panel.leer(self.PAGINA)
        datos.update(titulo="T" * 61, descripcion="D" * 156)
        textos = [a["texto"] for a in seo_panel.revisar_pagina(datos, "https://dulcecita.cl/otra/")]
        self.assertTrue(any("61 caracteres" in t for t in textos), textos)
        self.assertTrue(any("156 caracteres" in t for t in textos), textos)
        self.assertTrue(any("dirección oficial" in t for t in textos), textos)

    def test_avisa_si_falta_todo(self):
        textos = [a["texto"] for a in seo_panel.revisar_pagina(
            seo_panel.leer('<html><head><meta name="robots" content="noindex"></head><body></body></html>'),
            "https://dulcecita.cl/x/", espera_producto=True)]
        for esperado in ("No tiene título.", "No tiene descripción", "título principal", "noindex", "precio"):
            self.assertTrue(any(esperado in t for t in textos), (esperado, textos))


class VentasTests(_Panel):
    def test_compara_con_los_dias_anteriores(self):
        _pedido(10000, hace_dias=3, tipo_entrega="despacho", comuna_sector="Maipú")
        _pedido(5000, hace_dias=10)
        html = self.client.get(reverse("gestion:web") + "?dias=7").content.decode()
        self.assertIn("▲ 100%", html)
        self.assertIn("($5.000 en 1 pedido)", html)
        self.assertIn("Maipú", html)

    def test_si_bajo_lo_dice_y_sin_ventas_antes_no_inventa_un_porcentaje(self):
        _pedido(4000, hace_dias=2)
        _pedido(8000, hace_dias=9)
        self.assertIn("▼ 50%", self.client.get(reverse("gestion:web") + "?dias=7").content.decode())
        PedidoWeb.objects.filter(total=8000).delete()
        html = self.client.get(reverse("gestion:web") + "?dias=7").content.decode()
        self.assertIn("En los 7 días anteriores no hubo ventas web.", html)
        self.assertNotIn("▲", html)

    def test_las_ventas_por_dia_incluyen_los_dias_en_cero(self):
        _pedido(12000, hace_dias=1)
        html = self.client.get(reverse("gestion:web") + "?dias=7").content.decode()
        serie = html.split("Ventas por día", 1)[1].split("</div>\n</div>", 1)[0]
        self.assertEqual(serie.count("Sin ventas"), 7)
        self.assertIn("$12.000", serie)
        self.assertIn("1 pedido", serie)

    def test_hoy_no_dibuja_serie(self):
        self.assertNotIn("Ventas por día", self.client.get(reverse("gestion:web") + "?dias=1").content.decode())

    def test_search_console_ya_no_dice_que_falta_configurar(self):
        html = self.client.get(reverse("gestion:web")).content.decode()
        fila = html.split("Google Search Console", 1)[1].split("</a>", 1)[0]
        self.assertIn("Abrir", fila)
        self.assertNotIn("Falta configurar", fila)
        self.assertIn(reverse("gestion:seo"), html)

    @override_settings(PANEL_VENTA_CORPORATIVA=True)
    def test_el_inicio_corporativo_tambien_resume_la_tienda_web(self):
        _pedido(15900, hace_dias=0)
        _pedido(9000, hace_dias=4)
        html = self.client.get(reverse("gestion:dashboard")).content.decode()
        tarjeta = html.split("Tienda web", 1)[1].split("</a>", 1)[0]
        self.assertIn("1 pedido hoy · 2 en los últimos 7 días", tarjeta)
        self.assertIn("$24.900", tarjeta)
        self.assertIn(reverse("gestion:productos"), html)


class SerieTests(TestCase):
    HOY = date(2026, 11, 15)  # domingo

    def _fila(self, dia, total):
        return (timezone.make_aware(datetime(dia.year, dia.month, dia.day, 12)), total)

    def test_siete_dias_son_ocho_puntos_y_el_mejor_mide_cien(self):
        serie = _serie_ventas([self._fila(date(2026, 11, 14), 8000), self._fila(date(2026, 11, 14), 2000),
                               self._fila(date(2026, 11, 10), 5000)], 7, self.HOY)
        self.assertEqual(len(serie), 8)
        self.assertEqual(serie[-1]["etiqueta"], "Dom 15")
        sabado = serie[-2]
        self.assertEqual((sabado["etiqueta"], sabado["ventas"], sabado["pedidos"], sabado["pct"]),
                         ("Sáb 14", 10000, 2, 100))
        self.assertEqual(next(p for p in serie if p["etiqueta"] == "Mar 10")["pct"], 50)

    def test_noventa_dias_se_agrupan_por_semana(self):
        serie = _serie_ventas([self._fila(date(2026, 11, 9), 3000), self._fila(date(2026, 11, 15), 4000)],
                              90, self.HOY)
        self.assertEqual(len(serie), 13)
        self.assertEqual((serie[-1]["etiqueta"], serie[-1]["ventas"], serie[-1]["pedidos"]),
                         ("Sem. del 9/11", 7000, 2))

    def test_un_pedido_de_madrugada_cuenta_en_el_dia_de_chile(self):
        # 02:30 UTC del 15 son las 23:30 del 14 en Santiago.
        madrugada = datetime(2026, 11, 15, 2, 30, tzinfo=zona_horaria.utc)
        serie = _serie_ventas([(madrugada, 6000)], 7, self.HOY)
        self.assertEqual(next(p for p in serie if p["ventas"])["etiqueta"], "Sáb 14")

    def test_sin_ventas_todo_en_cero_y_hoy_sin_serie(self):
        self.assertTrue(all(p["pct"] == 0 for p in _serie_ventas([], 30, self.HOY)))
        self.assertEqual(_serie_ventas([], 1, self.HOY), [])

    def test_variacion(self):
        self.assertEqual(_variacion(150, 100), 50)
        self.assertEqual(_variacion(50, 100), -50)
        self.assertIsNone(_variacion(100, 0))
