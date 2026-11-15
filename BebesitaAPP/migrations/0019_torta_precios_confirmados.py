"""Precios de la torta de cuchuflis confirmados por la duena (15-11-2026).

Diego, con Tamara al lado, los dejo por escrito:

    50 cuchuflis    sin cobertura $14.990    con cobertura $17.490
    100 cuchuflis   sin cobertura $29.990    con cobertura $34.990

Contra lo que habia, cambia UNO: la de 50 con cobertura (chocolate o chocolate
blanco) baja de $17.990 a $17.490. Calza con el precio nuevo del cuchufli
bañado: 50 x $350 = $17.500.

La migracion deja la tabla COMPLETA como se confirmo, no solo la diferencia:
asi la base queda en los cuatro precios acordados aunque alguno se hubiera
movido a mano. Se reconoce cada precio por lo que ES (el tamaño por su numero,
la cobertura por si dice "sin"), nunca por id. Un tamaño que no este en la
tabla no se toca.
"""
import re

from django.db import migrations

# (cuchuflis, con cobertura) -> precio
PRECIOS = {
    (50, False): 14990,
    (50, True): 17490,
    (100, False): 29990,
    (100, True): 34990,
}
# Lo unico que cambio, para poder deshacer.
ANTES = {(50, True): 17990}


def _torta(Producto):
    principales = Producto.objects.filter(variante_de__isnull=True)
    return (principales.filter(slug="torta-de-cuchuflis").first()
            or principales.filter(nombre="Torta de cuchuflís").first())


def _clave(combo):
    """(50, True) para "50 cuchuflís · Chocolate"; None si no se reconoce."""
    cuchuflis = con_cobertura = None
    for opcion in combo.opciones.all():
        if opcion.tipo == "tamano":
            numero = re.search(r"\d+", opcion.nombre)
            cuchuflis = int(numero.group()) if numero else None
        elif opcion.tipo == "cobertura":
            con_cobertura = not opcion.nombre.strip().lower().startswith("sin")
    if cuchuflis is None or con_cobertura is None:
        return None
    return cuchuflis, con_cobertura


def _aplicar(apps, tabla):
    Producto = apps.get_model("BebesitaAPP", "Producto")
    PrecioCombinacion = apps.get_model("BebesitaAPP", "PrecioCombinacion")
    torta = _torta(Producto)
    if not torta:
        return  # base nueva: catalogo_inicial ya la crea con estos precios
    for combo in PrecioCombinacion.objects.filter(producto=torta).prefetch_related("opciones"):
        precio = tabla.get(_clave(combo))
        if precio and combo.precio != precio:
            combo.precio = precio
            combo.save(update_fields=["precio"])


def confirmados(apps, schema_editor):
    _aplicar(apps, PRECIOS)


def anteriores(apps, schema_editor):
    _aplicar(apps, ANTES)


class Migration(migrations.Migration):

    dependencies = [
        ("BebesitaAPP", "0018_cuchuflis_por_unidad"),
    ]

    operations = [migrations.RunPython(confirmados, anteriores)]
