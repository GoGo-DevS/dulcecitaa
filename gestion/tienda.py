"""El panel como el de una tienda online (15-11-2026, pedido de Diego).

- Inicio: como va la tienda (ventas de la semana contra la anterior, pedidos de
  hoy, lo ultimo que entro, lo mas pedido) y los accesos de todos los dias.
- Cada pedido de dulcecita.cl se abre DENTRO del panel. Antes la lista
  enlazaba a /admin/, que la duena no usa: veia que habia un pedido y no podia
  abrirlo.

Los pedidos web son de solo lectura aca: los crea el cliente al pagar y no
tienen estados que cambiar. Lo que la duena necesita es ver que pidieron,
a nombre de quien, como se entrega y escribirle por WhatsApp.
"""
import re
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, F, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from BebesitaAPP.models import Pedido as PedidoWeb
from BebesitaAPP.models import PedidoItem as PedidoItemWeb
from BebesitaAPP.models import Producto, Promocion


def whatsapp_del_cliente(pedido):
    """Enlace para escribirle al cliente del pedido, o "" si el telefono no sirve.

    El formulario acepta "+56 9 1234 5678", "912345678" o "9 1234 5678": se
    dejan solo los digitos y a un celular chileno sin codigo se le antepone 56.
    """
    digitos = re.sub(r"\D", "", pedido.telefono or "")
    if len(digitos) == 9 and digitos.startswith("9"):
        digitos = "56" + digitos
    if len(digitos) < 11:
        return ""
    nombre = (pedido.nombre_cliente or "").split(" ")[0]
    mensaje = f"Hola {nombre}, te escribo de {settings.BRAND_NAME} por tu pedido #{pedido.pk}."
    return f"https://wa.me/{digitos}?text={quote(mensaje)}"


def inicio_tienda(request):
    """El inicio del panel cuando se usa como tienda online."""
    from .views import _variacion

    ahora, hoy = timezone.now(), timezone.localdate()
    semana = PedidoWeb.objects.filter(creado__gte=ahora - timedelta(days=7))
    anterior = PedidoWeb.objects.filter(creado__gte=ahora - timedelta(days=14), creado__lt=ahora - timedelta(days=7))
    esta = semana.aggregate(pedidos=Count("id"), ventas=Sum("total"))
    antes = anterior.aggregate(pedidos=Count("id"), ventas=Sum("total"))
    ventas, ventas_antes = int(esta["ventas"] or 0), int(antes["ventas"] or 0)
    de_hoy = PedidoWeb.objects.filter(creado__date=hoy).aggregate(pedidos=Count("id"), ventas=Sum("total"))

    top = (PedidoItemWeb.objects.filter(pedido__creado__gte=ahora - timedelta(days=30))
           .values("producto__nombre")
           .annotate(unidades=Sum("cantidad"), monto=Sum(F("cantidad") * F("precio")))
           .order_by("-unidades")[:5])

    return render(request, "gestion/inicio_tienda.html", {
        "ventas": ventas,
        "pedidos": esta["pedidos"],
        "ticket": round(ventas / esta["pedidos"]) if esta["pedidos"] else 0,
        "ventas_antes": ventas_antes,
        "pedidos_antes": antes["pedidos"],
        "variacion": _variacion(ventas, ventas_antes),
        "pedidos_hoy": de_hoy["pedidos"],
        "ventas_hoy": int(de_hoy["ventas"] or 0),
        "productos_en_web": Producto.objects.filter(visible=True, variante_de__isnull=True).count(),
        "promo": Promocion.vigente(),
        "ultimos": PedidoWeb.objects.order_by("-creado")[:6],
        "total_pedidos": PedidoWeb.objects.count(),
        "top": top,
        "sitio": settings.SITE_URL,
    })


def ventas_lista(request):
    """Todos los pedidos de la tienda, el mas nuevo primero."""
    pagina = Paginator(PedidoWeb.objects.order_by("-creado"), 25).get_page(request.GET.get("pagina"))
    return render(request, "gestion/ventas_lista.html", {"pagina": pagina})


def venta_detalle(request, pk):
    pedido = get_object_or_404(PedidoWeb, pk=pk)
    lineas = [{"item": item, "subtotal": int(item.precio * item.cantidad)}
              for item in pedido.items.select_related("producto").order_by("id")]
    subtotal = sum(linea["subtotal"] for linea in lineas)
    return render(request, "gestion/venta_detalle.html", {
        "pedido": pedido,
        "lineas": lineas,
        "subtotal": subtotal,
        "unidades": sum(linea["item"].cantidad for linea in lineas),
        "whatsapp": whatsapp_del_cliente(pedido),
        "es_despacho": pedido.tipo_entrega == PedidoWeb.TIPO_ENTREGA_DESPACHO,
    })
