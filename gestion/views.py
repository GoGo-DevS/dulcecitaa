from datetime import date
from urllib.parse import quote

from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
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
from .models import Cliente, Componente, Compra, CostoProducto, Pedido, PedidoItem


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


def cliente_eliminar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        nombre = str(cliente)
        try:
            cliente.delete()
            messages.info(request, f"Cliente «{nombre}» eliminado.")
        except ProtectedError:
            messages.error(
                request,
                "No se puede eliminar: el cliente tiene pedidos asociados. "
                "Puedes marcarlo como inactivo en «Editar».",
            )
            return redirect("gestion:cliente_editar", pk=cliente.pk)
    return redirect("gestion:clientes")


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


def pedido_editar(request, pk):
    """Modifica los datos del pedido: cliente, descripción, fechas y notas."""
    pedido = get_object_or_404(Pedido, pk=pk)
    # Permitir el cliente actual aunque esté inactivo
    qs_clientes = Cliente.objects.filter(Q(activo=True) | Q(pk=pedido.cliente_id))
    if request.method == "POST":
        form = PedidoForm(request.POST, instance=pedido)
        form.fields["cliente"].queryset = qs_clientes
        if form.is_valid():
            form.save()
            messages.success(request, "Pedido actualizado.")
            return redirect("gestion:pedido_detalle", pk=pedido.pk)
    else:
        form = PedidoForm(instance=pedido)
        form.fields["cliente"].queryset = qs_clientes
    return render(request, "gestion/pedido_form.html", {
        "form": form,
        "titulo": f"Editar pedido #{pedido.id}",
        "submit_label": "Guardar cambios",
        "volver_url": reverse("gestion:pedido_detalle", kwargs={"pk": pedido.pk}),
    })


def pedido_nota(request, pk):
    """Guarda la nota/observación del pedido (siempre disponible, arriba)."""
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        pedido.notas = request.POST.get("notas", "").strip()
        pedido.save(update_fields=["notas"])
        messages.success(request, "Nota guardada.")
    return redirect("gestion:pedido_detalle", pk=pedido.pk)


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


# ----------------------------------------------------------------------------
# Costos por unidad (B)
# ----------------------------------------------------------------------------
def costos(request):
    """Define el costo de producción por UNIDAD de cada producto."""
    productos = list(Producto.objects.all().order_by("nombre"))
    if request.method == "POST":
        for p in productos:
            val = request.POST.get(f"costo_{p.id}", "").strip()
            costo = int(val) if val.isdigit() else 0
            obj, _ = CostoProducto.objects.get_or_create(producto=p)
            if obj.costo_unidad != costo:
                obj.costo_unidad = costo
                obj.save(update_fields=["costo_unidad"])
        messages.success(request, "Costos por unidad guardados.")
        return redirect("gestion:costos")

    costos_map = {c.producto_id: c.costo_unidad for c in CostoProducto.objects.all()}
    filas = [{"p": p, "costo": costos_map.get(p.id, 0)} for p in productos]
    return render(request, "gestion/costos.html", {"filas": filas})


# ----------------------------------------------------------------------------
# Compra a granel repartida entre pedidos (C)
# ----------------------------------------------------------------------------
def compra_granel(request):
    """Registra una compra grande y la reparte entre los pedidos elegidos,
    proporcional a las unidades que produce cada uno (crea una Compra por pedido)."""
    pedidos = (
        Pedido.objects.exclude(estado=Pedido.CANCELADO)
        .select_related("cliente")
        .prefetch_related("items__componentes")
        .order_by("-fecha_pedido", "-id")
    )
    if request.method == "POST":
        ids = request.POST.getlist("pedidos")
        seleccionados = [p for p in pedidos if str(p.pk) in ids]
        try:
            monto = int(request.POST.get("monto", "0"))
        except ValueError:
            monto = 0
        detalle = request.POST.get("detalle", "").strip()
        proveedor = request.POST.get("proveedor", "").strip()
        fecha_str = request.POST.get("fecha", "")
        try:
            fecha = date.fromisoformat(fecha_str) if fecha_str else timezone.localdate()
        except ValueError:
            fecha = timezone.localdate()

        if not seleccionados or monto <= 0:
            messages.error(request, "Elige al menos un pedido y un monto válido.")
            return redirect("gestion:compra_granel")

        unidades = {p.pk: p.total_unidades for p in seleccionados}
        total_u = sum(unidades.values())
        n = len(seleccionados)

        repartos = {}
        acumulado = 0
        for i, p in enumerate(seleccionados):
            if i < n - 1:
                if total_u > 0:
                    parte = round(monto * unidades[p.pk] / total_u)
                else:
                    parte = monto // n
                repartos[p.pk] = parte
                acumulado += parte
            else:
                repartos[p.pk] = monto - acumulado  # el resto al último (cuadra el total)

        for p in seleccionados:
            Compra.objects.create(
                pedido=p,
                proveedor=proveedor,
                detalle=f"Granel: {detalle}" if detalle else "Compra a granel",
                monto=repartos[p.pk],
                fecha=fecha,
            )
        messages.success(request, f"Compra a granel de ${monto:,} repartida en {n} pedidos.".replace(",", "."))
        return redirect("gestion:pedidos")

    return render(request, "gestion/compra_granel.html", {"pedidos": pedidos, "hoy": timezone.localdate()})


# ----------------------------------------------------------------------------
# Web: como le va a la tienda online
# ----------------------------------------------------------------------------
def web(request):
    """Numeros de la tienda web en el panel, sin tener que abrir Analytics.

    Todo sale de lo que la web ya guarda (pedidos, lineas, clics de /links):
    es exacto y en tiempo real. Las visitas, el origen y los mapas de calor
    viven en GA4 y Clarity; aqui van los accesos directos y si estan
    configurados.
    """
    from datetime import timedelta

    from django.conf import settings
    from django.db.models import Count, F, Sum

    from BebesitaAPP.links import resumen_clics
    from BebesitaAPP.models import ClicEnlace
    from BebesitaAPP.models import Pedido as PedidoWeb
    from BebesitaAPP.models import PedidoItem as PedidoItemWeb

    try:
        dias = int(request.GET.get("dias", 7))
    except ValueError:
        dias = 7
    if dias not in (1, 7, 30, 90):
        dias = 7
    ahora = timezone.now()
    desde = ahora - timedelta(days=dias)

    pedidos = PedidoWeb.objects.filter(creado__gte=desde)
    n_pedidos = pedidos.count()
    ventas = int(pedidos.aggregate(t=Sum("total"))["t"] or 0)
    cajas_box = int(pedidos.aggregate(c=Sum("cantidad_cajas"))["c"] or 0)

    top = (PedidoItemWeb.objects.filter(pedido__creado__gte=desde)
           .values("producto__nombre", "detalle")
           .annotate(unidades=Sum("cantidad"), monto=Sum(F("cantidad") * F("precio")))
           .order_by("-unidades")[:6])

    clics = resumen_clics(dias)
    total_clics = sum(n for _, n in clics)
    nombres = {"pedido": "Haz tu pedido", "whatsapp": "WhatsApp", "box": "Arma tu box",
               "corporativo": "Corporativos", "delivery": "Despacho y retiro", "instagram": "Instagram"}
    clics_filas = []
    for slug, n in clics:
        if slug.startswith("p") and slug[1:].isdigit():
            prod = Producto.objects.filter(pk=int(slug[1:])).first()
            etiqueta = prod.nombre if prod else slug
        else:
            etiqueta = nombres.get(slug, slug)
        clics_filas.append({"etiqueta": etiqueta, "n": n, "pct": round(n * 100 / total_clics) if total_clics else 0})

    sitio = getattr(settings, "SITE_URL", "https://dulcecita.cl")
    herramientas = [
        {"nombre": "Google Analytics 4", "para": "Visitas en tiempo real, de dónde llegan y qué compran",
         "ok": bool(settings.GA4_ID), "url": "https://analytics.google.com/analytics/web/#/realtime", "falta": "GA4_ID"},
        {"nombre": "Microsoft Clarity", "para": "Mapas de calor y grabaciones de cómo navegan",
         "ok": bool(settings.CLARITY_ID), "url": "https://clarity.microsoft.com/projects", "falta": "CLARITY_ID"},
        {"nombre": "Google Search Console", "para": "Qué buscan en Google para llegar y en qué posición sale",
         "ok": bool(settings.GOOGLE_SITE_VERIFICATION),
         "url": f"https://search.google.com/search-console?resource_id={quote(sitio + '/', safe='')}", "falta": "GOOGLE_SITE_VERIFICATION"},
        {"nombre": "Pixel de Meta", "para": "Ventas y contactos que vienen de anuncios en Instagram",
         "ok": bool(settings.META_PIXEL_ID), "url": "https://business.facebook.com/events_manager2", "falta": "META_PIXEL_ID"},
        {"nombre": "PageSpeed Insights", "para": "Velocidad del sitio en celular (Core Web Vitals)",
         "ok": True, "url": f"https://pagespeed.web.dev/analysis?url={quote(sitio + '/', safe='')}", "falta": ""},
        {"nombre": "Prueba de resultados enriquecidos", "para": "Que Google lea bien productos y precios",
         "ok": True, "url": f"https://search.google.com/test/rich-results?url={quote(sitio + '/productos/', safe='')}", "falta": ""},
    ]

    context = {
        "dias": dias,
        "opciones_dias": [(1, "Hoy"), (7, "7 días"), (30, "30 días"), (90, "90 días")],
        "n_pedidos": n_pedidos,
        "ventas": ventas,
        "ticket": round(ventas / n_pedidos) if n_pedidos else 0,
        "cajas_box": cajas_box,
        "pedidos_hoy": PedidoWeb.objects.filter(creado__date=timezone.localdate()).count(),
        "top": top,
        "clics_filas": clics_filas,
        "total_clics": total_clics,
        "clics_hoy": ClicEnlace.objects.filter(creado__date=timezone.localdate()).count(),
        "ultimos": PedidoWeb.objects.order_by("-creado")[:6],
        "herramientas": herramientas,
        "sitio": sitio,
    }
    return render(request, "gestion/web.html", context)
