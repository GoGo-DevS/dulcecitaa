from django.test import TestCase

# Create your tests here.


class PanelWebTests(TestCase):
    """La pantalla Web del panel resume la tienda y solo la ve quien entra."""

    def test_requiere_login_y_muestra_ventas_y_clics(self):
        from django.contrib.auth import get_user_model
        from BebesitaAPP.models import ClicEnlace, Pedido as PedidoWeb

        self.assertEqual(self.client.get("/panel/web/").status_code, 302)
        User = get_user_model()
        self.client.force_login(User.objects.create_user("duena", "d@example.com", "clave-larga-123"))
        PedidoWeb.objects.create(nombre_cliente="Ana", email_cliente="a@example.com", telefono="+56911111111",
                                 direccion="x", total=15900, cantidad_cajas=1)
        ClicEnlace.objects.create(slug="whatsapp")
        r = self.client.get("/panel/web/?dias=30")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Tienda web")
        self.assertRegex(r.content.decode(), r"15\D{1,6}900")
        self.assertContains(r, "WhatsApp")
        self.assertContains(r, "Herramientas de medición")
