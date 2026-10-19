"""SEO on-page (07-10-2026): title y description de /delivery/, textos propios
de cada ficha, enlaces internos del catalogo a las fichas y el JSON-LD de
Fichas de comerciantes (description y brand en cada producto).
"""
import json
import re

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from . import fichas_seo
from .models import Producto

SLUGS = {
    "Barquillos Rellenos Bañados en Chocolate": ("barquillos-rellenos-banados-en-chocolate", 1290),
    "Alfajores": ("alfajores", 1590),
    "Cuchuflís bañados": ("cuchuflis-banados", 1590),
    "Cuchuflís rellenos": ("cuchuflis-rellenos", 1190),
    "Torta de cuchuflís": ("torta-de-cuchuflis", 14990),
}


def _crear(nombre, precio, descripcion="Texto de la duena"):
    return Producto.objects.create(
        nombre=nombre, descripcion=descripcion, precio=precio, visible=True,
        imagen=SimpleUploadedFile("a.jpg", b"img", content_type="image/jpeg"))


def _ld(html):
    nodos = []
    for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        data = json.loads(bloque)
        nodos += data.get("@graph", [data])
    return nodos


def _title(html):
    return re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()


def _meta(html):
    return re.search(r'<meta name="description" content="([^"]*)"', html).group(1)


@override_settings(MINIMO_UNIDADES=10, DESPACHO_HORAS=48, BRAND_NAME="Dulcecita")
class DeliverySeoTests(TestCase):
    def test_title_y_description_nuevos_y_dentro_del_largo(self):
        html = self.client.get("/delivery/").content.decode()
        titulo, meta = _title(html), _meta(html)
        # 19-10-2026: Santiago adelante, que es la busqueda local que no tenia pagina.
        self.assertEqual(titulo, "Delivery de alfajores en Santiago y todo Chile | Dulcecita")
        self.assertLessEqual(len(titulo), 60)
        self.assertLessEqual(len(meta), 155)
        # Promete solo lo que la pagina muestra: Paket, Santiago por WhatsApp,
        # el minimo y las horas.
        for dato in ("Paket", "Santiago", "WhatsApp", "10 unidades", "48 h"):
            self.assertIn(dato, meta)
        self.assertIn("<h1>Delivery en Santiago y despacho a todo Chile</h1>", html)

    def test_no_se_imprime_marcado_de_plantilla(self):
        html = self.client.get("/delivery/").content.decode()
        self.assertNotIn("{#", html)
        self.assertNotIn("{% comment", html)
        self.assertNotIn("pagina con mas impresiones", html)


@override_settings(MINIMO_UNIDADES=10, DESPACHO_HORAS=48, BRAND_NAME="Dulcecita")
class FichasSeoTests(TestCase):
    def setUp(self):
        self.productos = {nombre: _crear(nombre, precio) for nombre, (_, precio) in SLUGS.items()}

    def test_los_slugs_calzan_con_los_textos_propios(self):
        for nombre, (slug, _) in SLUGS.items():
            self.assertEqual(self.productos[nombre].slug, slug)
            self.assertIsNotNone(fichas_seo.ficha(self.productos[nombre]), slug)

    def test_title_trabaja_la_busqueda_y_respeta_el_largo(self):
        esperados = {
            "alfajores": "Alfajores para regalar desde $1.590 | Dulcecita",
            "torta-de-cuchuflis": "Torta de cuchuflís decorada desde $14.990 | Dulcecita",
            "barquillos-rellenos-banados-en-chocolate": "Barquillos rellenos de manjar desde $1.290 | Dulcecita",
        }
        for slug, esperado in esperados.items():
            html = self.client.get(f"/productos/{slug}/").content.decode()
            self.assertEqual(_title(html), esperado)
        for nombre, (slug, _) in SLUGS.items():
            html = self.client.get(f"/productos/{slug}/").content.decode()
            self.assertLessEqual(len(_title(html)), 60, slug)
            self.assertLessEqual(len(_meta(html)), 155, slug)

    def test_si_el_precio_no_cabe_se_cae_el_precio_no_la_palabra(self):
        torta = self.productos["Torta de cuchuflís"]
        torta.precio = 123456789
        torta.save()
        titulo = fichas_seo.titulo(torta)
        self.assertLessEqual(len(titulo), 60)
        self.assertTrue(titulo.startswith("Torta de cuchuflís"))

    def test_h1_y_texto_propio_en_la_ficha(self):
        html = self.client.get("/productos/alfajores/").content.decode()
        self.assertIn('<h1 class="detail-titulo">Alfajores artesanales para regalar</h1>', html)
        self.assertIn("Sobre este producto", html)
        self.assertNotIn("{% comment", html)

    def test_cuchuflis_banados_y_rellenos_no_dicen_lo_mismo(self):
        banados = self.client.get("/productos/cuchuflis-banados/").content.decode()
        rellenos = self.client.get("/productos/cuchuflis-rellenos/").content.decode()
        self.assertNotEqual(_meta(banados), _meta(rellenos))
        self.assertNotEqual(_title(banados), _title(rellenos))
        for parrafo in fichas_seo.parrafos(self.productos["Cuchuflís bañados"]):
            self.assertNotIn(parrafo, rellenos)

    def test_la_ficha_enlaza_a_las_otras_fichas(self):
        html = self.client.get("/productos/alfajores/").content.decode()
        self.assertIn('href="/productos/cuchuflis-banados/"', html)
        self.assertIn('href="/productos/cuchuflis-rellenos/"', html)
        self.assertNotIn('class="dr-tile" href="/productos/alfajores/"', html)

    def test_el_catalogo_enlaza_a_cada_ficha(self):
        html = self.client.get("/productos/").content.decode()
        for slug, _ in SLUGS.values():
            self.assertIn(f'href="/productos/{slug}/"', html, slug)

    def test_producto_nuevo_sin_textos_propios_no_se_rompe(self):
        nuevo = _crear("Chilenitos", 990, descripcion="Chilenitos con manjar.")
        html = self.client.get(f"/productos/{nuevo.slug}/").content.decode()
        self.assertEqual(_title(html), "Chilenitos artesanales desde $990 | Dulcecita")
        self.assertEqual(_meta(html), "Chilenitos con manjar.")
        # 16-10-2026: toda ficha trae las preguntas comunes de la duena (duracion,
        # personalizacion, por mayor), aunque no tenga preguntas propias.
        self.assertIn("¿Cuánto duran y cómo se guardan?", html)

    def test_sin_voseo(self):
        textos = []
        for p in self.productos.values():
            textos += [fichas_seo.titulo(p), fichas_seo.h1(p), fichas_seo.descripcion(p)]
            textos += fichas_seo.parrafos(p)
        voseo = re.compile(r"\b(querés|tenés|podés|mirá|elegí|sabés|pedí|contanos|armá)\b", re.I)
        for t in textos:
            self.assertIsNone(voseo.search(t), t)


@override_settings(MINIMO_UNIDADES=10, BRAND_NAME="Dulcecita")
class JsonLdComercianteTests(TestCase):
    def setUp(self):
        self.alfajor = _crear("Alfajores", 1590, descripcion="Alfajor de triple capa")
        # La duena puede dejar la descripcion vacia desde el panel.
        self.vacio = _crear("Cuchuflís rellenos", 1190, descripcion="")

    def test_el_itemlist_del_catalogo_trae_description_y_brand(self):
        nodos = _ld(self.client.get("/productos/").content.decode())
        lista = next(n for n in nodos if n.get("@type") == "ItemList")
        self.assertEqual(len(lista["itemListElement"]), 2)
        for item in lista["itemListElement"]:
            producto = item["item"]
            self.assertTrue(producto["description"].strip(), producto["name"])
            self.assertEqual(producto["brand"], {"@type": "Brand", "name": "Dulcecita"})

    def test_la_ficha_trae_description_aunque_la_base_este_vacia(self):
        nodos = _ld(self.client.get("/productos/cuchuflis-rellenos/").content.decode())
        producto = next(n for n in nodos if n.get("@type") == "Product")
        self.assertIn("rellenos de manjar", producto["description"])
        self.assertEqual(producto["brand"]["name"], "Dulcecita")

    def test_la_descripcion_de_la_duena_manda(self):
        nodos = _ld(self.client.get("/productos/alfajores/").content.decode())
        producto = next(n for n in nodos if n.get("@type") == "Product")
        self.assertEqual(producto["description"], "Alfajor de triple capa")


@override_settings(MINIMO_UNIDADES=10, BRAND_NAME="Dulcecita")
class PreguntasComunesTests(TestCase):
    """Las respuestas de la duena del 16-10 en todas las fichas, sin duplicar."""

    def test_no_repite_una_pregunta_que_la_duena_ya_cargo(self):
        from .models import PreguntaFrecuente
        p = _crear("Alfajores", 1590)
        PreguntaFrecuente.objects.create(producto=p, pregunta="¿Cuanto duran y como se guardan?",
                                         respuesta="Un mes.", activa=True)
        html = self.client.get(f"/productos/{p.slug}/").content.decode()
        self.assertEqual(html.count("uran y c"), 2)  # 1 en la pagina + 1 en el schema

    def test_el_schema_declara_lo_mismo_que_se_ve(self):
        p = _crear("Alfajores", 1590)
        html = self.client.get(f"/productos/{p.slug}/").content.decode()
        faq = [n for n in _ld(html) if n.get("@type") == "FAQPage"][0]
        for q in faq["mainEntity"]:
            self.assertIn("<h3>%s</h3>" % q["name"], html)
        self.assertIn("desde 20 unidades", html)


@override_settings(MINIMO_UNIDADES=10, DESPACHO_HORAS=48, BRAND_NAME="Dulcecita",
                   SITE_URL="https://dulcecita.cl")
class Tanda1SeoTests(TestCase):
    """Tanda 1 del metodo /seo-gogodevs (19-10-2026).

    Search Console decia: 90 % de las impresiones son la marca, dos fichas
    "descubiertas, sin indexar" con 7 enlaces internos, y ninguna pagina con
    las palabras que la gente usa (dulces corporativos, box de dulces para
    regalar, alfajores en Santiago, por mayor).
    """

    def setUp(self):
        self.productos = {nombre: _crear(nombre, precio) for nombre, (_, precio) in SLUGS.items()}
        torta = self.productos["Torta de cuchuflís"]
        torta.en_box = False
        torta.save()

    def _pie(self, html):
        return html.split('<footer', 1)[1]

    def test_el_pie_de_todas_las_paginas_enlaza_a_cada_ficha(self):
        for ruta in ("/", "/productos/", "/arma-tu-box/", "/delivery/", "/corporativo/", "/contacto/",
                     "/productos/alfajores/"):
            pie = self._pie(self.client.get(ruta).content.decode())
            for slug, _ in SLUGS.values():
                self.assertIn(f'href="/productos/{slug}/"', pie, f"{ruta} -> {slug}")

    def test_un_producto_oculto_no_sale_en_el_pie(self):
        oculto = _crear("Secreto", 100)
        oculto.visible = False
        oculto.save()
        self.assertNotIn(f'href="/productos/{oculto.slug}/"', self._pie(self.client.get("/").content.decode()))

    def test_el_pie_no_agrega_una_consulta_por_producto(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as c:
            self.client.get("/delivery/")
        de_producto = [q for q in c.captured_queries if "bebesitaapp_producto" in q["sql"].lower()]
        self.assertEqual(len(de_producto), 1)

    def test_links_lleva_noindex_y_no_va_en_el_sitemap(self):
        html = self.client.get("/links/").content.decode()
        self.assertIn('<meta name="robots" content="noindex, follow">', html)
        self.assertNotIn("{% comment", html)
        sitemap = self.client.get("/sitemap.xml").content.decode()
        self.assertNotIn("/links/", sitemap)
        self.assertIn("https://dulcecita.cl/corporativo/", sitemap)

    def test_titles_y_descriptions_con_la_intencion_y_dentro_del_largo(self):
        esperados = {
            "/productos/": ("Comprar alfajores y cuchuflís por mayor | Dulcecita",
                            "<h1>Alfajores, barquillos y cuchuflís artesanales</h1>"),
            "/corporativo/": ("Dulces corporativos personalizados para empresas | Dulcecita",
                              "<h1>Dulces corporativos para tu empresa, con tu marca</h1>"),
            "/arma-tu-box/": ("Box de dulces para regalar, armado a tu gusto | Dulcecita",
                              "<h1>Box de dulces para regalar, a tu gusto</h1>"),
        }
        for ruta, (titulo, h1) in esperados.items():
            html = self.client.get(ruta).content.decode()
            self.assertEqual(_title(html), titulo, ruta)
            self.assertLessEqual(len(_title(html)), 60, ruta)
            self.assertLessEqual(len(_meta(html)), 155, ruta)
            self.assertIn(h1, html, ruta)
            self.assertNotIn("{% comment", html)

    def test_el_catalogo_dice_por_mayor_como_promete_su_title(self):
        html = self.client.get("/productos/").content.decode()
        self.assertIn("Venta por mayor desde 20 unidades", html)

    def test_corporativo_dice_que_hace_falta_para_cotizar_sin_inventar_plazos(self):
        html = self.client.get("/corporativo/").content.decode()
        self.assertIn("Qué necesitamos para cotizar", html)
        self.assertIn("desde 20 unidades", html)
        self.assertIn('href="/productos/alfajores/"', html.split("<footer", 1)[0])
        # Lo que la duena no confirmo no se publica.
        for invento in ("IVA", "3 días", "días hábiles de producción"):
            self.assertNotIn(invento, html)

    def test_el_box_enlaza_a_los_productos_que_lo_arman_y_no_a_la_torta(self):
        html = self.client.get("/arma-tu-box/").content.decode().split("<footer", 1)[0]
        self.assertIn('href="/productos/alfajores/"', html)
        self.assertIn('href="/productos/cuchuflis-banados/"', html)
        self.assertNotIn('href="/productos/torta-de-cuchuflis/"', html)
        self.assertIn("Navidad", html)

    def test_delivery_enlaza_a_las_fichas(self):
        html = self.client.get("/delivery/").content.decode().split("<footer", 1)[0]
        self.assertIn('href="/productos/barquillos-rellenos-banados-en-chocolate/"', html)

    def test_la_torta_responde_ninos_tamano_precio_y_donde_comprar(self):
        html = self.client.get("/productos/torta-de-cuchuflis/").content.decode()
        for dato in ("cumpleaños infantiles", "50 o 100", "El precio depende del tamaño", "Se compra aquí mismo",
                     "48 horas"):
            self.assertIn(dato, html)

    def test_la_ficha_de_alfajores_dice_chile_y_por_mayor(self):
        html = self.client.get("/productos/alfajores/").content.decode()
        self.assertIn("Santiago de Chile", html)
        self.assertIn("desde 20 unidades", html)
