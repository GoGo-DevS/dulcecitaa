"""/navidad/: el precio de partida del box vale para UN box (16-11-2026).

Correccion de la duena, por escrito, sobre la pregunta "¿Cuánto cuesta un box
de dulces para Navidad?": el box parte en $10.000 si el cliente lleva uno; si
quiere mas, se cotiza aparte. La respuesta anterior ("Depende de lo que
elijas: cada dulce va a su precio del catálogo...") no lo decia.

Lo que NO cambia: el precio de partida sale del mismo calculo que Arma tu box,
y lo que declara el FAQPage es exactamente lo que se ve en la pagina.
"""
import datetime
import json
import re
from unittest import mock

from django.test import override_settings

from .tests_tanda_0311 import _Catalogo, _cuerpo, _faq

CON_OFERTA = datetime.date(2026, 11, 16)
SIN_OFERTA = datetime.date(2027, 11, 5)
PREGUNTA = "¿Cuánto cuesta un box de dulces para Navidad?"


@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1490, BOX_MINIMO_TOTAL=10000, DESPACHO_HORAS=48,
                   BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl",
                   WHATSAPP_URL="https://wa.me/56900000000")
class BoxVariosSeCotizanTests(_Catalogo):
    def _html(self, dia=CON_OFERTA):
        with mock.patch("BebesitaAPP.temporada._hoy", return_value=dia):
            respuesta = self.client.get("/navidad/")
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    def test_la_respuesta_dice_el_precio_de_uno_y_que_varios_se_cotizan(self):
        respuesta = _faq(self._html())[PREGUNTA]
        self.assertEqual(
            respuesta,
            "Un box parte en $10.000, con el empaque incluido. Si quieres más de uno, se cotiza aparte: "
            "escríbenos por WhatsApp. En Navidad va en empaque navideño con cinta y tarjeta, al mismo precio.")

    def test_ya_no_queda_la_respuesta_anterior(self):
        html = self._html()
        for viejo in ("Depende de lo que elijas", "El box más simple", "cada dulce va a su precio del catálogo"):
            self.assertNotIn(viejo, html, viejo)

    def test_lo_que_lee_google_es_lo_que_ve_el_cliente(self):
        html = self._html()
        respuesta = _faq(html)[PREGUNTA]
        self.assertIn(f"<h3>{PREGUNTA}</h3>", html)
        self.assertIn(f'<p class="mb-0">{respuesta}</p>', html)
        # Y dentro del schema va el mismo texto, sin etiquetas.
        bloques = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.S)
        declaradas = [nodo for bloque in bloques for nodo in json.loads(bloque).get("@graph", [])
                      if nodo.get("@type") == "FAQPage"]
        self.assertEqual(len(declaradas), 1)
        textos = {q["name"]: q["acceptedAnswer"]["text"] for q in declaradas[0]["mainEntity"]}
        self.assertEqual(textos[PREGUNTA], respuesta)
        self.assertNotIn("<", respuesta)

    def test_el_precio_de_partida_sigue_el_minimo_del_box(self):
        with override_settings(BOX_MINIMO_TOTAL=12000):
            respuesta = _faq(self._html())[PREGUNTA]
        self.assertIn("Un box parte en $12.000, con el empaque incluido.", respuesta)
        self.assertNotIn("10.000", respuesta)

    def test_la_tarjeta_del_box_tambien_lo_dice_a_la_vista_y_lleva_a_whatsapp(self):
        cuerpo = _cuerpo(self._html())
        tarjeta = cuerpo.split('<article class="nav-card">', 2)[1].split("</article>", 1)[0]
        self.assertIn("<h2>Box navideño para regalar</h2>", tarjeta)
        # A la vista: antes del bloque plegado "Más sobre el box".
        a_la_vista = tarjeta.split('<details class="nav-mas">', 1)[0]
        self.assertIn("El box parte en $10.000, con el empaque incluido.", a_la_vista)
        self.assertRegex(
            a_la_vista,
            r'¿Más de un box\? Se cotiza aparte por <a href="https://wa\.me/56900000000[^"]*"[^>]*>WhatsApp</a>\.')

    def test_un_año_sin_oferta_lo_dice_igual_y_sin_empaque_navideno(self):
        html = self._html(SIN_OFERTA)
        respuesta = _faq(html)[PREGUNTA]
        self.assertEqual(respuesta, "Un box parte en $10.000, con el empaque incluido. "
                                    "Si quieres más de uno, se cotiza aparte: escríbenos por WhatsApp.")
        self.assertIn("¿Más de un box? Se cotiza aparte", _cuerpo(html))
