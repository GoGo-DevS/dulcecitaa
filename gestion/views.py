from datetime import date
from urllib.parse import quote

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from BebesitaAPP.models import Producto

from .forms import (
    ClienteForm,
    ComponenteForm,
    CompraForm,
    PedidoClienteForm,
    PedidoForm,
    PedidoItemForm,
)
from .models import Cliente, Componente, Compra, Pedido, PedidoItem


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _mes_anterior(y, m):
    return (y - 1, 12) if m == 1 else (y, m - 1)


def _mes_siguiente(y, m):
    return (y + 1, 1) if m == 12 else (y, m + 1)


MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


# ----------------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------------
def dashboard(request):
    hoy = timezone.localdate()
    try:
        y, m = (int(p) for p in request.GET.get("mes", "").split("-"))
        date(y, m, 1)
    except (ValueError, TypeError):
        y, m = hoy.year, hoy.month

    pedidos_mes = (
        Pedido.objects.filter(fecha_pedido__year=y, fecha_pedido__month=m)
        .exclude(estado=Pedido.CANCELADO)
        .select_related("cliente")
        .prefetch_related("items", "compras")
    )

    ventas = sum(p.precio_total for p in pedidos_mes)
    costos = sum(p.costo_aplicado for p in pedidos_mes)
    utilidad = ventas - costos

    por_entregar = (
        Pedido.objects.filter(estado__in=[Pedido.COTIZADO, Pedido.CONFIRMADO], fecha_entrega__isnull=False)
        .select_related("cliente")
        .prefetch_related("items")
        .order_by("fecha_entrega")[:8]
    )

    sin_costear = [
        p for p in Pedido.objects.filter(estado=Pedido.ENTREGADO)
        .select_related("cliente").prefetch_related("compras")
        if not p.tiene_compras
    ][:5]

    py, pm = _mes_anterior(y, m)
    ny, nm = _mes_siguiente(y, m)

    context = {
        "y": y, "m": m, "mes_nombre": MESES_ES[m],
        "mes_prev": f"{py}-{pm:02d}", "mes_next": f"{ny}-{nm:02d}",
        "ventas": ventas, "costos": costos, "utilidad": utilidad,
        "pedidos_mes": pedidos_mes,
        "por_entregar": por_entregar,
        "sin_costear": sin_costear,
        "total_clientes": Cliente.objects.filter(activo=True).count(),
    }
    return render(request, "gestion/dashboard.html", context)


# ----------------------------------------------------------------------------
# Clientes
# ----------------------------------------------------------------------------
def clientes_lista(request):
    q = request.GET.get("q", "").strip()
    clientes = Cliente.objects.all()
    if q:
        clientes = clientes.filter(
            Q(nombre__icontains=q) | Q(empresa__icontains=q) | Q(whatsapp__icontains=q)
        )
    return render(request, "gestion/clientes_lista.html", {"clientes": clientes, "q": q})


def cliente_nuevo(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f"Cliente «{cliente}» creado.")
            return redirect("gestion:clientes")
    else:
        form = ClienteForm()
    return render(request, "gestion/cliente_form.html", {"form": form, "titulo": "Nuevo cliente"})


def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cliente «{cliente}» actualizado.")
            return redirect("gestion:clientes")
    else:
        form = ClienteForm(instance=cliente)
    return render(
        request,
        "gestion/cliente_form.html",
        {"form": form, "titulo": "Editar cliente", "cliente": cliente},
    )


# ----------------------------------------------------------------------------
# Pedidos
# ----------------------------------------------------------------------------
def pedidos_lista(request):
    pedidos = (
        Pedido.objects.select_related("cliente")
        .prefetch_related("items", "compras")
        .all()
    )
    estado = request.GET.get("estado", "").strip()
    if estado:
        pedidos = pedidos.filter(estado=estado)
    return render(
        request,
        "gestion/pedidos_lista.html",
        {"pedidos": pedidos, "estado": estado, "estados": Pedido.ESTADOS},
    )


def pedido_nuevo(request):
    if request.method == "POST":
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            messages.success(request, "Pedido creado. Agrega los productos.")
            return redirect("gestion:pedido_detalle", pk=pedido.pk)
    else:
        inicial = {"fecha_pedido": timezone.localdate()}
        form = PedidoForm(initial=inicial)
        if not Cliente.objects.filter(activo=True).exists():
            messages.warning(request, "Primero crea un cliente.")
    return render(request, "gestion/pedido_form.html", {"form": form, "titulo": "Nuevo pedido"})


def pedido_detalle(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related("cliente").prefetch_related("items__componentes", "compras"), pk=pk
    )
    item_form = PedidoItemForm()
    componente_form = ComponenteForm()
    cliente_form = PedidoClienteForm(instance=pedido)
    compra_form = CompraForm(initial={"fecha": timezone.localdate()})

    # Catálogo (todo) para el datalist de cajas y el precio en vivo
    productos = list(Producto.objects.all().order_by("nombre").values("id", "nombre", "precio"))

    # Mensaje de cotización para WhatsApp
    saludo = pedido.cliente.titulo
    lineas = [f"Hola {saludo}! Te paso la cotización de Dulcecita 🧁", ""]
    for it in pedido.items.all():
        unidad = "caja" if it.cantidad == 1 else "cajas"
        lineas.append(f"• {it.cantidad} {unidad} · {it.descripcion} — ${it.subtotal:,}".replace(",", "."))
        for comp in it.componentes.all():
            lineas.append(f"    ◦ {comp.cantidad} × {comp.nombre} por caja")
    if pedido.tiene_componentes:
        lineas += ["", "A producir:"]
        for p in pedido.produccion:
            lineas.append(f"    • {p['total']} {p['nombre']}")
    lineas += ["", f"*Total: ${pedido.precio_total:,}*".replace(",", "."), "", "¿Lo confirmamos? 💕"]
    mensaje = "\n".join(lineas)
    if pedido.cliente.whatsapp_digits:
        wa_url = f"https://wa.me/{pedido.cliente.whatsapp_digits}?text={quote(mensaje)}"
    else:
        wa_url = f"https://wa.me/?text={quote(mensaje)}"

    context = {
        "pedido": pedido,
        "item_form": item_form,
        "componente_form": componente_form,
        "cliente_form": cliente_form,
        "compra_form": compra_form,
        "productos": productos,
        "wa_url": wa_url,
        "estados": Pedido.ESTADOS,
    }
    return render(request, "gestion/pedido_detalle.html", context)


def pedido_cliente(request, pk):
    """Cambia el cliente del pedido desde el detalle (combo en la cabecera)."""
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        form = PedidoClienteForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente del pedido actualizado.")
        else:
            messages.error(request, "No se pudo cambiar el cliente.")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)


def pedido_item_agregar(request, pk):
    """Agrega una CAJA al pedido. La caja queda enlazada al catálogo:
    si el nombre no existe como Producto, se crea (interconexión)."""
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        form = PedidoItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            nombre = item.descripcion.strip()
            if nombre:
                producto, creado = Producto.objects.get_or_create(
                    nombre__iexact=nombre,
                    defaults={"nombre": nombre, "precio": item.precio_unitario or 0,
                              "visible": False, "disponible": False},
                )
                item.producto = producto
                item.descripcion = producto.nombre
            item.pedido = pedido
            item.save()
            messages.success(request, "Caja agregada. Ahora elígele los productos que lleva.")
        else:
            messages.error(request, "Revisa los datos de la caja.")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)


def pedido_item_eliminar(request, pk, item_pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        PedidoItem.objects.filter(pk=item_pk, pedido=pedido).delete()
        messages.info(request, "Caja eliminada.")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)


def componente_agregar(request, pk, item_pk):
    """Agrega un producto DENTRO de una caja."""
    pedido = get_object_or_404(Pedido, pk=pk)
    item = get_object_or_404(PedidoItem, pk=item_pk, pedido=pedido)
    if request.method == "POST":
        form = ComponenteForm(request.POST)
        if form.is_valid():
            comp = form.save(commit=False)
            comp.item = item
            comp.save()
            messages.success(request, "Producto agregado a la caja.")
        else:
            messages.error(request, "Revisa el producto de la caja.")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)


def componente_eliminar(request, pk, item_pk, comp_pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        Componente.objects.filter(pk=comp_pk, item__pk=item_pk, item__pedido=pedido).delete()
        messages.info(request, "Producto quitado de la caja.")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)


def pedido_estado(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        nuevo = request.POST.get("estado")
        if nuevo in dict(Pedido.ESTADOS):
            pedido.estado = nuevo
        if "pagado" in request.POST:
            pedido.pagado = request.POST.get("pagado") == "1"
        pedido.save()
        messages.success(request, "Pedido actualizado.")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)


def pedido_eliminar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        pedido.delete()
        messages.info(request, "Pedido eliminado.")
        return redirect("gestion:pedidos")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)


# ----------------------------------------------------------------------------
# Compras
# ----------------------------------------------------------------------------
def compra_nueva(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        form = CompraForm(request.POST, request.FILES)
        if form.is_valid():
            compra = form.save(commit=False)
            compra.pedido = pedido
            compra.save()
            messages.success(request, "Compra registrada. El costo del pedido ahora es real.")
        else:
            messages.error(request, "Revisa los datos de la compra.")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)


def compra_eliminar(request, pk, compra_pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        Compra.objects.filter(pk=compra_pk, pedido=pedido).delete()
        messages.info(request, "Compra eliminada.")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)
