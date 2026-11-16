"""Minimo de $10.000 por box (11-11-2026, Tamara por WhatsApp: "el box desde 10mil
hacia arriba, no me conviene que me pidan 3 barquillos en una caja").

Se compara el TOTAL del box (dulces con la promocion vigente + empaque), el mismo
numero que cobra el carrito. Se revisa al armarlo, se avisa en el carrito si al
bajar de a uno queda bajo el minimo, y el checkout no lo cobra asi.
"""
import datetime

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Opcion, Pedido, Producto, Promocion


@override_settings(MINIMO_UNIDADES=10, MINIMO_BOX=3, BOX_PRICE=1500, SHIPPING_COST=0,
                   BOX_MINIMO_TOTAL=9500,
                   EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class BoxMinimoTests(TestCase):
    def setUp(self):
        self.choc = Opcion.objects.create(nombre="Chocolate", color="#5b3a29", orden=1)
        self.alfajor = Producto.objects.create(
            nombre="Alfajores", descripcion="x", precio=2000, en_box=True,
            imagen=SimpleUploadedFile("a.jpg", b"img", content_type="image/jpeg"))
        self.alfajor.opciones.add(self.choc)
        self.linea = f"{self.alfajor.id}-{self.choc.id}"

    def _armar(self, cantidad):
        return self.client.post(reverse("arma_tu_box"), data={f"q-{self.linea}": cantidad})

    def test_bajo_el_minimo_no_entra_al_carrito_y_dice_cuanto_falta(self):
        # 3 x 2.000 + empaque 1.500 = 7.500: faltan 2.000.
        r = self._armar(3)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.session.get("boxes", []), [])
        self.assertContains(r, "El box parte en $9.500: te faltan $2.000.")

    def test_justo_en_el_minimo_entra(self):
        # 4 x 2.000 + 1.500 = 9.500.
        r = self._armar(4)
        self.assertRedirects(r, reverse("carrito"))
        self.assertEqual(self.client.session["boxes"], [{self.linea: 4}])

    def test_bajar_de_a_uno_en_el_carrito_avisa_y_el_checkout_no_lo_cobra(self):
        self._armar(4)
        r = self.client.post(reverse("box_restar_ajax", args=[0, self.linea])).json()
        self.assertEqual(r["qty"], 3)
        self.assertEqual(r["box_falta"], 2000)
        carrito = self.client.get(reverse("carrito")).content.decode()
        aviso = carrito.split('data-box-falta="0"', 1)[1].split("</p>", 1)[0]
        self.assertNotIn("hidden", aviso.split(">", 1)[0])
        self.assertIn("te faltan <b data-box-falta-monto>$2.000</b>", aviso)

        r = self.client.get(reverse("checkout"))
        self.assertRedirects(r, reverse("carrito"), fetch_redirect_response=False)
        r = self.client.post(reverse("checkout"), data={
            "nombre": "Cliente", "email": "c@example.com", "telefono": "+56 9 1111 1111",
            "tipo_entrega": "retiro", "comuna_sector": "Santiago", "direccion": "Ref",
        })
        self.assertRedirects(r, reverse("carrito"), fetch_redirect_response=False)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_volver_a_subir_quita_el_aviso_y_deja_pagar(self):
        self._armar(4)
        self.client.post(reverse("box_restar_ajax", args=[0, self.linea]))
        r = self.client.post(reverse("box_sumar_ajax", args=[0, self.linea])).json()
        self.assertEqual(r["box_falta"], 0)
        carrito = self.client.get(reverse("carrito")).content.decode()
        self.assertIn('data-box-falta="0" hidden', carrito)
        r = self.client.post(reverse("checkout"), data={
            "nombre": "Cliente", "email": "c@example.com", "telefono": "+56 9 1111 1111",
            "tipo_entrega": "retiro", "comuna_sector": "Santiago", "direccion": "Ref",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Pedido.objects.get().total, 9500)

    def test_con_promocion_cuenta_el_precio_rebajado(self):
        hoy = timezone.localdate()
        Promocion.objects.create(nombre="Navidad", porcentaje=10, desde=hoy,
                                 hasta=hoy + datetime.timedelta(days=3), etiqueta="Navidad")
        # 4 x 1.800 + 1.500 = 8.700 (bajo 9.500); 5 x 1.800 + 1.500 = 10.500.
        self._armar(4)
        self.assertEqual(self.client.session.get("boxes", []), [])
        self._armar(5)
        self.assertEqual(self.client.session["boxes"], [{self.linea: 5}])

    def test_la_pantalla_lo_dice_y_el_boton_lo_sabe(self):
        html = self.client.get(reverse("arma_tu_box")).content.decode()
        self.assertIn("El box parte en $9.500, con el empaque incluido.", html)
        self.assertIn('data-minimo-total="9500"', html)
        self.assertIn("data-box-falta hidden", html)

    def test_navidad_dice_desde_cuanto_parte_el_box(self):
        html = self.client.get("/navidad/").content.decode()
        self.assertIn("El box parte en $9.500, con el empaque incluido.", html)
        self.assertIn("Un box parte en $9.500, con el empaque incluido.", html)

    @override_settings(BOX_MINIMO_TOTAL=0)
    def test_sin_minimo_vuelve_a_lo_de_antes(self):
        r = self._armar(3)
        self.assertRedirects(r, reverse("carrito"))
        carrito = self.client.get(reverse("carrito")).content.decode()
        self.assertNotIn("data-box-falta", carrito)
        pagina = self.client.get(reverse("arma_tu_box")).content.decode()
        self.assertNotIn("con el empaque incluido", pagina)
        self.assertIn('data-minimo-total="0"', pagina)


class MinimoPorDefectoTests(TestCase):
    def test_el_minimo_por_defecto_es_10000(self):
        from django.conf import settings
        self.assertEqual(settings.BOX_MINIMO_TOTAL, 10000)
