"""/corporativo/ con menos texto y con las fotos nuevas de Tamara (16-11-2026).

Pedido de Diego mirando la pagina en vivo: "sigue habiendo mucho texto aca" y
"las fotos, utiliza las nuevas que te pase".

- Menos texto A LA VISTA: una tarjeta con foto por cada cosa que se ofrece, lo
  que hace falta para cotizar en una franja y los plazos plegados (siguen en
  la pagina para Google y para quien los abra).
- Fotos: las de Tamara del 15-11, no las de AZA. Con nombre, alt, ancho y
  alto, WebP liviano, y la de portada sin carga diferida.
- El aviso de "solicitud enviada" queda junto al formulario, y el formulario
  envia a #cotizar: antes el aviso quedaba al fondo y nadie lo veia.

Lo que la pagina DICE (boleta, mismo precio por volumen, desde 20, sin fechas
limite inventadas) sigue probado en tests_seo_fichas.py.
"""
import datetime
import html as html_lib
import re
from pathlib import Path
from unittest import mock

from django.core import mail
from django.test import override_settings
from PIL import Image

from .tests_tanda_0311 import _Catalogo, _cuerpo, _title

ESTATICOS = Path(__file__).parent / "static"
EN_TEMPORADA = datetime.date(2026, 11, 16)
FUERA_DE_TEMPORADA = datetime.date(2027, 3, 10)
# Medido en dulcecita.cl/corporativo/ el 16-11-2026, antes del cambio.
PALABRAS_ANTES = 438
FOTOS_DE_AZA = ("box-regalo-aza", "corporativo-empaques-aza")


def _palabras(trozo, solo_a_la_vista):
    trozo = re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<svg\b.*?</svg>", " ", trozo, flags=re.S)
    if solo_a_la_vista:
        # De un bloque plegado solo se ve su encabezado (<summary>) hasta que se abre.
        trozo = re.sub(r"<details\b[^>]*>(.*?)</details>",
                       lambda m: " ".join(re.findall(r"<summary\b.*?</summary>", m.group(1), flags=re.S)),
                       trozo, flags=re.S)
    return len(re.findall(r"\w+", html_lib.unescape(re.sub(r"<[^>]+>", " ", trozo))))


def _imagenes(trozo):
    return [dict(re.findall(r'([\w-]+)="([^"]*)"', etiqueta)) for etiqueta in re.findall(r"<img\b[^>]*>", trozo)]


def _tarjetas(cuerpo):
    return [t.split("</article>", 1)[0] for t in cuerpo.split('<article class="nav-card">')[1:]]


@override_settings(MINIMO_UNIDADES=10, DESPACHO_HORAS=48, BRAND_NAME="Dulcecita", SITE_URL="https://dulcecita.cl",
                   WHATSAPP_URL="https://wa.me/56900000000", CONTACT_EMAIL="ventas@dulcecitaa.cl",
                   DEFAULT_FROM_EMAIL="no-reply@dulcecitaa.cl",
                   EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CorporativoMenosTextoTests(_Catalogo):
    def _html(self, dia=EN_TEMPORADA):
        with mock.patch("BebesitaAPP.temporada.timezone.localdate", return_value=dia):
            respuesta = self.client.get("/corporativo/")
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    # -- menos texto --
    def test_a_la_vista_queda_menos_de_la_mitad_del_texto_de_antes(self):
        cuerpo = _cuerpo(self._html())
        a_la_vista, total = _palabras(cuerpo, True), _palabras(cuerpo, False)
        self.assertLess(a_la_vista, PALABRAS_ANTES // 2, a_la_vista)
        # Los plazos siguen en la pagina, plegados.
        self.assertGreater(total - a_la_vista, 25, (total, a_la_vista))

    def test_cada_cosa_que_se_ofrece_es_una_tarjeta_con_su_titulo_y_su_foto(self):
        tarjetas = _tarjetas(_cuerpo(self._html()))
        self.assertEqual(len(tarjetas), 4)
        titulos = ["Box de regalo", "Empaques con tu marca",
                   "Regalos de fin de año para tu equipo y tus clientes", "Eventos y pedidos por volumen"]
        for tarjeta, titulo in zip(tarjetas, titulos):
            self.assertEqual(tarjeta.count("<h2>"), 1)
            self.assertIn(f"<h2>{titulo}</h2>", tarjeta)
            self.assertEqual(len(_imagenes(tarjeta)), 1, titulo)

    def test_no_se_perdio_lo_que_la_pagina_ofrecia(self):
        cuerpo = _cuerpo(self._html())
        for dato in ("coffee breaks", "Mesas dulces", "despacho a todo Chile", "Tu logo, tus colores y un mensaje",
                     "al mismo precio por unidad del catálogo desde 20 unidades", "Emitimos boleta",
                     "menos de 24 horas hábiles", "<h2>Qué necesitamos para cotizar</h2>"):
            self.assertIn(dato, cuerpo, dato)

    def test_los_plazos_siguen_en_la_pagina_pero_plegados(self):
        cuerpo = _cuerpo(self._html())
        plegado = cuerpo.split('<details class="nav-mas corp-plazos">', 1)[1].split("</details>", 1)[0]
        self.assertIn("Un pedido normal sale 48 horas después del pago", plegado)
        self.assertIn("los pedidos grandes se cotizan con su propio plazo de producción", plegado)
        self.assertIn("Todo va envuelto por unidad", plegado)
        self.assertIn("Paket", plegado)
        self.assertNotIn("open", cuerpo.split('<details class="nav-mas corp-plazos"', 1)[1].split(">", 1)[0])

    def test_la_tarjeta_del_box_enlaza_solo_a_los_dulces_que_entran_en_un_box(self):
        box = _tarjetas(_cuerpo(self._html()))[0]
        for producto in (self.barquillos, self.alfajores, self.banados, self.rellenos):
            self.assertIn(f'href="{producto.get_absolute_url()}"', box, producto.nombre)
        # La torta no es un dulce de box: no se ofrece como contenido del box.
        self.assertNotIn(self.torta.get_absolute_url(), box)
        self.assertTrue(box.split('<p class="corp-dulces">', 1)[1].split("</p>", 1)[0].endswith("box surtido"))

    def test_title_h1_y_un_solo_h1_no_cambiaron(self):
        html = self._html()
        self.assertEqual(_title(html), "Dulces corporativos y regalos de fin de año | Dulcecita")
        self.assertEqual(re.findall(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S),
                         ["Dulces corporativos para tu empresa, con tu marca"])
        self.assertNotIn("{% comment", html)
        self.assertNotIn("{#", html)

    # -- los botones de la portada --
    def test_pedir_cotizacion_baja_al_formulario_y_whatsapp_lleva_el_mensaje(self):
        cuerpo = _cuerpo(self._html())
        portada = cuerpo.split("</section>", 1)[0]
        self.assertIn('<a href="#cotizar" class="btn-main">Pedir cotización</a>', portada)
        self.assertEqual(cuerpo.count('id="cotizar"'), 1)
        # El formulario esta DENTRO de la seccion a la que baja el boton.
        seccion = cuerpo.split('id="cotizar"', 1)[1]
        self.assertIn('<form method="post"', seccion)
        enlace = re.search(r'<a href="(https://wa\.me/56900000000\?[^"]+)"[^>]*>Escríbenos por WhatsApp</a>', portada)
        self.assertIsNotNone(enlace)
        self.assertIn("cotizar+dulces+corporativos", html_lib.unescape(enlace.group(1)))

    @override_settings(WHATSAPP_URL="")
    def test_sin_whatsapp_configurado_no_queda_un_boton_roto(self):
        cuerpo = _cuerpo(self._html())
        self.assertNotIn("Escríbenos por WhatsApp", cuerpo)
        self.assertNotIn('href=""', cuerpo)

    # -- fotos --
    def test_las_fotos_son_las_nuevas_de_tamara_y_no_las_de_aza(self):
        html = self._html()
        for vieja in FOTOS_DE_AZA:
            self.assertNotIn(vieja, html, vieja)
        self.assertNotIn("AZA", _cuerpo(html))
        nombres = [foto["src"].rsplit("/", 1)[1].split(".", 1)[0] for foto in _imagenes(_cuerpo(html))]
        self.assertEqual(nombres, [
            "regalos-de-navidad-dulcecita", "caja-con-ventana-sticker-dulcecita",
            "box-de-regalo-caja-con-ventana", "cuchuflis-con-sticker-personalizado",
            "box-navideno-bolsas-kraft", "regalos-en-fila-con-cinta"])
        self.assertEqual(len(set(nombres)), len(nombres))   # ninguna repetida

    def test_la_foto_de_portada_carga_primero_y_las_demas_esperan(self):
        for dia in (EN_TEMPORADA, FUERA_DE_TEMPORADA):
            portada, *demas = _imagenes(_cuerpo(self._html(dia)))
            self.assertEqual(portada.get("fetchpriority"), "high")
            self.assertNotIn("loading", portada)
            self.assertTrue(all(foto.get("loading") == "lazy" for foto in demas), demas)

    def test_fuera_de_temporada_la_portada_no_es_la_caja_navidena(self):
        fotos = _imagenes(_cuerpo(self._html(FUERA_DE_TEMPORADA)))
        self.assertIn("cajas-dulcecita-con-ventana", fotos[0]["src"])
        self.assertNotIn("regalos-de-navidad-dulcecita", " ".join(foto["src"] for foto in fotos))
        self.assertEqual(len({foto["src"] for foto in fotos}), len(fotos))

    def test_cada_foto_dice_que_muestra_existe_pesa_poco_y_mide_lo_declarado(self):
        vistos = set()
        for dia in (EN_TEMPORADA, FUERA_DE_TEMPORADA):
            for foto in _imagenes(_cuerpo(self._html(dia))):
                self.assertGreater(len(foto.get("alt", "")), 25, foto)
                archivo = ESTATICOS / foto["src"].split("/static/", 1)[1].split("?", 1)[0]
                self.assertTrue(archivo.is_file(), archivo)
                self.assertTrue(archivo.name.endswith(".webp"), archivo.name)
                self.assertLess(archivo.stat().st_size, 100 * 1024, archivo.name)
                with Image.open(archivo) as imagen:
                    self.assertEqual(imagen.size, (int(foto["width"]), int(foto["height"])), archivo.name)
                vistos.add(archivo.name)
        self.assertEqual(len(vistos), 7)

    # -- el aviso despues de enviar --
    DATOS = {"nombre": "Andrea", "empresa": "Acme", "email": "andrea@acme.cl",
             "telefono": "+56 9 9999 9999", "mensaje": "Necesito 100 cajas"}

    def test_el_formulario_envia_al_ancla_donde_esta_el_aviso(self):
        cuerpo = _cuerpo(self._html())
        self.assertIn('<form method="post" action="#cotizar"', cuerpo)
        self.assertNotIn("corp-avisos", cuerpo)   # sin aviso, no queda una caja vacia

    def test_el_aviso_de_enviado_queda_junto_al_formulario_y_una_sola_vez(self):
        respuesta = self.client.post("/corporativo/", data=self.DATOS, follow=True)
        self.assertEqual(len(mail.outbox), 1)
        cuerpo = _cuerpo(respuesta.content.decode())
        aviso = "Tu solicitud fue enviada. Te contactaremos pronto."
        self.assertEqual(cuerpo.count(aviso), 1)
        seccion = cuerpo.split('id="cotizar"', 1)[1]
        self.assertIn(aviso, seccion)
        self.assertLess(seccion.index(aviso), seccion.index('<form method="post"'))

    def test_un_formulario_incompleto_avisa_junto_al_formulario(self):
        respuesta = self.client.post("/corporativo/", data={**self.DATOS, "email": ""})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        seccion = _cuerpo(respuesta.content.decode()).split('id="cotizar"', 1)[1]
        self.assertIn("Revisa los datos del formulario.", seccion)
        self.assertIn('class="field-error"', seccion)
