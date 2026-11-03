"""Tanda SEO del 03-11-2026 (encargo de Diego: top 10 a fin de año, Navidad).

1. Fichas de barquillos y cuchuflis: "cuanto cuestan" con el precio de la
   BASE, Santiago y por mayor en el texto, y el pie enlazando con la palabra
   que se busca.
2. Schema: el minimo de la oferta es el de cada producto (la torta, 1).
3. /navidad/ para personas, solo con la oferta que ya existe; las empresas
   siguen en /corporativo/.
4. /arma-tu-box/ con punto de miles en todos sus precios.
La conexion a la base (los 500 del 02-11) esta en tests_conexion.py.
"""
import datetime
import json
import re
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from . import fichas_seo
from .models import Opcion, PrecioCombinacion, Producto, Promocion
from .templatetags.plata import pesos


def _crear(nombre, precio, pack=1, coberturas=(), **extra):
    p = Producto.objects.create(
        nombre=nombre, descripcion="Texto de la duena", precio=precio, visible=True,
        unidades_por_pack=pack, imagen=SimpleUploadedFile("a.jpg", b"img", content_type="image/jpeg"),
        **extra)
    if coberturas:
        p.opciones.add(*coberturas)
    return p


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


def _cuerpo(html):
    """Lo que esta entre el menu y el pie: el contenido propio de la pagina."""
    return html.split('<main class="site-main">', 1)[1].split("<footer", 1)[0]


def _faq(html):
    faq = [n for n in _ld(html) if n.get("@type") == "FAQPage"][0]
    return {q["name"]: q["acceptedAnswer"]["text"] for q in faq["mainEntity"]}


class _Catalogo(TestCase):
    """El catalogo como lo deja catalogo_inicial: 4 dulces con cobertura y la torta."""

    def setUp(self):
        self.choc = Opcion.objects.create(tipo="cobertura", nombre="Chocolate", orden=1)
        self.blanco = Opcion.objects.create(tipo="cobertura", nombre="Chocolate blanco", orden=2)
        cob = (self.choc, self.blanco)
        self.barquillos = _crear("Barquillos Rellenos Bañados en Chocolate", 1290, coberturas=cob, orden=0)
        self.alfajores = _crear("Alfajores", 1590, coberturas=cob, orden=1)
        self.banados = _crear("Cuchuflís bañados", 1590, pack=4, coberturas=cob, orden=3)
        self.rellenos = _crear("Cuchuflís rellenos", 1190, pack=4, orden=4)
        self.torta = _crear("Torta de cuchuflís", 14990, orden=5, minimo=1, en_box=False)
        t50 = Opcion.objects.create(tipo="tamano", nombre="50 cuchuflís", orden=1)
        sin = Opcion.objects.create(tipo="cobertura", nombre="Sin cobertura", orden=0)
        self.torta.opciones.add(t50, sin, self.choc)
        for cob_torta, precio in [(sin, 14990), (self.choc, 17990)]:
            pc = PrecioCombinacion.objects.create(producto=self.torta, precio=precio)
            pc.opciones.set([t50, cob_torta])
            pc.actualizar_clave()


# --- 1. fichas ---------------------------------------------------------------

@override_settings(MINIMO_UNIDADES=10, DESPACHO_HORAS=48, BRAND_NAME="Dulcecita",
                   SITE_URL="https://dulcecita.cl")
class FichasCuantoCuestanTests(_Catalogo):
    CASOS = {
        "barquillos-rellenos-banados-en-chocolate": (
            "¿Cuánto cuestan los barquillos rellenos?",
            "$1.290 por unidad, con chocolate o chocolate blanco."),
        "cuchuflis-banados": (
            "¿Cuánto cuestan los cuchuflís bañados en chocolate?",
            "$1.590 la bolsita de 4, con chocolate o chocolate blanco."),
        "cuchuflis-rellenos": (
            "¿Cuánto cuestan los cuchuflís rellenos?",
            "$1.190 la bolsita de 4."),
        "alfajores": (
            "¿Cuánto cuesta un alfajor artesanal?",
            "$1.590 por unidad, con chocolate o chocolate blanco."),
    }

    def test_cada_ficha_responde_cuanto_cuesta_con_el_precio_de_la_base(self):
        for slug, (pregunta, respuesta) in self.CASOS.items():
            html = self.client.get(f"/productos/{slug}/").content.decode()
            self.assertIn(f"<h3>{pregunta}</h3>", html, slug)
            self.assertIn(f'<p class="mb-0">{respuesta}</p>', html, slug)
            # El schema declara exactamente lo que se ve.
            self.assertEqual(_faq(html)[pregunta], respuesta, slug)

    def test_el_precio_respondido_es_el_que_cobra_el_carrito(self):
        for p in (self.barquillos, self.banados, self.alfajores):
            respuesta = fichas_seo.pregunta_precio(p).respuesta
            for op in (self.choc, self.blanco):
                self.assertIn(f"${pesos(p.precio_para([op.id]))}", respuesta, p.nombre)

    def test_si_la_duena_cambia_el_precio_la_respuesta_cambia_sola(self):
        self.barquillos.precio = 1390
        self.barquillos.save()
        html = self.client.get("/productos/barquillos-rellenos-banados-en-chocolate/").content.decode()
        preguntas = html.split("Lo que más nos preguntan", 1)[1]
        self.assertIn("$1.390 por unidad", preguntas)
        self.assertNotIn("$1.290", preguntas)

    def test_si_una_cobertura_cuesta_distinto_cada_precio_va_con_la_suya(self):
        self.blanco.recargo = 100
        self.blanco.save()
        respuesta = fichas_seo.pregunta_precio(self.barquillos).respuesta
        self.assertEqual(respuesta, "$1.290 por unidad, con chocolate; $1.390, con chocolate blanco.")

    def test_con_promocion_responde_el_precio_rebajado_y_hasta_cuando(self):
        from django.utils import timezone
        hoy = timezone.localdate()
        Promocion.objects.create(nombre="Navidad", porcentaje=10, desde=hoy,
                                 hasta=hoy + datetime.timedelta(days=5), etiqueta="Navidad")
        respuesta = fichas_seo.pregunta_precio(self.barquillos).respuesta
        self.assertIn(f"${pesos(self.barquillos.precio_para([self.choc.id]))} por unidad", respuesta)
        self.assertNotIn("$1.290", respuesta)
        self.assertIn("10% de descuento hasta el", respuesta)

    def test_barquillos_y_cuchuflis_dicen_santiago_y_por_mayor(self):
        for slug in ("barquillos-rellenos-banados-en-chocolate", "cuchuflis-banados", "cuchuflis-rellenos"):
            parrafos = self.client.get(f"/productos/{slug}/").content.decode().split(
                "Sobre este producto", 1)[1].split("También te puede gustar", 1)[0]
            self.assertIn("Santiago", parrafos, slug)
            self.assertIn("por mayor", parrafos.lower(), slug)
            self.assertIn("WhatsApp", parrafos, slug)
        barquillos = self.client.get("/productos/barquillos-rellenos-banados-en-chocolate/").content.decode()
        self.assertIn("Por mayor, desde 20 unidades al mismo precio por unidad.", barquillos)

    def test_lo_que_la_duena_no_confirmo_no_aparece_en_las_fichas(self):
        for slug in ("barquillos-rellenos-banados-en-chocolate", "cuchuflis-banados", "cuchuflis-rellenos"):
            cuerpo = _cuerpo(self.client.get(f"/productos/{slug}/").content.decode())
            for invento in ("reventa", "revender", "precio mayorista", "descuento por volumen", "IVA",
                            "factura", "envío gratis", "comunas"):
                self.assertNotIn(invento, cuerpo, f"{slug}: {invento}")

    def test_titles_y_metas_siguen_dentro_del_largo(self):
        for slug in self.CASOS:
            html = self.client.get(f"/productos/{slug}/").content.decode()
            self.assertLessEqual(len(_title(html)), 60, slug)
            self.assertLessEqual(len(_meta(html)), 155, slug)

    def test_un_producto_sin_ficha_propia_no_inventa_pregunta_de_precio(self):
        nuevo = _crear("Chilenitos", 990)
        self.assertIsNone(fichas_seo.pregunta_precio(nuevo))

    def test_el_pie_enlaza_con_la_palabra_que_se_busca(self):
        pie = self.client.get("/delivery/").content.decode().split("<footer", 1)[1]
        for producto, ancla in [(self.barquillos, "Barquillos rellenos"),
                                (self.alfajores, "Alfajores artesanales"),
                                (self.banados, "Cuchuflís bañados en chocolate"),
                                (self.rellenos, "Cuchuflís rellenos de manjar"),
                                (self.torta, "Torta de cuchuflís")]:
            self.assertIn(f'href="{producto.get_absolute_url()}" class="footer-link">{ancla}</a>', pie)

    def test_un_producto_sin_ficha_enlaza_con_su_nombre(self):
        nuevo = _crear("Chilenitos", 990)
        pie = self.client.get("/").content.decode().split("<footer", 1)[1]
        self.assertIn(f'href="{nuevo.get_absolute_url()}" class="footer-link">Chilenitos</a>', pie)


# --- 2. schema ---------------------------------------------------------------

@override_settings(MINIMO_UNIDADES=10, BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl")
class SchemaMinimoTests(_Catalogo):
    def _oferta(self, slug):
        html = self.client.get(f"/productos/{slug}/").content.decode()
        producto = next(n for n in _ld(html) if n.get("@type") == "Product")
        return producto["offers"]

    def test_la_torta_se_ofrece_desde_una_como_dice_su_ficha(self):
        self.assertEqual(self._oferta("torta-de-cuchuflis")["eligibleQuantity"]["minValue"], 1)

    def test_los_demas_desde_el_minimo_general(self):
        self.assertEqual(self._oferta("alfajores")["eligibleQuantity"]["minValue"], 10)
        self.assertEqual(self._oferta("cuchuflis-banados")["eligibleQuantity"]["unitText"], "bolsita")


# --- 3. /navidad/ --------------------------------------------------------------

@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1490, DESPACHO_HORAS=48,
                   BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl",
                   WHATSAPP_URL="https://wa.me/56900000000")
class NavidadTests(_Catalogo):
    def _html(self):
        respuesta = self.client.get("/navidad/")
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    def test_title_meta_h1_y_canonical(self):
        html = self._html()
        self.assertEqual(_title(html), "Regalos de Navidad: box de dulces artesanales | Dulcecita")
        self.assertLessEqual(len(_title(html)), 60)
        self.assertLessEqual(len(_meta(html)), 155)
        self.assertIn("Navidad", _meta(html))
        self.assertIn("<h1>Regalos de Navidad: box de dulces, detalles y tortas</h1>", html)
        self.assertIn('<link rel="canonical" href="https://dulcecita.cl/navidad/">', html)
        self.assertNotIn("{% comment", html)
        self.assertNotIn("{#", html)

    def test_los_precios_son_los_de_la_base(self):
        cuerpo = _cuerpo(self._html())
        self.assertIn('Alfajores artesanales</a>: $1.590 por unidad', cuerpo)
        self.assertIn('Barquillos rellenos</a>: $1.290 por unidad', cuerpo)
        self.assertIn('Cuchuflís bañados en chocolate</a>: $1.590 la bolsita de 4', cuerpo)
        self.assertIn('Cuchuflís rellenos de manjar</a>: $1.190 la bolsita de 4', cuerpo)
        self.assertIn("el empaque cuesta $1.490", cuerpo)
        # La torta con sus precios por combinacion, del mismo calculo que su ficha.
        self.assertIn(fichas_seo._texto_precios(self.torta), cuerpo)

    def test_el_ejemplo_de_box_suma_lo_que_cobraria_arma_tu_box(self):
        cuerpo = _cuerpo(self._html())
        # 3 barquillos + 3 alfajores + 3 bolsitas de cuchuflis banados + empaque.
        esperado = 3 * 1290 + 3 * 1590 + 3 * 1590 + 1490
        self.assertIn(f"cuesta ${pesos(esperado)} con el empaque", cuerpo)
        self.assertIn("3 bolsitas de 4 cuchuflís bañados en chocolate", cuerpo)
        # El box mas simple: 3 del dulce mas barato (bolsita de rellenos) + empaque.
        self.assertIn(f"parte en ${pesos(3 * 1190 + 1490)}", cuerpo)

    def test_si_la_duena_cambia_un_precio_la_pagina_cambia_sola(self):
        self.alfajores.precio = 1690
        self.alfajores.save()
        cuerpo = _cuerpo(self._html())
        self.assertIn('Alfajores artesanales</a>: $1.690 por unidad', cuerpo)
        self.assertIn(f"cuesta ${pesos(3 * 1290 + 3 * 1690 + 3 * 1590 + 1490)} con el empaque", cuerpo)

    def test_con_promocion_los_precios_ya_vienen_rebajados(self):
        from django.utils import timezone
        hoy = timezone.localdate()
        Promocion.objects.create(nombre="Navidad", porcentaje=10, desde=hoy,
                                 hasta=hoy + datetime.timedelta(days=5), etiqueta="Navidad")
        cuerpo = _cuerpo(self._html())
        rebajado = self.alfajores.precio_para([self.choc.id])
        self.assertIn(f"Alfajores artesanales</a>: ${pesos(rebajado)} por unidad", cuerpo)
        self.assertIn("ya aplicado", cuerpo)

    def test_no_publica_nada_que_la_duena_no_haya_confirmado(self):
        cuerpo = _cuerpo(self._html())
        for invento in ("box navideño", "Box navideño", "empaque navideño", "caja navideña",
                        "fecha límite", "último día", "hasta el", "cupos", "IVA", "factura",
                        "envío gratis", "despacho gratis", "24 de diciembre", "reventa"):
            self.assertNotIn(invento, cuerpo, invento)

    def test_una_intencion_por_url_navidad_para_personas_corporativo_para_empresas(self):
        navidad = self._html()
        corporativo = self.client.get("/corporativo/").content.decode()
        self.assertNotIn("fin de año", _title(navidad))
        self.assertNotIn("corporativ", _title(navidad).lower())
        self.assertEqual(_title(corporativo), "Dulces corporativos y regalos de fin de año | Dulcecita")
        # Se derivan entre ellas desde el contenido, no solo desde el pie.
        self.assertIn('href="/corporativo/"', _cuerpo(navidad))
        self.assertIn('href="/navidad/"', _cuerpo(corporativo))

    def test_enlaza_a_cada_ficha_al_box_y_al_delivery(self):
        cuerpo = _cuerpo(self._html())
        for p in (self.barquillos, self.alfajores, self.banados, self.rellenos, self.torta):
            self.assertIn(f'href="{p.get_absolute_url()}"', cuerpo, p.nombre)
        self.assertIn('href="/arma-tu-box/"', cuerpo)
        self.assertIn('href="/delivery/"', cuerpo)

    def test_whatsapp_con_el_mensaje_escrito(self):
        cuerpo = _cuerpo(self._html())
        self.assertIn("https://wa.me/56900000000?text=Hola+Dulcecita%2C+quiero+dulces+para+regalar+en+Navidad.",
                      cuerpo)

    def test_el_faq_del_schema_es_lo_que_se_ve(self):
        html = self._html()
        faq = _faq(html)
        self.assertEqual(len(faq), 3)
        for pregunta, respuesta in faq.items():
            self.assertIn(f"<h3>{pregunta}</h3>", html)
            self.assertIn(f'<p class="mb-0">{respuesta}</p>', html)
        migas = next(n for n in _ld(html) if n.get("@type") == "BreadcrumbList")
        self.assertEqual(migas["itemListElement"][-1]["item"], "https://dulcecita.cl/navidad/")

    def test_esta_en_el_sitemap(self):
        self.assertIn("https://dulcecita.cl/navidad/", self.client.get("/sitemap.xml").content.decode())

    def test_sin_voseo(self):
        texto = re.sub(r"<[^>]+>", " ", _cuerpo(self._html()))
        voseo = re.compile(r"\b(querés|tenés|podés|mirá|elegí|sabés|pedí|contanos|armá|escribinos|vos)\b", re.I)
        self.assertIsNone(voseo.search(texto))

    def test_no_hace_una_consulta_por_producto(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as antes:
            self._html()
        for i in range(3):
            _crear(f"Extra {i}", 1000 + i, coberturas=(self.choc, self.blanco), orden=10 + i)
        with CaptureQueriesContext(connection) as despues:
            self._html()
        self.assertEqual(len(antes.captured_queries), len(despues.captured_queries))


@override_settings(BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl")
class TemporadaNavidadTests(_Catalogo):
    def test_se_enciende_en_noviembre_y_se_apaga_despues_del_25(self):
        from .temporada import es_navidad
        self.assertFalse(es_navidad(datetime.date(2026, 10, 31)))
        self.assertTrue(es_navidad(datetime.date(2026, 11, 1)))
        self.assertTrue(es_navidad(datetime.date(2026, 12, 25)))
        self.assertFalse(es_navidad(datetime.date(2026, 12, 26)))
        self.assertFalse(es_navidad(datetime.date(2027, 1, 10)))

    def _portada(self, dia):
        with mock.patch("BebesitaAPP.temporada.timezone.localdate", return_value=dia):
            return self.client.get("/").content.decode()

    def test_en_temporada_el_menu_y_la_portada_empujan_navidad(self):
        html = self._portada(datetime.date(2026, 11, 3))
        menu = html.split('id="navbarMain"', 1)[1].split("</nav>", 1)[0]
        self.assertIn('href="/navidad/">Navidad</a>', menu)
        self.assertIn('<a href="/navidad/" class="btn-main">Ver regalos de Navidad</a>', html)

    def test_fuera_de_temporada_se_apagan_pero_el_pie_la_sigue_enlazando(self):
        html = self._portada(datetime.date(2027, 1, 10))
        menu = html.split('id="navbarMain"', 1)[1].split("</nav>", 1)[0]
        self.assertNotIn("/navidad/", menu)
        self.assertNotIn("Ver regalos de Navidad", html)
        self.assertIn('href="/navidad/" class="footer-link">Regalos de Navidad</a>', html.split("<footer", 1)[1])
        # La pagina sigue publicada todo el año.
        self.assertEqual(self.client.get("/navidad/").status_code, 200)


# --- 4. /arma-tu-box/ ----------------------------------------------------------

@override_settings(MINIMO_BOX=3, BOX_PRICE=1490)
class BoxConPuntoDeMilesTests(_Catalogo):
    def test_todos_los_precios_del_box_con_punto_de_miles(self):
        html = self.client.get("/arma-tu-box/").content.decode()
        self.assertIn("<small>$1.290 c/u</small>", html)
        self.assertIn("<strong>$1.490</strong>", html)
        self.assertIn('data-box-total>$1.490</p>', html)
        self.assertNotRegex(_cuerpo(html), r"\$\d{4,}\b")
        # El total que calcula el navegador usa el mismo formato.
        self.assertIn(".replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.')", html)


@override_settings(MINIMO_BOX=3, BOX_PRICE=1490, BRAND_NAME="Dulcecita")
class NavidadBoxDesdeTests(_Catalogo):
    def test_el_box_mas_simple_usa_la_fila_mas_barata_aunque_no_sea_la_primera_cobertura(self):
        # Rellenos fuera: el mas barato pasa a ser el barquillo de chocolate BLANCO.
        self.rellenos.visible = False
        self.rellenos.save()
        self.blanco.recargo = -100
        self.blanco.save()
        cuerpo = _cuerpo(self.client.get("/navidad/").content.decode())
        self.assertIn(f"parte en ${pesos(3 * 1190 + 1490)}", cuerpo)
