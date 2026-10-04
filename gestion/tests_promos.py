"""La seccion de promociones del panel.

Tamara la maneja desde el celular, asi que lo que se prueba aca es el flujo
completo por la UI (crear, editar, apagar, borrar) y que el precio que ve la
clienta en la web cambie de verdad. Ver tambien BebesitaAPP/tests_promocion.py,
que cubre el motor del descuento.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from BebesitaAPP.models import Producto, Promocion


class PanelPromosTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.duena = User.objects.create_user("duena2", "d2@example.com", "clave-larga-123")
        self.prod = Producto.objects.create(
            nombre="Caja sorpresa", descripcion="x", precio=12900, stock=5,
            imagen="productos/x.jpg")

    def _promo(self, **kw):
        hoy = timezone.localdate()
        datos = dict(nombre="Dia del Profesor", porcentaje=10, desde=hoy,
                     hasta=hoy + timedelta(days=12), etiqueta="Dia del Profesor")
        datos.update(kw)
        return Promocion.objects.create(**datos)

    # --- lo que protege el middleware ---

    def test_las_cinco_rutas_piden_login(self):
        promo = self._promo()
        rutas = [("get", "/panel/promos/"),
                 ("get", "/panel/promos/nueva/"),
                 ("get", "/panel/promos/%d/editar/" % promo.pk),
                 ("post", "/panel/promos/%d/encender/" % promo.pk),
                 ("post", "/panel/promos/%d/eliminar/" % promo.pk)]
        for metodo, url in rutas:
            r = getattr(self.client, metodo)(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertNotIn("Dia del Profesor", r.content.decode(), url)
        # y nada se toco de paso
        self.assertTrue(Promocion.objects.get(pk=promo.pk).activa)

    # --- la pregunta que la pantalla tiene que responder ---

    def test_la_lista_dice_si_hay_descuento_corriendo_y_en_pesos(self):
        self._promo()
        self.client.force_login(self.duena)
        html = self.client.get("/panel/promos/").content.decode()
        self.assertIn("Dia del Profesor", html)
        self.assertIn("10%", html)
        # El efecto en pesos sobre un producto de verdad: 12.900 -> 11.610.
        # Un "10%" no dice nada; el precio final si.
        self.assertRegex(html, r"11\D{1,6}610")

    def test_sin_promo_vigente_la_lista_lo_dice(self):
        hoy = timezone.localdate()
        self._promo(desde=hoy - timedelta(days=20), hasta=hoy - timedelta(days=10))
        self.client.force_login(self.duena)
        html = self.client.get("/panel/promos/").content.decode()
        self.assertIn("precios normales", html)
        self.assertIn("Terminada", html)

    def test_la_programada_dice_cuando_empieza_y_todavia_no_descuenta(self):
        hoy = timezone.localdate()
        self._promo(desde=hoy + timedelta(days=3), hasta=hoy + timedelta(days=9))
        self.client.force_login(self.duena)
        html = self.client.get("/panel/promos/").content.decode()
        self.assertIn("Empieza en 3 d", html)
        self.assertEqual(self.prod.precio_para([]), 12900)

    def test_el_ultimo_dia_se_avisa_como_tal(self):
        self._promo(hasta=timezone.localdate())
        self.client.force_login(self.duena)
        self.assertContains(self.client.get("/panel/promos/"), "ltimo d")

    # --- crear y editar por el formulario ---

    def test_crear_por_el_formulario_descuenta_en_la_web(self):
        hoy = timezone.localdate()
        self.client.force_login(self.duena)
        r = self.client.post("/panel/promos/nueva/", {
            "nombre": "Halloween", "porcentaje": "15",
            "desde": hoy.isoformat(), "hasta": (hoy + timedelta(days=5)).isoformat(),
            "etiqueta": "Halloween", "mensaje": "", "activa": "on"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Promocion.objects.count(), 1)
        self.assertEqual(self.prod.precio_para([]), 10965)   # 12.900 - 15%

    def test_el_formulario_rechaza_hasta_antes_de_desde(self):
        hoy = timezone.localdate()
        self.client.force_login(self.duena)
        r = self.client.post("/panel/promos/nueva/", {
            "nombre": "Al reves", "porcentaje": "10",
            "desde": hoy.isoformat(), "hasta": (hoy - timedelta(days=1)).isoformat(),
            "etiqueta": "x", "mensaje": "", "activa": "on"})
        self.assertEqual(r.status_code, 200)   # vuelve al formulario
        self.assertEqual(Promocion.objects.count(), 0)
        # Y el error sale BAJO el campo "hasta", no suelto arriba: si no, no se
        # sabe cual de las dos fechas hay que corregir. La regla vive en
        # Promocion.clean() y el ModelForm la corre sola.
        self.assertIn("hasta", r.context["form"].errors)

    def test_avisa_cuando_dos_campanas_se_cruzan_de_fecha(self):
        hoy = timezone.localdate()
        self._promo()                      # hoy -> hoy+12
        self.client.force_login(self.duena)
        r = self.client.post("/panel/promos/nueva/", {
            "nombre": "Halloween", "porcentaje": "15",
            "desde": (hoy + timedelta(days=5)).isoformat(),
            "hasta": (hoy + timedelta(days=20)).isoformat(),
            "etiqueta": "Halloween", "mensaje": "", "activa": "on"}, follow=True)
        avisos = [m.message for m in r.context["messages"]]
        self.assertTrue(any("se cruza de fecha" in a for a in avisos), avisos)

    def test_editar_el_porcentaje_cambia_el_precio_de_la_web(self):
        promo = self._promo()
        self.client.force_login(self.duena)
        self.client.post("/panel/promos/%d/editar/" % promo.pk, {
            "nombre": promo.nombre, "porcentaje": "20",
            "desde": promo.desde.isoformat(), "hasta": promo.hasta.isoformat(),
            "etiqueta": promo.etiqueta, "mensaje": "", "activa": "on"})
        self.assertEqual(self.prod.precio_para([]), 10320)   # 12.900 - 20%

    # --- apagar es lo que mas se usa ---

    def test_apagar_devuelve_el_precio_normal_y_encender_lo_trae_de_vuelta(self):
        promo = self._promo()
        self.assertEqual(self.prod.precio_para([]), 11610)
        self.client.force_login(self.duena)
        self.client.post("/panel/promos/%d/encender/" % promo.pk)
        self.assertFalse(Promocion.objects.get(pk=promo.pk).activa)
        self.assertEqual(self.prod.precio_para([]), 12900)
        self.client.post("/panel/promos/%d/encender/" % promo.pk)
        self.assertEqual(self.prod.precio_para([]), 11610)

    def test_apagar_y_eliminar_no_se_hacen_por_GET(self):
        promo = self._promo()
        self.client.force_login(self.duena)
        self.assertEqual(self.client.get("/panel/promos/%d/encender/" % promo.pk).status_code, 405)
        self.assertEqual(self.client.get("/panel/promos/%d/eliminar/" % promo.pk).status_code, 405)
        self.assertTrue(Promocion.objects.filter(pk=promo.pk).exists())
        self.assertTrue(Promocion.objects.get(pk=promo.pk).activa)

    def test_eliminar_borra_y_la_web_vuelve_al_precio_normal(self):
        promo = self._promo()
        self.client.force_login(self.duena)
        self.client.post("/panel/promos/%d/eliminar/" % promo.pk)
        self.assertEqual(Promocion.objects.count(), 0)
        self.assertEqual(self.prod.precio_para([]), 12900)

    # --- la pantalla sirve aunque no haya nada cargado ---

    def test_sin_productos_la_pantalla_no_revienta(self):
        Producto.objects.all().delete()
        self._promo()
        self.client.force_login(self.duena)
        self.assertEqual(self.client.get("/panel/promos/").status_code, 200)
        self.assertEqual(self.client.get("/panel/promos/nueva/").status_code, 200)

    def test_sin_ninguna_campana_la_pantalla_invita_a_crear_una(self):
        self.client.force_login(self.duena)
        r = self.client.get("/panel/promos/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "/panel/promos/nueva/")

    # --- el menu lleva a la pantalla ---

    def test_el_menu_del_panel_tiene_la_entrada(self):
        self.client.force_login(self.duena)
        for url in ("/panel/", "/panel/promos/"):
            self.assertContains(self.client.get(url), "/panel/promos/")

    def test_a_una_campana_terminada_no_se_le_ofrece_apagar(self):
        hoy = timezone.localdate()
        promo = self._promo(desde=hoy - timedelta(days=20), hasta=hoy - timedelta(days=10))
        self.client.force_login(self.duena)
        html = self.client.get("/panel/promos/").content.decode()
        # No hay boton de apagado para ella (no descuenta nada: no haria nada)
        self.assertNotIn('action="/panel/promos/%d/encender/"' % promo.pk, html)
        # Pero si se puede volver a usar cambiandole las fechas
        self.assertIn("Reusar", html)
        self.assertIn("/panel/promos/%d/editar/" % promo.pk, html)

    def test_la_que_corre_si_tiene_apagar(self):
        promo = self._promo()
        self.client.force_login(self.duena)
        html = self.client.get("/panel/promos/").content.decode()
        self.assertIn('action="/panel/promos/%d/encender/"' % promo.pk, html)
        self.assertIn("Apagar", html)
