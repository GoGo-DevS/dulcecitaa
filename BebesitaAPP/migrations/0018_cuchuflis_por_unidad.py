"""Los cuchuflis se venden por unidad (15-11-2026, pedido de la duena).

Hasta hoy iban en bolsita de 4: $1.590 los bañados y $1.190 los rellenos, desde
10 bolsitas. Desde ahora se venden por unidad: $350 los bañados (con cobertura)
y $300 los rellenos (sin cobertura), desde 30 unidades.

Por que una migracion y no el panel: el precio, la unidad de venta, el minimo
y los textos de la ficha tienen que cambiar EN EL MISMO deploy. Cambiar el
precio a mano en el panel dejaria, mientras tanto, "$350 la bolsita de 4"
publicado y cobrandose: un precio mal publicado es el error mas caro de una
tienda.

- Se busca por slug (y por nombre si el slug cambio), nunca por id: la base de
  produccion no tiene por que tener los mismos ids que la local.
- En una base nueva no hay productos todavia y no hace nada: catalogo_inicial
  ya los crea por unidad.
- La descripcion la escribe la duena desde el panel: solo se cambia la frase
  de fabrica ("Se venden en bolsita de 4 unidades."). Si ella la reescribio,
  su texto se respeta.
- La torta de cuchuflis NO se toca aca.
"""
from django.db import migrations

MINIMO = 30
FRASE_BOLSITA = "Se venden en bolsita de 4 unidades."
FRASE_UNIDAD = "Se venden por unidad, desde 30."

# slug -> nombre de fabrica, precio por unidad y lo que costaba la bolsita de 4.
CUCHUFLIS = {
    "cuchuflis-banados": {"nombre": "Cuchuflís bañados", "precio": 350, "bolsita": 1590},
    "cuchuflis-rellenos": {"nombre": "Cuchuflís rellenos", "precio": 300, "bolsita": 1190},
}

# La pregunta de la portada que responde el minimo: decia 10 para todo.
PREGUNTA_MINIMO = "¿Cuál es el pedido mínimo?"
FRASE_MINIMO = " Los cuchuflís se venden por unidad, desde 30."


def _cuchuflis(Producto):
    for slug, datos in CUCHUFLIS.items():
        principales = Producto.objects.filter(variante_de__isnull=True)
        producto = (principales.filter(slug=slug).first()
                    or principales.filter(nombre=datos["nombre"]).first())
        if producto:
            yield producto, datos


def por_unidad(apps, schema_editor):
    Producto = apps.get_model("BebesitaAPP", "Producto")
    Pregunta = apps.get_model("BebesitaAPP", "PreguntaFrecuente")

    cambiados = 0
    for producto, datos in _cuchuflis(Producto):
        producto.precio = datos["precio"]
        producto.unidades_por_pack = 1
        producto.minimo = MINIMO
        producto.descripcion = (producto.descripcion or "").replace(FRASE_BOLSITA, FRASE_UNIDAD)
        producto.save(update_fields=["precio", "unidades_por_pack", "minimo", "descripcion"])
        cambiados += 1

    if not cambiados:
        return
    for pregunta in Pregunta.objects.filter(producto__isnull=True, pregunta=PREGUNTA_MINIMO):
        if "cuchufl" not in pregunta.respuesta.lower():
            pregunta.respuesta = pregunta.respuesta.rstrip() + FRASE_MINIMO
            pregunta.save(update_fields=["respuesta"])


def a_bolsita(apps, schema_editor):
    Producto = apps.get_model("BebesitaAPP", "Producto")
    Pregunta = apps.get_model("BebesitaAPP", "PreguntaFrecuente")

    for producto, datos in _cuchuflis(Producto):
        producto.precio = datos["bolsita"]
        producto.unidades_por_pack = 4
        producto.minimo = 0
        producto.descripcion = (producto.descripcion or "").replace(FRASE_UNIDAD, FRASE_BOLSITA)
        producto.save(update_fields=["precio", "unidades_por_pack", "minimo", "descripcion"])

    for pregunta in Pregunta.objects.filter(producto__isnull=True, pregunta=PREGUNTA_MINIMO):
        if pregunta.respuesta.endswith(FRASE_MINIMO):
            pregunta.respuesta = pregunta.respuesta[:-len(FRASE_MINIMO)]
            pregunta.save(update_fields=["respuesta"])


class Migration(migrations.Migration):

    dependencies = [
        ("BebesitaAPP", "0017_promocion"),
    ]

    operations = [migrations.RunPython(por_unidad, a_bolsita)]
