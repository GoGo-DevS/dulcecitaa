"""Crea o actualiza la promocion de una campana por fecha.

Existe porque el plan de Render es free y NO tiene Shell: sin esto la duena
tendria que entrar al panel igual, pero asi queda registrado el porcentaje y
las fechas de cada campana en un comando que se puede repetir.

Las fechas se pasan completas a proposito. Un "dura 10 dias" se calcula desde
hoy y el dia que se corra de nuevo da otro rango distinto sin avisar.
"""
import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from BebesitaAPP.models import Promocion


class Command(BaseCommand):
    help = "Crea o actualiza una promocion con fechas. Ensayo por defecto."

    def add_arguments(self, p):
        p.add_argument("--nombre", required=True)
        p.add_argument("--porcentaje", type=int, required=True)
        p.add_argument("--desde", required=True, help="AAAA-MM-DD")
        p.add_argument("--hasta", required=True, help="AAAA-MM-DD, ese dia TODAVIA aplica")
        p.add_argument("--etiqueta", default="Oferta", help="El sello sobre el precio.")
        p.add_argument("--mensaje", default="", help="La franja de arriba.")
        p.add_argument("--apagar-otras", action="store_true",
                       help="Desactiva las demas. Dos promociones encimadas hacen "
                            "que gane la de mayor descuento, y eso sorprende.")
        p.add_argument("--confirmar", action="store_true")

    def handle(self, *a, **o):
        try:
            desde = dt.date.fromisoformat(o["desde"])
            hasta = dt.date.fromisoformat(o["hasta"])
        except ValueError as e:
            raise CommandError(f"Fecha invalida, usa AAAA-MM-DD: {e}")
        if hasta < desde:
            raise CommandError("La fecha de termino es anterior al inicio.")
        if not 1 <= o["porcentaje"] <= 60:
            raise CommandError("El porcentaje tiene que estar entre 1 y 60.")

        hoy = timezone.localdate()
        corre_hoy = desde <= hoy <= hasta
        self.stdout.write(f'  {o["nombre"]}: {o["porcentaje"]}% del {desde} al {hasta}')
        self.stdout.write(f'  {"APLICA HOY" if corre_hoy else f"no aplica hoy ({hoy})"}')

        otras = Promocion.objects.filter(activa=True).exclude(nombre=o["nombre"])
        solapan = [p for p in otras if not (p.hasta < desde or p.desde > hasta)]
        if solapan:
            self.stdout.write(self.style.WARNING(
                f'  OJO: se solapa con {len(solapan)} activa(s): ' +
                ', '.join(f'{p.nombre} ({p.porcentaje}%)' for p in solapan)))
            self.stdout.write('       Gana la de MAYOR descuento. Usa --apagar-otras si no es lo que quieres.')

        if not o["confirmar"]:
            self.stdout.write(self.style.WARNING("  ENSAYO. Con --confirmar se guarda."))
            return

        promo, creada = Promocion.objects.update_or_create(
            nombre=o["nombre"],
            defaults=dict(porcentaje=o["porcentaje"], desde=desde, hasta=hasta,
                          etiqueta=o["etiqueta"], mensaje=o["mensaje"], activa=True))
        if o["apagar_otras"]:
            n = Promocion.objects.exclude(pk=promo.pk).filter(activa=True).update(activa=False)
            self.stdout.write(f"  {n} promocion(es) apagada(s)")
        self.stdout.write(self.style.SUCCESS(f'  {"creada" if creada else "actualizada"}: {promo}'))
