from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import CategoriaProducto, Opcion, Pedido, PedidoItem, Producto


@override_settings(MINIMO_UNIDADES=10)
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
        # Entra con el minimo puesto, no de a uno.
        self.assertEqual(session.get("cart", {}).get(str(self.producto.id)), 10)

    def test_decrementar_carrito_ajax_modifica_cantidad(self):
        self._set_cart({str(self.producto.id): 11})

        response = self.client.post(reverse("decrementar_carrito_ajax", args=[self.producto.id]))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["qty"], 10)
        self.assertEqual(payload["cart_count"], 10)

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

    def test_productos_entrega_cookie_csrf_para_ajax_carrito(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse("productos"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value
        response = client.post(
            reverse("agregar_carrito_ajax", args=[self.producto.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])


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
    BOX_PRICE=0,
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
                "cantidad_cajas": 1,
                "comentario_ocasion": "Cumpleaños",
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
                "cantidad_cajas": 1,
                "comentario_ocasion": "Cumpleaños",
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
                "cantidad_cajas": 1,
                "comentario_ocasion": "Cumpleaños",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "wa.me")
        self.assertContains(response, "%231")


@override_settings(
    MINIMO_UNIDADES=10,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CONTACT_EMAIL="ventas@dulcecitaa.cl",
    BOX_PRICE=0,
    SHIPPING_COST=0,
)
class CoberturasTests(TestCase):
    """La cobertura se elige en la tarjeta y viaja hasta el pedido."""

    def setUp(self):
        self.chocolate = Opcion.objects.create(nombre="Chocolate", color="#5b3a29", orden=1)
        self.blanco = Opcion.objects.create(nombre="Chocolate blanco", color="#f3ead9", orden=2)
        self.alfajor = Producto.objects.create(
            nombre="Alfajores", descripcion="x", precio=2000,
            imagen=SimpleUploadedFile("a.jpg", b"img", content_type="image/jpeg"),
        )
        self.alfajor.opciones.add(self.chocolate, self.blanco)
        self.otro = Producto.objects.create(
            nombre="Otro", descripcion="x", precio=1000,
            imagen=SimpleUploadedFile("b.jpg", b"img", content_type="image/jpeg"),
        )

    def _agregar(self, linea):
        return self.client.post(reverse("agregar_carrito_ajax", args=[linea]))

    def test_cada_cobertura_es_una_linea_propia(self):
        self._agregar(f"{self.alfajor.id}-{self.chocolate.id}")
        self._agregar(f"{self.alfajor.id}-{self.blanco.id}")
        cart = self.client.session["cart"]
        self.assertEqual(cart, {
            f"{self.alfajor.id}-{self.chocolate.id}": 10,
            f"{self.alfajor.id}-{self.blanco.id}": 10,
        })

    def test_sin_elegir_toma_la_primera_cobertura(self):
        # El enlace "Agregar y ver carrito" y los carritos viejos no mandan cobertura.
        payload = self._agregar(str(self.alfajor.id)).json()
        self.assertEqual(payload["linea"], f"{self.alfajor.id}-{self.chocolate.id}")

    def test_cobertura_que_el_producto_no_ofrece_se_rechaza(self):
        response = self._agregar(f"{self.otro.id}-{self.blanco.id}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_dos_coberturas_en_la_misma_linea_se_rechaza(self):
        response = self._agregar(f"{self.alfajor.id}-{self.chocolate.id}-{self.blanco.id}")
        self.assertEqual(response.status_code, 404)

    def test_clave_basura_no_revienta(self):
        self.assertEqual(self._agregar("abc").status_code, 404)
        self.assertEqual(self.client.post(reverse("eliminar_carrito_ajax", args=["x-1"])).status_code, 200)

    def test_el_recargo_se_suma_al_precio(self):
        self.blanco.recargo = 300
        self.blanco.save()
        payload = self._agregar(f"{self.alfajor.id}-{self.blanco.id}").json()
        self.assertEqual(payload["total"], 23000.0)

    def test_el_pedido_guarda_la_cobertura_y_el_correo_la_dice(self):
        self._agregar(f"{self.alfajor.id}-{self.blanco.id}")
        response = self.client.post(reverse("checkout"), data={
            "nombre": "Cliente", "email": "c@example.com", "telefono": "+56 9 1111 1111",
            "tipo_entrega": "retiro", "comuna_sector": "Santiago", "direccion": "Ref",
            "cantidad_cajas": 1, "comentario_ocasion": "Regalo",
        })
        self.assertEqual(response.status_code, 302)
        item = PedidoItem.objects.get()
        self.assertEqual(item.detalle, "Cobertura: Chocolate blanco")
        self.assertIn("Chocolate blanco", mail.outbox[-1].alternatives[0][0])

    def test_catalogo_muestra_muestras_y_no_duplica_variantes(self):
        variante = Producto.objects.create(
            nombre="Alfajores", descripcion="x", precio=2000, variante_de=self.alfajor, visible=False,
            imagen=SimpleUploadedFile("c.jpg", b"img", content_type="image/jpeg"),
        )
        response = self.client.get(reverse("productos"))
        self.assertContains(response, 'data-opciones', count=1)
        self.assertContains(response, f'data-id="{self.alfajor.id}-{self.chocolate.id}"')
        self.assertNotContains(response, f'data-pid="{variante.id}"')


class CatalogoInicialTests(TestCase):
    """El deploy deja en produccion el catalogo nuevo sin pisar ediciones."""

    def setUp(self):
        import tempfile
        self._media = tempfile.mkdtemp()
        self._override = override_settings(MEDIA_ROOT=self._media)
        self._override.enable()
        self.viejo = Producto.objects.create(
            nombre="Brownie chocolate", descripcion="x", precio=3000, visible=True, destacado=True,
            imagen=SimpleUploadedFile("brownie.jpg", b"img", content_type="image/jpeg"),
        )

    def tearDown(self):
        import shutil
        self._override.disable()
        shutil.rmtree(self._media, ignore_errors=True)

    def _correr(self):
        from django.core.management import call_command
        call_command("catalogo_inicial", stdout=__import__("io").StringIO())

    def test_carga_los_tres_con_coberturas_y_oculta_el_viejo(self):
        self._correr()
        visibles = Producto.objects.filter(visible=True)
        self.assertEqual(visibles.count(), 3)
        for p in visibles:
            self.assertEqual([o.nombre for o in p.opciones.all()], ["Chocolate", "Chocolate blanco"])
            self.assertTrue(p.imagen.storage.exists(p.imagen.name))
        self.viejo.refresh_from_db()
        self.assertFalse(self.viejo.visible)

    def test_segunda_corrida_no_pisa_lo_editado_en_el_admin(self):
        self._correr()
        alfajor = Producto.objects.get(nombre="Alfajores")
        alfajor.precio = 2200
        alfajor.save()
        self.viejo.visible = True
        self.viejo.save()
        self._correr()
        self.assertEqual(Producto.objects.get(nombre="Alfajores").precio, 2200)
        self.assertEqual(Producto.objects.filter(nombre="Alfajores").count(), 1)
        self.viejo.refresh_from_db()
        self.assertTrue(self.viejo.visible)

    def test_repone_la_foto_si_el_disco_se_borro(self):
        self._correr()
        alfajor = Producto.objects.get(nombre="Alfajores")
        alfajor.imagen.storage.delete(alfajor.imagen.name)
        self._correr()
        alfajor.refresh_from_db()
        self.assertTrue(alfajor.imagen.storage.exists(alfajor.imagen.name))


@override_settings(MINIMO_UNIDADES=10, BOX_PRICE=1500, SHIPPING_COST=0,
                   EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PedidoSinCajaTests(TestCase):
    """El pedido normal va en bolsa: la caja no se cobra (se cobra en Arma tu box)."""

    def test_checkout_normal_no_cobra_caja_ni_pide_ocasion(self):
        producto = Producto.objects.create(
            nombre="Barquillos", descripcion="x", precio=1500,
            imagen=SimpleUploadedFile("b.jpg", b"img", content_type="image/jpeg"),
        )
        self.client.post(reverse("agregar_carrito_ajax", args=[producto.id]))
        pagina = self.client.get(reverse("checkout"))
        self.assertNotContains(pagina, "cantidad_cajas")
        response = self.client.post(reverse("checkout"), data={
            "nombre": "Cliente", "email": "c@example.com", "telefono": "+56 9 1111 1111",
            "tipo_entrega": "retiro", "comuna_sector": "Santiago", "direccion": "Ref",
        })
        self.assertEqual(response.status_code, 302)
        pedido = Pedido.objects.get()
        self.assertEqual((pedido.cantidad_cajas, pedido.costo_caja, pedido.total), (0, 0, 15000))
        self.assertNotIn("Cajas (", mail.outbox[0].body)
