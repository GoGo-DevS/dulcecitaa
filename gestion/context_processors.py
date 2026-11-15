from django.conf import settings


def panel(request):
    """Si el panel muestra las cotizaciones corporativas ("Pedidos" y "Clientes").

    15-11-2026: ocultas "de momento" (pedido de Diego), para que el panel se use
    como el de una tienda online. Se ocultan del menu y del inicio; las pantallas
    y los datos siguen existiendo. Ver PANEL_VENTA_CORPORATIVA en settings.
    """
    return {"panel_corporativo": bool(getattr(settings, "PANEL_VENTA_CORPORATIVA", False))}
