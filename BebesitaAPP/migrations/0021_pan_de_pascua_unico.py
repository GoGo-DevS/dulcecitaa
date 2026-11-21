"""Un solo pan de pascua, igual a lo que se promociona, y sin productos duplicados (20-11-2026).

El 19-11 la duena creo el pan de pascua dos veces ("PAN DE PASCUA", $8.500, misma foto)
y duplico la torta: el panel no tenia como borrar y, con dos productos del mismo nombre,
no dejaba guardar ninguno. Diego pidio dejar el pan 1:1 con lo que se venia
promocionando (temporada.OFERTAS_NAVIDAD: medio kilo, $8.590) y con sus fotos.

Lo que hace, en este orden:
1. pan-de-pascua-2 y torta-de-cuchuflis-2: si NO tienen historia (pedidos de la web,
   cajas o componentes del panel, costo cargado), se borran y su direccion queda con
   301 al producto que se queda. Si tienen historia, solo se ocultan: nunca se borra
   una venta.
2. El pan que se queda (pan-de-pascua; si no existiera, el -2): nombre "Pan de pascua",
   $8.590, la frase del formato delante del texto de la duena (que se conserva), visible,
   la foto principal y 3 fotos extra (BebesitaAPP/datos/pan-de-pascua/, WebP < 100 KB).

Se puede correr dos veces sin duplicar fotos. No tiene vuelta atras automatica: los
productos borrados no tenian ventas.
"""
from pathlib import Path

from django.core.files import File
from django.db import migrations

FOTOS = Path(__file__).resolve().parent.parent / "datos" / "pan-de-pascua"
PRINCIPAL = "pan-de-pascua-artesanal.webp"
EXTRAS = ("pan-de-pascua-en-su-molde.webp", "pan-de-pascua-envasado-receta-artesanal.webp",
          "pan-de-pascua-pesado.webp")
NOMBRE = "Pan de pascua"
PRECIO = 8590
FORMATO = "Pan de pascua artesanal en formato de medio kilo."
DUPLICADOS = (("pan-de-pascua-2", "pan-de-pascua"), ("torta-de-cuchuflis-2", "torta-de-cuchuflis"))
QUIEN = "migracion 0021 (pedido de Diego, 20-11-2026)"


def _ids_con_variantes(Producto, producto):
    return [producto.pk] + list(Producto.objects.filter(variante_de_id=producto.pk).values_list("pk", flat=True))


def _tiene_historia(apps, producto):
    Producto = apps.get_model("BebesitaAPP", "Producto")
    ids = _ids_con_variantes(Producto, producto)
    return any(apps.get_model(app, modelo).objects.filter(producto_id__in=ids).exists()
               for app, modelo in (("BebesitaAPP", "PedidoItem"), ("gestion", "PedidoItem"),
                                   ("gestion", "Componente"), ("gestion", "CostoProducto")))


def _quitar_duplicados(apps):
    Producto = apps.get_model("BebesitaAPP", "Producto")
    Redireccion = apps.get_model("BebesitaAPP", "RedireccionProducto")
    for viejo, queda in DUPLICADOS:
        dup = Producto.objects.filter(slug=viejo, variante_de__isnull=True).first()
        destino = Producto.objects.filter(slug=queda, variante_de__isnull=True).first()
        if dup is None or destino is None:
            continue
        if _tiene_historia(apps, dup):
            Producto.objects.filter(pk=dup.pk).update(visible=False)
            continue
        Redireccion.objects.filter(destino_id=dup.pk).update(destino=destino)
        Redireccion.objects.update_or_create(
            slug=viejo, defaults={"pk_antiguo": dup.pk, "nombre": dup.nombre, "destino": destino,
                                  "borrado_por": QUIEN})
        dup.delete()


def _arreglar_pan(apps):
    Producto = apps.get_model("BebesitaAPP", "Producto")
    Imagen = apps.get_model("BebesitaAPP", "ProductoImagen")
    pan = (Producto.objects.filter(slug="pan-de-pascua", variante_de__isnull=True).first()
           or Producto.objects.filter(slug="pan-de-pascua-2", variante_de__isnull=True).first())
    if pan is None:
        return
    pan.nombre = NOMBRE
    pan.precio = PRECIO
    texto = (pan.descripcion or "").strip()
    if FORMATO not in texto:
        pan.descripcion = f"{FORMATO} {texto}".strip()
    pan.visible = True
    if Path(PRINCIPAL).stem not in (pan.imagen.name or ""):
        with open(FOTOS / PRINCIPAL, "rb") as archivo:
            pan.imagen.save(PRINCIPAL, File(archivo), save=False)
    pan.save()
    for nombre in EXTRAS:
        if Imagen.objects.filter(producto_id=pan.pk, imagen__contains=Path(nombre).stem).exists():
            continue
        extra = Imagen(producto_id=pan.pk)
        with open(FOTOS / nombre, "rb") as archivo:
            extra.imagen.save(nombre, File(archivo), save=False)
        extra.save()


def adelante(apps, schema_editor):
    _quitar_duplicados(apps)
    _arreglar_pan(apps)


class Migration(migrations.Migration):

    dependencies = [
        ("BebesitaAPP", "0020_redireccion_producto"),
        ("gestion", "0006_costoproducto"),
    ]

    operations = [migrations.RunPython(adelante, migrations.RunPython.noop)]
