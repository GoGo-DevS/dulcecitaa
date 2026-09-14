from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .email_utils import send_checkout_emails, send_contact_email, send_corporate_email
from .forms import CheckoutForm, ContactoForm, CorporativoForm
from .models import (
    BeneficioDiferencial,
    CampanaEspecial,
    CategoriaProducto,
    Opcion,
    Pedido,
    PedidoItem,
    PreguntaFrecuente,
    Producto,
    Testimonio,
)


def _parse_linea(linea):
    """'15-3-8' -> (15, (3, 8)): producto 15 con las opciones 3 y 8.

    El carrito se indexa por LINEA y no por producto: diez alfajores de
    chocolate y diez de chocolate blanco son dos lineas del mismo producto.
    Un carrito viejo, con claves "15", sigue valiendo (linea sin opciones).
    """
    try:
        partes = [int(x) for x in str(linea).split("-")]
    except (TypeError, ValueError):
        return None
    if not partes or any(x <= 0 for x in partes):
        return None
    return partes[0], tuple(sorted(set(partes[1:])))


def _clave_linea(pid, opcion_ids=()):
    return "-".join(str(x) for x in [pid, *sorted(opcion_ids)])


def _resolver_linea(linea):
    """Valida lo que pide el cliente contra lo que el producto ofrece.

    Devuelve (producto, clave normalizada) o (None, None). Una opcion que el
    producto no ofrece invalida la linea; un grupo sin elegir (el enlace
    "Agregar y ver carrito" no manda nada) toma la primera opcion del grupo,
    que es la misma que la tarjeta muestra marcada.
    """
    parsed = _parse_linea(linea)
    if not parsed:
        return None, None
    pid, pedidas = parsed
    producto = Producto.objects.filter(pk=pid).prefetch_related("opciones").first()
    if not producto:
        return None, None
    ofrecidas = {op.id: op for op in producto.opciones.all() if op.activa}
    if any(oid not in ofrecidas for oid in pedidas):
        return None, None
    elegidas = [ofrecidas[oid] for oid in pedidas]
    tipos = [op.tipo for op in elegidas]
    if len(tipos) != len(set(tipos)):
        return None, None  # dos coberturas en la misma linea
    for tipo, _etiqueta, opciones in producto.grupos_opciones():
        if tipo not in tipos:
            elegidas.append(opciones[0])
    return producto, _clave_linea(pid, [op.id for op in elegidas])


def _clave_o_vacia(linea):
    parsed = _parse_linea(linea)
    return _clave_linea(*parsed) if parsed else ""


def _get_cart(request):
    """Obtiene el carrito de sesion con cantidades enteras positivas."""
    raw_cart = request.session.get("cart", {})
    cart = {}
    for linea, qty in raw_cart.items():
        parsed = _parse_linea(linea)
        try:
            qty_int = int(qty)
        except (TypeError, ValueError):
            continue
        if parsed and qty_int > 0:
            cart[_clave_linea(*parsed)] = qty_int
    return cart


def _minimo():
    """Unidades minimas por producto. La venta es por volumen."""
    return max(1, int(getattr(settings, "MINIMO_UNIDADES", 1)))


def _sumar_al_carrito(cart, pid):
    """Un producto entra al carrito CON el minimo puesto, no de a uno.

    Si entrara con 1, el cliente veria "1" en el carrito y recien se enteraria
    del minimo al pagar. Entrar ya en el minimo hace visible la regla en el
    momento en que agrega.
    """
    minimo = _minimo()
    cart[pid] = max(minimo, cart.get(pid, 0) + 1)
    return cart[pid]


def _restar_del_carrito(cart, pid):
    """Bajar del minimo saca el producto: no existe un carrito con 9."""
    if pid not in cart:
        return 0
    if cart[pid] - 1 >= _minimo():
        cart[pid] -= 1
        return cart[pid]
    del cart[pid]
    return 0


def _save_cart(request, cart):
    request.session["cart"] = cart
    request.session.modified = True


def _build_cart_items(cart):
    lineas = {clave: _parse_linea(clave) for clave in cart}
    products_map = Producto.objects.in_bulk([pid for pid, _ in lineas.values()])
    opciones_map = Opcion.objects.in_bulk([oid for _, ops in lineas.values() for oid in ops])
    items = []
    total = 0

    for clave, cantidad in cart.items():
        pid, opcion_ids = lineas[clave]
        producto = products_map.get(pid)
        opciones = [opciones_map[oid] for oid in opcion_ids if oid in opciones_map]
        if not producto or len(opciones) != len(opcion_ids):
            continue
        precio_unitario = producto.precio + sum(op.recargo for op in opciones)
        subtotal = precio_unitario * cantidad
        total += subtotal
        items.append(
            {
                "linea": clave,
                "producto": producto,
                "opciones": opciones,
                "detalle": " · ".join(f"{op.get_tipo_display()}: {op.nombre}" for op in opciones),
                "precio_unitario": precio_unitario,
                "cantidad": cantidad,
                "subtotal": subtotal,
            }
        )

    return items, total


def _subtotal_de(productos, clave):
    return next((item["subtotal"] for item in productos if item["linea"] == clave), 0)


def _format_money(value):
    amount = Decimal(value or 0)
    return f"${amount:,.0f}".replace(",", ".")


def _shipping_cost_for_delivery(delivery_type):
    if delivery_type == CheckoutForm.TIPO_ENTREGA_DESPACHO:
        return int(getattr(settings, "SHIPPING_COST", 0))
    return 0


def _box_cost_for(cantidad_cajas):
    return int(getattr(settings, "BOX_PRICE", 0)) * cantidad_cajas


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


@ensure_csrf_cookie
def home(request):
    destacados = Producto.objects.filter(visible=True, destacado=True, variante_de__isnull=True).select_related("categoria")[:4]
    if not destacados:
        destacados = Producto.objects.filter(visible=True).select_related("categoria")[:4]

    # Slides del hero (carrusel): destacados con imagen
    hero_items = [p for p in destacados if p.imagen][:4]
    # Grilla "Nuestros productos"
    grilla = Producto.objects.filter(visible=True, variante_de__isnull=True).select_related("categoria")[:12]

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


@ensure_csrf_cookie
def productos(request):
    # Las variantes (la cobertura del alfajor, por ejemplo) no se listan
    # sueltas: se eligen dentro de la ficha de su producto principal. Si no,
    # el mismo alfajor aparece dos veces en el catalogo.
    productos_qs = (Producto.objects.filter(visible=True, variante_de__isnull=True)
                    .select_related("categoria")
                    .prefetch_related("opciones"))
    categorias = CategoriaProducto.objects.filter(activa=True, productos__visible=True).distinct()

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


def agregar_al_carrito(request, linea):
    producto, clave = _resolver_linea(linea)
    if not producto:
        raise Http404("Producto no encontrado")
    if not producto.visible or not producto.disponible:
        messages.error(request, "Este producto no está disponible por ahora.")
        return redirect("productos")
    cart = _get_cart(request)
    _sumar_al_carrito(cart, clave)
    _save_cart(request, cart)
    return redirect("carrito")


@ensure_csrf_cookie
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
    current_cantidad_cajas = 1
    if request.method == "POST":
        current_delivery_type = request.POST.get("tipo_entrega") or CheckoutForm.TIPO_ENTREGA_RETIRO
        try:
            current_cantidad_cajas = max(1, int(request.POST.get("cantidad_cajas") or 1))
        except ValueError:
            current_cantidad_cajas = 1
    shipping_cost = _shipping_cost_for_delivery(current_delivery_type)
    box_cost = _box_cost_for(current_cantidad_cajas)
    total = subtotal + shipping_cost + box_cost

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            shipping_cost = _shipping_cost_for_delivery(data["tipo_entrega"])
            box_cost = _box_cost_for(data["cantidad_cajas"])
            total = subtotal + shipping_cost + box_cost
            pedido = Pedido.objects.create(
                nombre_cliente=data["nombre"],
                email_cliente=data["email"],
                telefono=data["telefono"],
                tipo_entrega=data["tipo_entrega"],
                comuna_sector=data["comuna_sector"],
                direccion=data["direccion"],
                costo_despacho=shipping_cost,
                cantidad_cajas=data["cantidad_cajas"],
                costo_caja=box_cost,
                comentario_ocasion=data["comentario_ocasion"],
                total=total,
            )

            for item in productos:
                PedidoItem.objects.create(
                    pedido=pedido,
                    producto=item["producto"],
                    cantidad=item["cantidad"],
                    precio=item["precio_unitario"],
                    detalle=item["detalle"],
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
            "box_cost": box_cost,
            "box_price": getattr(settings, "BOX_PRICE", 0),
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
        "box_cost_formatted": _format_money(pedido.costo_caja),
        "total_formatted": _format_money(pedido.total),
        "whatsapp_order_url": _build_order_whatsapp_url(pedido),
    }
    return render(request, "checkout_exito.html", context)


def quitar_carrito(request, linea):
    cart = _get_cart(request)
    pid = _clave_o_vacia(linea)
    if pid in cart:
        _restar_del_carrito(cart, pid)
        _save_cart(request, cart)
    return redirect("carrito")


@require_POST
def agregar_carrito_ajax(request, linea):
    producto, pid = _resolver_linea(linea)
    if not producto:
        return JsonResponse({"ok": False, "error": "Producto no encontrado"}, status=404)
    if not producto.visible or not producto.disponible:
        return JsonResponse({"ok": False, "error": "Producto no disponible"}, status=400)
    cart = _get_cart(request)
    _sumar_al_carrito(cart, pid)
    _save_cart(request, cart)

    productos, total = _build_cart_items(cart)
    item_subtotal = _subtotal_de(productos, pid)
    qty = cart.get(pid, 0)

    return JsonResponse(
        {
            "ok": True,
            "linea": pid,
            "cart_count": sum(cart.values()),
            "qty": qty,
            "item_subtotal": float(item_subtotal),
            "total": float(total),
        }
    )


@require_POST
def decrementar_carrito_ajax(request, linea):
    cart = _get_cart(request)
    pid = _clave_o_vacia(linea)
    if pid in cart:
        _restar_del_carrito(cart, pid)
        _save_cart(request, cart)

    productos, total = _build_cart_items(cart)
    qty = cart.get(pid, 0)
    item_subtotal = _subtotal_de(productos, pid)

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
def eliminar_carrito_ajax(request, linea):
    cart = _get_cart(request)
    cart.pop(_clave_o_vacia(linea), None)
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


@ensure_csrf_cookie
def producto_detalle(request, pk):
    producto = get_object_or_404(Producto.objects.prefetch_related("opciones"), pk=pk)
    imagenes = getattr(producto, "imagenes", None)
    ctx = {"p": producto, "imagenes": imagenes.all() if imagenes else []}

    if request.GET.get("modal") == "1":
        return render(request, "partials/producto_detalle.html", ctx)
    return render(request, "producto_detalle_page.html", ctx)


def delivery(request):
    """Despacho y retiro.

    El menu tenia "Delivery y retiro" y "Contacto" apuntando los DOS a la
    misma pagina: dos opciones distintas que llevaban al mismo lugar.
    """
    return render(request, 'delivery.html')
