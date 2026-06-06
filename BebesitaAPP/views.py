from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .email_utils import send_checkout_emails, send_contact_email, send_corporate_email
from .forms import CheckoutForm, ContactoForm, CorporativoForm
from .models import (
    BeneficioDiferencial,
    CampanaEspecial,
    CategoriaProducto,
    Pedido,
    PedidoItem,
    PreguntaFrecuente,
    Producto,
    Testimonio,
)


def _get_cart(request):
    """Obtiene el carrito de sesion con cantidades enteras positivas."""
    raw_cart = request.session.get("cart", {})
    cart = {}
    for pid, qty in raw_cart.items():
        try:
            pid_str = str(int(pid))
            qty_int = int(qty)
        except (TypeError, ValueError):
            continue
        if qty_int > 0:
            cart[pid_str] = qty_int
    return cart


def _save_cart(request, cart):
    request.session["cart"] = cart
    request.session.modified = True


def _get_products_map(cart):
    product_ids = [int(pid) for pid in cart.keys()]
    return Producto.objects.in_bulk(product_ids)


def _build_cart_items(cart):
    products_map = _get_products_map(cart)
    items = []
    total = 0

    for pid, cantidad in cart.items():
        producto = products_map.get(int(pid))
        if not producto:
            continue
        subtotal = producto.precio * cantidad
        total += subtotal
        items.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "subtotal": subtotal,
            }
        )

    return items, total


def _format_money(value):
    amount = Decimal(value or 0)
    return f"${amount:,.0f}".replace(",", ".")


def _shipping_cost_for_delivery(delivery_type):
    if delivery_type == CheckoutForm.TIPO_ENTREGA_DESPACHO:
        return int(getattr(settings, "SHIPPING_COST", 0))
    return 0


def _build_order_whatsapp_url(pedido):
    base_url = getattr(settings, "WHATSAPP_URL", "").strip()
    if not base_url:
        return ""

    delivery_label = "Retiro en punto" if pedido.tipo_entrega == Pedido.TIPO_ENTREGA_RETIRO else "Despacho a domicilio"
    message = (
        f"Hola {settings.BRAND_NAME}, acabo de realizar el pedido #{pedido.id}. "
        f"Quedo atento para coordinar {delivery_label.lower()}."
    )
    parsed = urlparse(base_url)
    query = dict(parse_qsl(parsed.query))
    query["text"] = message
    return urlunparse(parsed._replace(query=urlencode(query)))


def home(request):
    destacados = Producto.objects.filter(visible=True, destacado=True).select_related("categoria")[:4]
    if not destacados:
        destacados = Producto.objects.filter(visible=True).select_related("categoria")[:4]

    # Slides del hero (carrusel): destacados con imagen
    hero_items = [p for p in destacados if p.imagen][:4]
    # Grilla "Nuestros productos"
    grilla = Producto.objects.filter(visible=True).select_related("categoria")[:12]

    beneficios = BeneficioDiferencial.objects.filter(activo=True)[:4]
    testimonios = Testimonio.objects.filter(activo=True, destacado=True)[:3]
    faqs = PreguntaFrecuente.objects.filter(activa=True)[:6]
    campanas = CampanaEspecial.objects.filter(activa=True)[:2]

    return render(
        request,
        "home.html",
        {
            "destacados": destacados,
            "hero_items": hero_items,
            "grilla": grilla,
            "beneficios": beneficios,
            "testimonios": testimonios,
            "faqs": faqs,
            "campanas": campanas,
        },
    )


def productos(request):
    productos_qs = Producto.objects.filter(visible=True).select_related("categoria")
    categorias = CategoriaProducto.objects.filter(activa=True)

    query = (request.GET.get("q") or "").strip()
    categoria_slug = (request.GET.get("categoria") or "").strip()
    solo_destacados = (request.GET.get("destacados") or "").strip() == "1"

    if query:
        productos_qs = productos_qs.filter(nombre__icontains=query)
    if categoria_slug:
        productos_qs = productos_qs.filter(categoria__slug=categoria_slug)
    if solo_destacados:
        productos_qs = productos_qs.filter(destacado=True)

    productos_qs = productos_qs.order_by("orden", "nombre")

    return render(
        request,
        "productos.html",
        {
            "productos": productos_qs,
            "categorias": categorias,
            "filtro_q": query,
            "filtro_categoria": categoria_slug,
            "filtro_destacados": solo_destacados,
        },
    )


def corporativo(request):
    if request.method == "POST":
        form = CorporativoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            sent = send_corporate_email(data)
            if sent:
                messages.success(request, "Tu solicitud fue enviada. Te contactaremos pronto.")
                return redirect("corporativo")
            messages.error(
                request,
                "No pudimos enviar tu solicitud ahora. Intenta nuevamente o escríbenos al correo comercial.",
            )
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        form = CorporativoForm()

    return render(request, "corporativo.html", {"form": form})


def contacto(request):
    if request.method == "POST":
        form = ContactoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            sent = send_contact_email(data)
            if sent:
                messages.success(request, "Tu mensaje fue enviado. Te responderemos pronto.")
                return redirect("contacto")
            messages.error(
                request,
                "No pudimos enviar tu mensaje ahora. Intenta nuevamente o escríbenos al correo comercial.",
            )
        else:
            messages.error(request, "Corrige los campos marcados y vuelve a intentar.")
    else:
        form = ContactoForm()

    return render(request, "contacto.html", {"form": form})


def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    if not producto.visible or not producto.disponible:
        messages.error(request, "Este producto no está disponible por ahora.")
        return redirect("productos")
    cart = _get_cart(request)
    pid = str(producto_id)
    cart[pid] = cart.get(pid, 0) + 1
    _save_cart(request, cart)
    return redirect("carrito")


def mostrar_carrito(request):
    cart = _get_cart(request)
    productos, total = _build_cart_items(cart)
    return render(request, "carrito.html", {"productos": productos, "total": total})


def checkout(request):
    cart = _get_cart(request)
    if not cart:
        return redirect("carrito")

    productos, subtotal = _build_cart_items(cart)
    if not productos:
        _save_cart(request, {})
        messages.error(request, "Algunos productos ya no están disponibles. Tu carrito fue actualizado.")
        return redirect("carrito")

    current_delivery_type = CheckoutForm.TIPO_ENTREGA_RETIRO
    if request.method == "POST":
        current_delivery_type = request.POST.get("tipo_entrega") or CheckoutForm.TIPO_ENTREGA_RETIRO
    shipping_cost = _shipping_cost_for_delivery(current_delivery_type)
    total = subtotal + shipping_cost

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            shipping_cost = _shipping_cost_for_delivery(data["tipo_entrega"])
            total = subtotal + shipping_cost
            pedido = Pedido.objects.create(
                nombre_cliente=data["nombre"],
                email_cliente=data["email"],
                telefono=data["telefono"],
                tipo_entrega=data["tipo_entrega"],
                comuna_sector=data["comuna_sector"],
                direccion=data["direccion"],
                costo_despacho=shipping_cost,
                total=total,
            )

            for item in productos:
                PedidoItem.objects.create(
                    pedido=pedido,
                    producto=item["producto"],
                    cantidad=item["cantidad"],
                    precio=item["producto"].precio,
                )

            delivery = send_checkout_emails(pedido=pedido, items=productos)
            if not (delivery["customer_ok"] and delivery["internal_ok"]):
                messages.warning(request, "Tu pedido fue guardado, pero hubo un problema al enviar correos.")

            _save_cart(request, {})
            return redirect("checkout_exito", pedido_id=pedido.id)
        messages.error(request, "Revisa los campos del formulario para continuar.")
    else:
        form = CheckoutForm(initial={"tipo_entrega": CheckoutForm.TIPO_ENTREGA_RETIRO})

    return render(
        request,
        "checkout.html",
        {
            "productos": productos,
            "subtotal": subtotal,
            "shipping_cost": shipping_cost,
            "total": total,
            "pickup_point_label": getattr(settings, "PICKUP_POINT_LABEL", ""),
            "form": form,
        },
    )


def checkout_exito(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    delivery_label = "Retiro en punto" if pedido.tipo_entrega == Pedido.TIPO_ENTREGA_RETIRO else "Despacho a domicilio"
    context = {
        "pedido_id": pedido.id,
        "pedido": pedido,
        "delivery_label": delivery_label,
        "shipping_cost_formatted": _format_money(pedido.costo_despacho),
        "total_formatted": _format_money(pedido.total),
        "whatsapp_order_url": _build_order_whatsapp_url(pedido),
    }
    return render(request, "checkout_exito.html", context)


def quitar_carrito(request, producto_id):
    cart = _get_cart(request)
    pid = str(producto_id)
    if pid in cart:
        if cart[pid] > 1:
            cart[pid] -= 1
        else:
            del cart[pid]
        _save_cart(request, cart)
    return redirect("carrito")


@require_POST
def agregar_carrito_ajax(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    if not producto.visible or not producto.disponible:
        return JsonResponse({"ok": False, "error": "Producto no disponible"}, status=400)
    cart = _get_cart(request)
    pid = str(producto_id)
    cart[pid] = cart.get(pid, 0) + 1
    _save_cart(request, cart)

    productos, total = _build_cart_items(cart)
    item_subtotal = 0
    qty = cart.get(pid, 0)
    for item in productos:
        if item["producto"].id == producto_id:
            item_subtotal = item["subtotal"]
            break

    return JsonResponse(
        {
            "ok": True,
            "cart_count": sum(cart.values()),
            "qty": qty,
            "item_subtotal": float(item_subtotal),
            "total": float(total),
        }
    )


@require_POST
def decrementar_carrito_ajax(request, producto_id):
    cart = _get_cart(request)
    pid = str(producto_id)
    if pid in cart:
        if cart[pid] > 1:
            cart[pid] -= 1
        else:
            del cart[pid]
        _save_cart(request, cart)

    productos, total = _build_cart_items(cart)
    qty = cart.get(pid, 0)
    item_subtotal = 0
    for item in productos:
        if item["producto"].id == producto_id:
            item_subtotal = item["subtotal"]
            break

    return JsonResponse(
        {
            "ok": True,
            "cart_count": sum(cart.values()),
            "qty": qty,
            "item_subtotal": float(item_subtotal),
            "total": float(total),
        }
    )


def carrito_json(request):
    cart = _get_cart(request)
    return JsonResponse({"ok": True, "cart": cart, "cart_count": sum(cart.values())})


@require_POST
def eliminar_carrito_ajax(request, producto_id):
    cart = _get_cart(request)
    cart.pop(str(producto_id), None)
    _save_cart(request, cart)

    _, total = _build_cart_items(cart)
    return JsonResponse(
        {
            "ok": True,
            "cart_count": sum(cart.values()),
            "qty": 0,
            "item_subtotal": 0,
            "total": float(total),
        }
    )


def producto_detalle(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    imagenes = getattr(producto, "imagenes", None)
    ctx = {"p": producto, "imagenes": imagenes.all() if imagenes else []}

    if request.GET.get("modal") == "1":
        return render(request, "partials/producto_detalle.html", ctx)
    return render(request, "producto_detalle_page.html", ctx)

