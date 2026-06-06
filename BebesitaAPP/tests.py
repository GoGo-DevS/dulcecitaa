from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CategoriaProducto, Pedido, Producto


class CarritoFlowTests(TestCase):
    def setUp(self):
        self.producto = Producto.objects.create(
            nombre="Caja premium",
            descripcion="Caja de prueba",
            precio=10000,
            imagen=SimpleUploadedFile("test.jpg", b"fake-image-content", content_type="image/jpeg"),
        )

    def _set_cart(self, data):
        session = self.client.session
        session["cart"] = data
        session.save()

    def test_agregar_al_carrito_incrementa_cantidad(self):
        self.client.get(reverse("agregar_al_carrito", args=[self.producto.id]))
        session = self.client.session
        self.assertEqual(session.get("cart", {}).get(str(self.producto.id)), 1)

    def test_decrementar_carrito_ajax_modifica_cantidad(self):
        self._set_cart({str(self.producto.id): 2})

        response = self.client.post(reverse("decrementar_carrito_ajax", args=[self.producto.id]))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["qty"], 1)
        self.assertEqual(payload["cart_count"], 1)

    def test_eliminar_carrito_ajax_quita_producto_y_total(self):
        self._set_cart({str(self.producto.id): 2})

        response = self.client.post(reverse("eliminar_carrito_ajax", args=[self.producto.id]))
        payload = response.json()
        session = self.client.session

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["qty"], 0)
        self.assertEqual(payload["total"], 0.0)
        self.assertNotIn(str(self.producto.id), session.get("cart", {}))

    def test_agregar_carrito_ajax_producto_inexistente_responde_404(self):
        response = self.client.post(reverse("agregar_carrito_ajax", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_agregar_al_carrito_producto_no_disponible_no_agrega(self):
        self.producto.disponible = False
        self.producto.save()

        response = self.client.get(reverse("agregar_al_carrito", args=[self.producto.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("productos"))
        self.assertNotIn(str(self.producto.id), self.client.session.get("cart", {}))


class CatalogoFiltroTests(TestCase):
    def setUp(self):
        self.cat_brownie = CategoriaProducto.objects.create(nombre="Brownies", slug="brownies", orden=1)
        self.cat_torta = CategoriaProducto.objects.create(nombre="Tortas", slug="tortas", orden=2)
        self.p1 = Producto.objects.create(
            nombre="Brownie Clásico",
            descripcion="Chocolate",
            precio=5000,
            categoria=self.cat_brownie,
            destacado=True,
            imagen=SimpleUploadedFile("p1.jpg", b"fake", content_type="image/jpeg"),
        )
        self.p2 = Producto.objects.create(
            nombre="Torta Frambuesa",
            descripcion="Frambuesa",
            precio=12000,
            categoria=self.cat_torta,
            destacado=False,
            imagen=SimpleUploadedFile("p2.jpg", b"fake", content_type="image/jpeg"),
        )

    def test_filtro_por_busqueda_y_categoria(self):
        response = self.client.get(reverse("productos"), {"q": "Brownie", "categoria": "brownies"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.p1.nombre)
        self.assertNotContains(response, self.p2.nombre)

    def test_filtro_solo_destacados(self):
        response = self.client.get(reverse("productos"), {"destacados": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.p1.nombre)
        self.assertNotContains(response, self.p2.nombre)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CONTACT_EMAIL="ventas@dulcecitaa.cl",
    DEFAULT_FROM_EMAIL="no-reply@dulcecitaa.cl",
    SHIPPING_COST=2500,
)
class FormulariosYCheckoutTests(TestCase):
    def setUp(self):
        self.producto = Producto.objects.create(
            nombre="Brownie",
            descripcion="Brownie de prueba",
            precio=5000,
            imagen=SimpleUploadedFile("test2.jpg", b"fake-image-content", content_type="image/jpeg"),
        )

    def test_contacto_post_envia_y_redirige(self):
        response = self.client.post(
            reverse("contacto"),
            data={
                "nombre": "Diego",
                "email": "diego@example.com",
                "mensaje": "Quiero mas informacion",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("contacto"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Contacto Web", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["ventas@dulcecitaa.cl"])
        self.assertTrue(any(content_type == "text/html" for _, content_type in mail.outbox[0].alternatives))

    def test_contacto_post_invalido_muestra_error(self):
        response = self.client.post(
            reverse("contacto"),
            data={"nombre": "", "email": "correo-invalido", "mensaje": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Corrige los campos marcados")

    def test_corporativo_post_envia_y_redirige(self):
        response = self.client.post(
            reverse("corporativo"),
            data={
                "nombre": "Andrea",
                "empresa": "Acme",
                "email": "andrea@acme.cl",
                "telefono": "+56 9 9999 9999",
                "mensaje": "Necesito 100 cajas",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("corporativo"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Solicitud Corporativa", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["ventas@dulcecitaa.cl"])
        self.assertTrue(any(content_type == "text/html" for _, content_type in mail.outbox[0].alternatives))

    def test_checkout_post_valido_crea_pedido_y_limpia_carrito(self):
        session = self.client.session
        session["cart"] = {str(self.producto.id): 2}
        session.save()

        response = self.client.post(
            reverse("checkout"),
            data={
                "nombre": "Cliente Test",
                "email": "cliente@example.com",
                "telefono": "+56 9 1111 1111",
                "tipo_entrega": "despacho",
                "comuna_sector": "Providencia",
                "direccion": "Calle Falsa 123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Pedido.objects.count(), 1)

        pedido = Pedido.objects.first()
        self.assertEqual(response.url, reverse("checkout_exito", args=[pedido.id]))
        self.assertEqual(pedido.tipo_entrega, "despacho")
        self.assertEqual(str(pedido.costo_despacho), "2500.00")
        self.assertEqual(str(pedido.total), "12500.00")

        session = self.client.session
        self.assertEqual(session.get("cart"), {})
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ["cliente@example.com"])
        self.assertEqual(mail.outbox[1].to, ["ventas@dulcecitaa.cl"])
        self.assertTrue(any(content_type == "text/html" for _, content_type in mail.outbox[0].alternatives))
        self.assertTrue(any(content_type == "text/html" for _, content_type in mail.outbox[1].alternatives))

    def test_checkout_post_invalido_no_crea_pedido(self):
        session = self.client.session
        session["cart"] = {str(self.producto.id): 1}
        session.save()

        response = self.client.post(
            reverse("checkout"),
            data={
                "nombre": "",
                "email": "mal-correo",
                "telefono": "abc",
                "tipo_entrega": "despacho",
                "comuna_sector": "",
                "direccion": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revisa los campos del formulario")
        self.assertEqual(Pedido.objects.count(), 0)

    @patch("BebesitaAPP.views.send_contact_email", return_value=False)
    def test_contacto_error_envio_muestra_feedback(self, _mock_send):
        response = self.client.post(
            reverse("contacto"),
            data={
                "nombre": "Diego",
                "email": "diego@example.com",
                "mensaje": "Consulta de prueba",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No pudimos enviar tu mensaje ahora")

    @patch("BebesitaAPP.views.send_corporate_email", return_value=False)
    def test_corporativo_error_envio_muestra_feedback(self, _mock_send):
        response = self.client.post(
            reverse("corporativo"),
            data={
                "nombre": "Andrea",
                "empresa": "Acme",
                "email": "andrea@acme.cl",
                "telefono": "+56 9 9999 9999",
                "mensaje": "Necesito propuesta",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No pudimos enviar tu solicitud ahora")

    @patch("BebesitaAPP.views.send_checkout_emails", return_value={"customer_ok": False, "internal_ok": False})
    def test_checkout_si_falla_correo_igual_crea_pedido_y_avisa(self, _mock_send):
        session = self.client.session
        session["cart"] = {str(self.producto.id): 1}
        session.save()

        response = self.client.post(
            reverse("checkout"),
            data={
                "nombre": "Cliente Test",
                "email": "cliente@example.com",
                "telefono": "+56 9 1111 1111",
                "tipo_entrega": "retiro",
                "comuna_sector": "Santiago Centro",
                "direccion": "Calle Falsa 123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertContains(response, "hubo un problema al enviar correos")

    @patch("BebesitaAPP.views.send_checkout_emails", return_value={"customer_ok": True, "internal_ok": True})
    @override_settings(WHATSAPP_URL="https://wa.me/56912345678")
    def test_checkout_exito_muestra_link_whatsapp_con_pedido(self, _mock_send):
        session = self.client.session
        session["cart"] = {str(self.producto.id): 1}
        session.save()

        response = self.client.post(
            reverse("checkout"),
            data={
                "nombre": "Cliente Test",
                "email": "cliente@example.com",
                "telefono": "+56 9 1111 1111",
                "tipo_entrega": "retiro",
                "comuna_sector": "Nunoa",
                "direccion": "Referencia local 12",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "wa.me")
        self.assertContains(response, "%231")
