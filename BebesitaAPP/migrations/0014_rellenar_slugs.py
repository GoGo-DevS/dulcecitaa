"""Da direccion web (slug) a los productos que ya existian.

Los visibles primero: si un producto oculto y uno visible se llaman igual
("Alfajores", la variante vieja de chocolate blanco), la direccion limpia
/productos/alfajores/ queda para el que se vende.
"""
from django.db import migrations
from django.utils.text import slugify


def rellenar(apps, schema_editor):
    Producto = apps.get_model("BebesitaAPP", "Producto")
    usados = set(Producto.objects.exclude(slug="").values_list("slug", flat=True))
    for p in Producto.objects.filter(slug="").order_by("-visible", "variante_de_id", "orden", "pk"):
        base = slugify(p.nombre)[:110] or "producto"
        slug, n = base, 2
        while slug in usados:
            slug, n = f"{base}-{n}", n + 1
        usados.add(slug)
        p.slug = slug
        p.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [("BebesitaAPP", "0013_producto_slug")]
    operations = [migrations.RunPython(rellenar, migrations.RunPython.noop)]
