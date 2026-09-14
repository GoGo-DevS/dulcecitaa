"""Las dos coberturas y el fin del alfajor blanco como producto aparte.

Antes el alfajor de chocolate blanco era un Producto propio (variante del
negro). Ahora la cobertura es una Opcion que se elige en la tarjeta, y la
ofrecen los tres productos: alfajores, barquillos y cuchuflis.

La variante NO se borra, se oculta: PedidoItem apunta a Producto con CASCADE,
asi que borrarla se llevaria por delante los pedidos que la compraron.
Se busca por nombre y no por id porque la base de produccion no tiene por que
tener los mismos ids que la local.
"""
from django.db import migrations

COBERTURAS = [
    ("Chocolate", "#5b3a29", 1),
    ("Chocolate blanco", "#f3ead9", 2),
]
LLEVAN_COBERTURA = ("alfajor", "barquillo", "cuchufl")


def crear(apps, schema_editor):
    Opcion = apps.get_model("BebesitaAPP", "Opcion")
    Producto = apps.get_model("BebesitaAPP", "Producto")

    coberturas = []
    for nombre, color, orden in COBERTURAS:
        op, _ = Opcion.objects.get_or_create(
            tipo="cobertura", nombre=nombre, defaults={"color": color, "orden": orden})
        coberturas.append(op)

    for producto in Producto.objects.filter(variante_de__isnull=True):
        if any(clave in producto.nombre.lower() for clave in LLEVAN_COBERTURA):
            producto.opciones.add(*coberturas)
            if producto.variante_nombre:
                producto.variante_nombre = ""
                producto.save(update_fields=["variante_nombre"])

    Producto.objects.filter(variante_de__isnull=False).update(visible=False)


def deshacer(apps, schema_editor):
    Opcion = apps.get_model("BebesitaAPP", "Opcion")
    Producto = apps.get_model("BebesitaAPP", "Producto")
    Producto.objects.filter(variante_de__isnull=False).update(visible=True)
    Opcion.objects.filter(tipo="cobertura", nombre__in=[c[0] for c in COBERTURAS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("BebesitaAPP", "0010_opciones_cobertura_relleno"),
    ]

    operations = [migrations.RunPython(crear, deshacer)]
