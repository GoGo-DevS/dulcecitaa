"""Carga las preguntas frecuentes que el sitio YA responde en otras paginas.

No inventa nada: cada respuesta sale de un dato que dulcecita.cl ya publica
(minimo de 10 unidades, despacho por Paket, 48 horas, coordinacion por
WhatsApp en Santiago, box desde 3 con empaque de $1.490) o de una variable de
settings. Lo unico que cambia es DONDE esta: juntas, en formato de pregunta y
declaradas como FAQPage, que es lo que Google puede desplegar bajo el
resultado y lo que un asistente puede citar.

Las preguntas sobre ingredientes, alergenos y vida util NO van aca: esas las
sabe la duena y son sobre un alimento. Una respuesta inventada ahi no es un
problema de SEO, es un problema de salud.

Idempotente y NO pisa lo escrito: si la pregunta ya existe se deja como esta,
porque la duena pudo haberla editado desde el panel. Ensayo por defecto.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from BebesitaAPP.models import PreguntaFrecuente


def preguntas():
    minimo = getattr(settings, "MINIMO_UNIDADES", 10)
    minimo_box = getattr(settings, "MINIMO_BOX", 3)
    box = getattr(settings, "BOX_PRICE", 1490)
    horas = getattr(settings, "DESPACHO_HORAS", 48)
    return [
        (10, "¿Cuál es el pedido mínimo?",
         f"El mínimo es de {minimo} unidades por producto. Si quieres mezclar varios "
         f"sabores, en Arma tu box el mínimo baja a {minimo_box} unidades por producto."),
        (20, "¿Hacen despacho a regiones?",
         "Sí, despachamos a todo Chile por Paket. Cuando el pedido sale te entregamos "
         "el seguimiento para que puedas verlo en camino."),
        (30, "¿Cómo es la entrega en Santiago?",
         "En Santiago la entrega se coordina directo por WhatsApp: acordamos día, hora "
         "y punto de entrega antes de despachar."),
        (40, "¿Cuánto demora mi pedido?",
         f"El pedido sale {horas} horas después de confirmado. Si lo necesitas para una "
         "fecha puntual, conviene escribirnos con anticipación."),
        (50, "¿Cuánto cuesta armar un box?",
         f"El empaque del box cuesta ${box:,}".replace(",", ".") +
         f" y puedes mezclar lo que quieras desde {minimo_box} unidades por producto."),
        (60, "¿Hacen regalos corporativos?",
         "Sí. Preparamos box para empresas, coffee breaks y regalos de fin de año, con "
         "la posibilidad de personalizar el empaque y sumar una tarjeta."),
    ]


class Command(BaseCommand):
    help = "Carga las preguntas frecuentes que el sitio ya responde. Ensayo por defecto."

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true",
                            help="Sin esto solo muestra lo que haria.")
        parser.add_argument("--solo-si-vacio", action="store_true",
                            help="No hace nada si ya hay alguna pregunta cargada. "
                                 "Es como corre en el build: si la duena borro una "
                                 "a proposito, el siguiente deploy NO la revive.")

    def handle(self, *args, **opciones):
        confirmar = opciones["confirmar"]
        if opciones["solo_si_vacio"] and PreguntaFrecuente.objects.exists():
            self.stdout.write("  ya hay preguntas cargadas: no se toca nada.")
            return
        nuevas = saltadas = 0
        for orden, pregunta, respuesta in preguntas():
            # se compara por la pregunta, no por el texto completo: la duena
            # puede haber reescrito la respuesta y eso no se toca.
            if PreguntaFrecuente.objects.filter(pregunta=pregunta).exists():
                saltadas += 1
                self.stdout.write(f"  ya existe: {pregunta}")
                continue
            nuevas += 1
            self.stdout.write(f"  {'CREA' if confirmar else 'crearia'}: {pregunta}")
            if confirmar:
                PreguntaFrecuente.objects.create(
                    pregunta=pregunta, respuesta=respuesta, orden=orden, activa=True)
        self.stdout.write("")
        self.stdout.write(f"  nuevas: {nuevas}   ya estaban: {saltadas}")
        if not confirmar:
            self.stdout.write(self.style.WARNING("  ENSAYO. Con --confirmar se guardan."))
