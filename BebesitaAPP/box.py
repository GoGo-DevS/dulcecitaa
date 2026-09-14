"""Arma tu box: el cliente combina productos y coberturas en una caja.

Es distinto del pedido normal en tres cosas, todas pedidas por la duena:
- el minimo es por LINEA y parte en 3 (no en 10): 3 alfajores blancos,
  3 negros, 3 cuchuflis rellenos...
- se cobra la caja, un valor fijo por box (BOX_PRICE);
- en el carrito aparece como un bloque "Arma tu box #1" con sus lineas, y
  cada linea se ajusta de a una unidad.

En la sesion vive aparte del carrito normal: session["boxes"] es una lista de
cajas y cada caja es {linea: cantidad}, con la misma clave de linea que usa el
carrito ("15-2" = producto 15 con la opcion 2).
"""
from itertools import product as combinar

from django.conf import settings

from .models import Producto


def minimo_box():
    return max(1, int(getattr(settings, "MINIMO_BOX", 3)))


def precio_caja():
    return int(getattr(settings, "BOX_PRICE", 0))


def filas_para_armar():
    """Una fila por cada combinacion vendible: "Alfajores · Chocolate blanco".

    Con un solo grupo de opciones son tantas filas como coberturas; si mañana
    se agrega relleno, salen todas las combinaciones cobertura x relleno.
    """
    from .views import _clave_linea

    filas = []
    productos = (Producto.objects.filter(visible=True, disponible=True, variante_de__isnull=True)
                 .prefetch_related("opciones").order_by("orden", "nombre"))
    for p in productos:
        grupos = [opciones for _tipo, _etiqueta, opciones in p.grupos_opciones()]
        for combinacion in (combinar(*grupos) if grupos else [()]):
            filas.append({
                "clave": _clave_linea(p.id, [op.id for op in combinacion]),
                "producto": p,
                "opciones": list(combinacion),
                "precio": p.precio + sum(op.recargo for op in combinacion),
            })
    return filas


def get_boxes(request):
    """Cajas de la sesion, limpias: sin lineas bajo el minimo ni cajas vacias."""
    from .views import _clave_linea, _parse_linea

    minimo = minimo_box()
    boxes = []
    for caja in request.session.get("boxes", []) or []:
        if not isinstance(caja, dict):
            continue
        limpia = {}
        for linea, qty in caja.items():
            parsed = _parse_linea(linea)
            try:
                qty = int(qty)
            except (TypeError, ValueError):
                continue
            if parsed and qty >= minimo:
                limpia[_clave_linea(*parsed)] = qty
        if limpia:
            boxes.append(limpia)
    return boxes


def save_boxes(request, boxes):
    request.session["boxes"] = [caja for caja in boxes if caja]
    request.session.modified = True


def build_boxes(boxes):
    """Para mostrar y cobrar: cada caja con sus lineas, subtotal, caja y total."""
    from .views import _build_cart_items

    resultado = []
    for indice, caja in enumerate(boxes):
        items, subtotal = _build_cart_items(caja)
        if not items:
            continue
        resultado.append({
            "indice": indice,
            "numero": indice + 1,
            "items": items,
            "unidades": sum(item["cantidad"] for item in items),
            "subtotal": subtotal,
            "caja": precio_caja(),
            "total": subtotal + precio_caja(),
        })
    return resultado


def unidades(boxes):
    return sum(sum(caja.values()) for caja in boxes)
