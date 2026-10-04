"""Pruebas de la promocion por fecha.

Lo que se prueba no es "el descuento funciona" sino lo que cuesta plata si
falla: que una promocion VENCIDA deje de cobrarse barata, que una FUTURA no se
cobre antes, y que el precio que se cobra sea el mismo que se mostro.
"""
import datetime as dt

from django.test import TestCase
from django.utils import timezone

from BebesitaAPP.models import Opcion, Producto, Promocion


class PromocionVigencia(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.p = Producto.objects.create(nombre="Alfajores", descripcion="x", precio=1000)

    def _promo(self, dias_desde, dias_hasta, pct=10, activa=True):
        return Promocion.objects.create(
            nombre="prueba", porcentaje=pct, etiqueta="Dia del Profesor", activa=activa,
            desde=self.hoy + dt.timedelta(days=dias_desde),
            hasta=self.hoy + dt.timedelta(days=dias_hasta))

    def test_vigente_hoy_descuenta(self):
        self._promo(-1, 1)
        self.assertEqual(self.p.precio_para([]), 900)

    def test_el_ultimo_dia_todavia_aplica(self):
        self._promo(-5, 0)          # termina HOY
        self.assertEqual(self.p.precio_para([]), 900)

    def test_el_primer_dia_ya_aplica(self):
        self._promo(0, 5)           # empieza HOY
        self.assertEqual(self.p.precio_para([]), 900)

    def test_vencida_NO_descuenta(self):
        """Lo que le paso a medina: la oferta vencida se seguia cobrando."""
        self._promo(-10, -1)
        self.assertEqual(self.p.precio_para([]), 1000)

    def test_futura_NO_descuenta(self):
        self._promo(5, 10)
        self.assertEqual(self.p.precio_para([]), 1000)

    def test_desactivada_NO_descuenta(self):
        self._promo(-1, 1, activa=False)
        self.assertEqual(self.p.precio_para([]), 1000)

    def test_sin_promociones_el_precio_es_el_de_lista(self):
        self.assertEqual(self.p.precio_para([]), 1000)
        self.assertFalse(self.p.tiene_descuento)

    def test_si_hay_dos_encimadas_gana_la_de_MAYOR_descuento(self):
        """Equivocarse a favor del cliente es barato; cobrarle mas, no."""
        self._promo(-1, 1, pct=10)
        self._promo(-1, 1, pct=25)
        self.assertEqual(self.p.precio_para([]), 750)

    def test_el_precio_de_lista_nunca_cambia(self):
        self._promo(-1, 1)
        self.assertEqual(self.p.precio_lista_para([]), 1000)
        self.assertEqual(self.p.precio_para([]), 900)
        self.assertTrue(self.p.tiene_descuento)

    def test_descuenta_tambien_sobre_el_recargo_de_una_opcion(self):
        op = Opcion.objects.create(nombre="Chocolate", tipo="cobertura", recargo=200)
        self.p.opciones.add(op)
        self._promo(-1, 1)
        # 1000 + 200 = 1200, menos 10% = 1080
        self.assertEqual(self.p.precio_para([op.id]), 1080)

    def test_redondea_a_peso(self):
        self.p.precio = 1595
        self.p.save()
        self._promo(-1, 1, pct=10)
        self.assertEqual(self.p.precio_para([]), 1436)   # 1435,5 -> 1436
        self.assertIsInstance(self.p.precio_para([]), int)

    def test_hasta_antes_de_desde_no_se_puede_guardar(self):
        from django.core.exceptions import ValidationError
        pr = Promocion(nombre="mala", porcentaje=10,
                       desde=self.hoy, hasta=self.hoy - dt.timedelta(days=1))
        with self.assertRaises(ValidationError):
            pr.full_clean()
