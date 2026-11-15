"""Productos de la tienda web, desde el panel (15-11-2026).

Hasta hoy el catalogo de dulcecita.cl solo se editaba en /admin/. La duena no
lo usa, asi que cada cambio de precio, de foto o de minimo pasaba por Diego y
por un deploy. Esta seccion le deja hacerlo a ella, desde el telefono.

Reglas que vienen de errores caros:
- Un producto NO se borra: los pedidos apuntan a el con CASCADE y borrarlo se
  llevaria los pedidos que lo compraron. Se oculta.
- La direccion web (slug) no se edita: cambiarla rompe los enlaces compartidos
  y lo que Google ya tiene indexado.
- Despues de guardar se dice en pesos que cambio ("$1.590 -> $350"): un precio
  mal publicado es el error mas caro de una tienda, y el que lo escribio tiene
  que poder verlo al tiro.
"""
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from BebesitaAPP import fichas_seo
from BebesitaAPP.models import Opcion, Producto, Promocion

from .forms import ProductoForm

_ORDEN_TIPOS = {tipo: i for i, (tipo, _) in enumerate(Opcion.TIPOS)}


def _pesos(valor):
    return "$" + fichas_seo._pesos(valor)


def como_se_cobra(producto):
    """"$350 por unidad", "$1.590 la bolsita de 4" o "desde $14.990 (4 precios)".

    Precio de LISTA, sin la promocion: en el panel la duena edita el precio
    normal; el descuento de una campaña se ve en Promos.
    """
    combos = list(producto.precios_combinacion.all())
    if combos:
        cuantos = len(combos)
        return f"desde {_pesos(min(c.precio for c in combos))} ({cuantos} precio{'s' if cuantos != 1 else ''})"
    return f"{_pesos(producto.precio)} {fichas_seo.unidad_de_venta(producto)}"


def _nombre_combo(combo):
    """"50 cuchuflís · Sin cobertura": el tamaño primero, como en la web."""
    opciones = sorted(combo.opciones.all(), key=lambda op: (_ORDEN_TIPOS.get(op.tipo, 9), op.orden, op.nombre))
    return " · ".join(op.nombre for op in opciones) or "Sin opciones"


def _principales():
    return (Producto.objects.filter(variante_de__isnull=True)
            .prefetch_related("opciones", "precios_combinacion"))


def productos_lista(request):
    productos = list(_principales().order_by("orden", "nombre"))
    for p in productos:
        p.cobro = como_se_cobra(p)
        p.minimo_real = p.minimo_efectivo()
    return render(request, "gestion/productos_lista.html", {
        "en_web": [p for p in productos if p.visible],
        "ocultos": [p for p in productos if not p.visible],
        "promo": Promocion.vigente(),
    })


def _leer_combos(datos, combos):
    """Los precios por combinacion que vienen en el formulario.

    Devuelve ([(combo, precio nuevo)], [errores]). Solo se editan los que ya
    existen: crear una combinacion nueva es armar un producto, y eso se hace
    con Diego.
    """
    leidos, errores = [], []
    for combo in combos:
        crudo = (datos.get(f"combo_{combo.pk}") or "").strip().replace(".", "").replace("$", "")
        if not crudo.isdigit() or int(crudo) <= 0:
            errores.append(f"{combo.nombre}: escribe un precio mayor que cero.")
            combo.valor = datos.get(f"combo_{combo.pk}", "")
            continue
        combo.valor = int(crudo)
        leidos.append((combo, int(crudo)))
    return leidos, errores


def _cambios(antes, producto):
    """Lo que cambio, en palabras y en pesos, para el aviso de despues de guardar."""
    cambios = []
    if antes["precio"] != producto.precio:
        cambios.append(f"precio {_pesos(antes['precio'])} → {_pesos(producto.precio)}")
    if antes["unidades_por_pack"] != producto.unidades_por_pack:
        cambios.append("ahora se vende " + ("por unidad" if producto.unidades_por_pack == 1
                                           else f"en paquete de {producto.unidades_por_pack}"))
    if antes["minimo"] != producto.minimo:
        cambios.append(f"mínimo {producto.minimo_efectivo()}")
    if antes["visible"] != producto.visible:
        cambios.append("ahora se ve en la web" if producto.visible else "ya no se ve en la web")
    if antes["disponible"] != producto.disponible:
        cambios.append("se puede comprar" if producto.disponible else "quedó como no disponible")
    return cambios


def producto_form(request, pk=None):
    producto = get_object_or_404(Producto, pk=pk, variante_de__isnull=True) if pk else None
    combos = list(producto.precios_combinacion.prefetch_related("opciones")) if producto else []
    for combo in combos:
        combo.nombre = _nombre_combo(combo)
        combo.valor = combo.precio
    # Antes de armar el formulario: validar un ModelForm ya escribe sobre la instancia.
    antes = ({campo: getattr(producto, campo) for campo in
              ("precio", "unidades_por_pack", "minimo", "visible", "disponible")} if producto else None)
    errores_combos = []

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        precios_combo, errores_combos = _leer_combos(request.POST, combos)
        if form.is_valid() and not errores_combos:
            with transaction.atomic():
                guardado = form.save()
                cambios = _cambios(antes, guardado) if antes else []
                for combo, nuevo in precios_combo:
                    if combo.precio != nuevo:
                        cambios.append(f"{combo.nombre}: {_pesos(combo.precio)} → {_pesos(nuevo)}")
                        combo.precio = nuevo
                        combo.save(update_fields=["precio"])
            if not antes:
                messages.success(request, f"«{guardado.nombre}» creado: {como_se_cobra(guardado)}, "
                                          f"desde {guardado.minimo_efectivo()}.")
            elif cambios:
                messages.success(request, f"«{guardado.nombre}» guardado: {'; '.join(cambios)}.")
            else:
                messages.success(request, f"«{guardado.nombre}» guardado.")
            if guardado.visible:
                messages.info(request, "El cambio ya está en la web.")
            return redirect("gestion:productos")
    else:
        inicial = {}
        if not producto:
            ultimo = Producto.objects.filter(variante_de__isnull=True).aggregate(m=Max("orden"))["m"]
            inicial = {"orden": (ultimo or 0) + 1, "visible": True, "disponible": True}
        form = ProductoForm(instance=producto, initial=inicial)

    return render(request, "gestion/producto_form.html", {
        "form": form,
        "producto": producto,
        "combos": combos,
        "errores_combos": errores_combos,
        "titulo": f"Editar {producto.nombre}" if producto else "Nuevo producto",
        "cobro": como_se_cobra(producto) if producto else "",
        "promo": Promocion.vigente(),
        "minimo_general": max(1, int(getattr(settings, "MINIMO_UNIDADES", 1))),
    })


@require_POST
def producto_toggle(request, pk, campo):
    """Mostrar u ocultar, y marcar disponible o no, sin abrir el formulario."""
    if campo not in ("visible", "disponible"):
        return redirect("gestion:productos")
    producto = get_object_or_404(Producto, pk=pk, variante_de__isnull=True)
    setattr(producto, campo, not getattr(producto, campo))
    producto.save(update_fields=[campo])
    if campo == "visible":
        if producto.visible:
            messages.success(request, f"«{producto.nombre}» ya se ve en la web.")
        else:
            messages.info(request, f"«{producto.nombre}» quedó oculto: sale del catálogo, "
                                   "pero los pedidos anteriores no se pierden.")
    elif producto.disponible:
        messages.success(request, f"«{producto.nombre}» se puede comprar otra vez.")
    else:
        messages.info(request, f"«{producto.nombre}» quedó como no disponible: se ve, pero no se puede comprar.")
    return redirect("gestion:productos")
