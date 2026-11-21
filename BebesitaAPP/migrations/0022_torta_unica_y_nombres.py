"""La torta duplicada otra vez fuera, y los nombres escritos normal (21-11-2026).

La 0021 borro torta-de-cuchuflis-2 el 21-11 a las 12:52, y en el mismo build
`catalogo_inicial` la volvio a crear: buscaba la torta por el nombre exacto
"Torta de cuchuflís", y la duena habia renombrado la original a "TORTA CUCHUFLIS".
Ese comando ya busca por la direccion (gestion/management/commands/catalogo_inicial.py).

1. torta-de-cuchuflis-2: igual que en la 0021. Sin historia se borra con 301 a
   torta-de-cuchuflis; con historia solo se oculta.
2. Los nombres que la duena escribio en MAYUSCULAS vuelven a escribirse normal. Las
   tarjetas los siguen mostrando en mayusculas por CSS, pero el dato en mayusculas
   salia asi en el title de Google, el schema, el carrito y los correos. Solo se
   tocan los que estan enteros en mayusculas; un nombre que ella escribio de otra
   forma se respeta.
"""
from django.db import migrations

NOMBRES = {
    "alfajores": "Alfajores",
    "cuchuflis-rellenos": "Cuchuflís rellenos",
    "cuchuflis-banados": "Cuchuflís bañados",
    "torta-de-cuchuflis": "Torta de cuchuflís",
    "barquillos-rellenos-banados-en-chocolate": "Barquillos Rellenos Bañados en Chocolate",
    "pan-de-pascua": "Pan de pascua",
}
QUIEN = "migracion 0022 (pedido de Diego, 21-11-2026)"


def _tiene_historia(apps, producto):
    Producto = apps.get_model("BebesitaAPP", "Producto")
    ids = [producto.pk] + list(Producto.objects.filter(variante_de_id=producto.pk).values_list("pk", flat=True))
    return any(apps.get_model(app, modelo).objects.filter(producto_id__in=ids).exists()
               for app, modelo in (("BebesitaAPP", "PedidoItem"), ("gestion", "PedidoItem"),
                                   ("gestion", "Componente"), ("gestion", "CostoProducto")))


def adelante(apps, schema_editor):
    Producto = apps.get_model("BebesitaAPP", "Producto")
    Redireccion = apps.get_model("BebesitaAPP", "RedireccionProducto")
    dup = Producto.objects.filter(slug="torta-de-cuchuflis-2", variante_de__isnull=True).first()
    torta = Producto.objects.filter(slug="torta-de-cuchuflis", variante_de__isnull=True).first()
    if dup and torta:
        if _tiene_historia(apps, dup):
            Producto.objects.filter(pk=dup.pk).update(visible=False)
        else:
            Redireccion.objects.filter(destino_id=dup.pk).update(destino=torta)
            Redireccion.objects.update_or_create(
                slug="torta-de-cuchuflis-2",
                defaults={"pk_antiguo": dup.pk, "nombre": dup.nombre, "destino": torta, "borrado_por": QUIEN})
            dup.delete()
    for slug, nombre in NOMBRES.items():
        producto = Producto.objects.filter(slug=slug, variante_de__isnull=True).first()
        if producto and producto.nombre.strip() and producto.nombre == producto.nombre.upper():
            Producto.objects.filter(pk=producto.pk).update(nombre=nombre)


class Migration(migrations.Migration):

    dependencies = [
        ("BebesitaAPP", "0021_pan_de_pascua_unico"),
        ("gestion", "0006_costoproducto"),
    ]

    operations = [migrations.RunPython(adelante, migrations.RunPython.noop)]
