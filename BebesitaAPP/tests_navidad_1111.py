"""/navidad/ con la oferta que confirmo la duena el 11-11-2026 (audios de Tamara).

- Box navideño a pedido: cinta y tarjeta, sin eleccion de color, mismo precio
  de empaque que el Arma tu box.
- Pan de pascua: medio kilo, $8.590, desde el 20 de noviembre, por WhatsApp.
- Pedidos de Navidad hasta el 20 de diciembre.

Todo sale de temporada.OFERTAS_NAVIDAD y se apaga solo despues del 25 de
diciembre: la pagina generica (sin nada de esto) esta en tests_tanda_0311.py.
"""
import datetime
import re
from unittest import mock

from django.test import override_settings

from . import temporada
from .tests_tanda_0311 import _Catalogo, _cuerpo, _faq, _meta, _title

DIA_OFERTA = datetime.date(2026, 11, 11)


@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1490, DESPACHO_HORAS=48,
                   BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl",
                   WHATSAPP_URL="https://wa.me/56900000000")
class NavidadOferta2026Tests(_Catalogo):
    def _html(self, dia=DIA_OFERTA):
        with mock.patch("BebesitaAPP.temporada._hoy", return_value=dia):
            respuesta = self.client.get("/navidad/")
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    def test_title_meta_y_h1_nombran_el_box_navideno_y_el_pan_de_pascua(self):
        html = self._html()
        self.assertEqual(_title(html), "Regalos de Navidad, box navideño y pan de pascua | Dulcecita")
        self.assertLessEqual(len(_title(html)), 60)
        self.assertLessEqual(len(_meta(html)), 155)
        self.assertIn("pan de pascua artesanal de medio kilo a $8.590", _meta(html))
        self.assertIn("Pedidos hasta el 20 de diciembre.", _meta(html))
        self.assertIn("<h1>Regalos de Navidad: box navideño, pan de pascua y dulces artesanales</h1>", html)

    def test_pan_de_pascua_con_lo_que_dijo_la_duena(self):
        cuerpo = _cuerpo(self._html())
        self.assertIn("<h2>Pan de pascua artesanal</h2>", cuerpo)
        self.assertIn("en formato de medio kilo, a $8.590. Lo vendemos desde el 20 de noviembre.", cuerpo)
        self.assertIn("https://wa.me/56900000000?text=Hola+Dulcecita%2C+quiero+encargar+pan+de+pascua.", cuerpo)

    def test_box_navideno_al_precio_del_empaque_de_la_base(self):
        cuerpo = _cuerpo(self._html())
        self.assertIn("empaque navideño con cinta y tarjeta, por los mismos $1.490 del empaque", cuerpo)
        self.assertIn("no se elige color", cuerpo)
        self.assertIn("«¿Para qué ocasión es?»", cuerpo)

    @override_settings(BOX_PRICE=1690)
    def test_si_cambia_el_empaque_el_box_navideno_cambia_solo(self):
        cuerpo = _cuerpo(self._html())
        self.assertIn("por los mismos $1.690 del empaque", cuerpo)

    def test_el_precio_del_pan_sale_de_un_solo_lugar(self):
        oferta = {2026: {**temporada.OFERTAS_NAVIDAD[2026],
                         "pan_de_pascua": {**temporada.OFERTAS_NAVIDAD[2026]["pan_de_pascua"], "precio": 9200}}}
        with mock.patch.dict(temporada.OFERTAS_NAVIDAD, oferta):
            html = self._html()
        self.assertNotIn("8.590", html)
        self.assertIn("a $9.200", _cuerpo(html))
        self.assertIn("a $9.200", _faq(html)["¿Tienen pan de pascua?"])

    def test_fecha_limite_de_pedidos(self):
        cuerpo = _cuerpo(self._html())
        self.assertIn("<b>Recibimos pedidos de Navidad hasta el 20 de diciembre.</b>", cuerpo)
        self.assertIn("<b>Los dulces duran aproximadamente un mes</b>", cuerpo)

    def test_el_faq_suma_pan_y_fecha_limite_y_es_lo_que_se_ve(self):
        html = self._html()
        faq = _faq(html)
        self.assertEqual(len(faq), 5)
        self.assertEqual(faq["¿Tienen pan de pascua?"],
                         "Sí, pan de pascua artesanal en formato de medio kilo, a $8.590. "
                         "Lo vendemos desde el 20 de noviembre. Se encarga por WhatsApp.")
        self.assertEqual(faq["¿Hasta cuándo puedo pedir para Navidad?"],
                         "Recibimos pedidos de Navidad hasta el 20 de diciembre. "
                         "Cada pedido sale 48 horas después del pago.")
        self.assertIn("En Navidad va en empaque navideño con cinta y tarjeta, al mismo precio.",
                      faq["¿Cuánto cuesta un box de dulces para Navidad?"])
        for pregunta, respuesta in faq.items():
            self.assertIn(f"<h3>{pregunta}</h3>", html)
            self.assertIn(f'<p class="mb-0">{respuesta}</p>', html)

    def test_despues_del_20_de_diciembre_dice_que_cerraron_y_no_ofrece_encargar(self):
        html = self._html(datetime.date(2026, 12, 21))
        cuerpo = _cuerpo(html)
        self.assertIn("Los pedidos de Navidad cerraron el 20 de diciembre.", cuerpo)
        self.assertNotIn("Recibimos pedidos de Navidad", cuerpo)
        self.assertNotIn("quiero+encargar+pan+de+pascua", cuerpo)
        self.assertNotIn("Pedidos hasta", _meta(html))
        self.assertEqual(_faq(html)["¿Hasta cuándo puedo pedir para Navidad?"],
                         "Los pedidos de Navidad cerraron el 20 de diciembre.")

    def test_despues_del_25_vuelve_la_pagina_generica_sin_precios_viejos(self):
        for dia in (datetime.date(2026, 12, 26), datetime.date(2027, 3, 1), datetime.date(2027, 11, 5)):
            html = self._html(dia)
            for viejo in ("pan de pascua", "8.590", "box navideño", "20 de diciembre", "cinta y tarjeta"):
                self.assertNotIn(viejo, html, f"{dia}: {viejo}")
            self.assertEqual(_title(html), "Regalos de Navidad: box de dulces artesanales | Dulcecita")
            self.assertEqual(len(_faq(html)), 3)

    def test_no_publica_lo_que_la_duena_no_dijo(self):
        cuerpo = _cuerpo(self._html())
        for invento in ("cupos", "por mayor de pan", "pan de pascua dura", "envío gratis",
                        "despacho gratis", "IVA", "factura", "24 de diciembre", "reservar"):
            self.assertNotIn(invento, cuerpo, invento)

    def test_sin_voseo(self):
        texto = re.sub(r"<[^>]+>", " ", _cuerpo(self._html()))
        voseo = re.compile(r"\b(querés|tenés|podés|mirá|elegí|sabés|pedí|contanos|armá|escribinos|vos)\b", re.I)
        self.assertIsNone(voseo.search(texto))


class OfertaNavidadTests(_Catalogo):
    def test_ventana_y_fechas(self):
        self.assertIsNone(temporada.oferta_navidad(datetime.date(2026, 10, 31)))
        o = temporada.oferta_navidad(datetime.date(2026, 11, 1))
        self.assertEqual(o["pedidos_hasta_texto"], "20 de diciembre")
        self.assertEqual(o["pan"]["desde_texto"], "20 de noviembre")
        self.assertFalse(o["cerrado"])
        self.assertFalse(temporada.oferta_navidad(datetime.date(2026, 12, 20))["cerrado"])
        self.assertTrue(temporada.oferta_navidad(datetime.date(2026, 12, 21))["cerrado"])
        self.assertIsNotNone(temporada.oferta_navidad(datetime.date(2026, 12, 25)))
        self.assertIsNone(temporada.oferta_navidad(datetime.date(2026, 12, 26)))
        # Un año sin oferta cargada no hereda la del anterior.
        self.assertIsNone(temporada.oferta_navidad(datetime.date(2027, 11, 15)))


@override_settings(BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl")
class GorroNavidadTests(_Catalogo):
    """Pedido de la duena (11-11): algo navideño en /navidad/. Solo en temporada."""

    def _html(self, dia):
        with mock.patch("BebesitaAPP.temporada.timezone.localdate", return_value=dia):
            return self.client.get("/navidad/").content.decode()

    def test_en_temporada_el_gorro_acompana_al_navidad(self):
        html = self._html(datetime.date(2026, 11, 11))
        self.assertEqual(html.count('class="gorro-navidad"'), 2)
        self.assertIn('aria-hidden="true"', html.split('class="gorro-navidad"', 1)[1][:200])
        self.assertIn('class="eyebrow eyebrow--navidad"', html)
        self.assertNotIn("{% comment", html)

    def test_fuera_de_temporada_no_hay_gorro(self):
        html = self._html(datetime.date(2027, 1, 10))
        self.assertNotIn("gorro-navidad", html)
        self.assertNotIn("eyebrow--navidad", html)


@override_settings(BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl")
class EsteticaNavidenaTests(_Catalogo):
    """Pedido de la duena (11-11): todo el sitio con estetica navideña en temporada."""

    def _get(self, ruta, dia):
        with mock.patch("BebesitaAPP.temporada.timezone.localdate", return_value=dia):
            return self.client.get(ruta).content.decode()

    def test_en_temporada_todo_el_sitio_se_adorna(self):
        for ruta in ("/", "/productos/", "/arma-tu-box/", "/contacto/", "/navidad/"):
            html = self._get(ruta, datetime.date(2026, 11, 11))
            self.assertIn("temporada-navidad", html.split("<body", 1)[1][:200], ruta)
            self.assertIn("css/navidad.css", html, ruta)
            self.assertIn('<div class="nieve" aria-hidden="true">', html, ruta)

    def test_la_franja_anuncia_la_fecha_limite_y_el_pan(self):
        html = self._get("/", datetime.date(2026, 11, 11))
        franja = html.split('class="dr-topbar dr-topbar--navidad"', 1)[1].split("</a>", 1)[0]
        self.assertIn("Navidad: pedidos hasta el 20 de diciembre · Pan de pascua desde el 20 de noviembre", franja)
        self.assertTrue(franja.startswith(' href="/navidad/">'), franja[:40])
        self.assertNotIn("Compra aquí · Entrega coordinada por WhatsApp", html)

    def test_despues_del_20_la_franja_dice_que_cerraron(self):
        html = self._get("/", datetime.date(2026, 12, 22))
        self.assertIn("Navidad: los pedidos cerraron el 20 de diciembre", html)
        self.assertNotIn("pedidos hasta el 20 de diciembre", html)

    def test_la_portada_nombra_box_navideno_y_pan(self):
        html = self._get("/", datetime.date(2026, 11, 11))
        aviso = html.split('class="box-invita__caja"', 1)[1].split("</section>", 1)[0]
        self.assertIn("Box navideño con cinta y tarjeta y pan de pascua artesanal.", aviso)
        # Pedidos de Tamara (11-11): "mucho texto" y "para curso no, los niños ya salen".
        self.assertNotIn("curso", aviso)
        self.assertIn("Pedidos hasta el 20 de diciembre.", aviso)
        self.assertIn('class="gorro-navidad"', aviso)

    def test_la_promocion_sigue_teniendo_prioridad_en_la_franja(self):
        from .models import Promocion
        dia = datetime.date(2026, 11, 11)
        Promocion.objects.create(nombre="Cyber", porcentaje=10, desde=dia,
                                 hasta=dia + datetime.timedelta(days=3), etiqueta="Cyber")
        html = self._get("/", dia)
        self.assertIn("dr-topbar--promo", html)
        self.assertNotIn("dr-topbar--navidad", html)
        # Una sola franja: la de la promocion (dr-topbar__ir es el boton de adentro).
        self.assertEqual(len(re.findall(r'class="dr-topbar(?: [^"]*)?"', html)), 1)

    def test_fuera_de_temporada_no_queda_nada(self):
        for dia in (datetime.date(2026, 12, 26), datetime.date(2027, 1, 10)):
            html = self._get("/", dia)
            for rastro in ("temporada-navidad", "navidad.css", 'class="nieve"', "dr-topbar--navidad",
                           "gorro-navidad", "pan de pascua"):
                self.assertNotIn(rastro, html, f"{dia}: {rastro}")
            self.assertIn("Compra aquí · Entrega coordinada por WhatsApp", html)

    def test_la_nieve_respeta_reducir_movimiento(self):
        from pathlib import Path
        css = (Path(__file__).parent / "static" / "css" / "navidad.css").read_text(encoding="utf-8")
        bloque = css.split("@media (prefers-reduced-motion: reduce)", 1)[1].split("}", 2)
        self.assertIn(".nieve { display: none; }", bloque[0] + "}")
        self.assertIn("pointer-events: none", css.split(".nieve {", 1)[1].split("}", 1)[0])
