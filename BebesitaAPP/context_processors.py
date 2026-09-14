def cart_count(request):
    from .box import get_boxes, unidades
    from .views import _get_cart

    return {"cart_count": sum(_get_cart(request).values()) + unidades(get_boxes(request))}


def site_config(request):
    from django.conf import settings

    default_og_image = getattr(settings, "DEFAULT_OG_IMAGE", "")
    if default_og_image and not default_og_image.startswith("http"):
        default_og_image_url = request.build_absolute_uri(default_og_image)
    else:
        default_og_image_url = default_og_image

    return {
        "site_brand": getattr(settings, "BRAND_NAME", "Dulcecitaa"),
        "contact_email": getattr(settings, "CONTACT_EMAIL", ""),
        "whatsapp_url": getattr(settings, "WHATSAPP_URL", ""),
        "instagram_url": getattr(settings, "INSTAGRAM_URL", ""),
        "business_hours": getattr(settings, "BUSINESS_HOURS", ""),
        "minimo_unidades": getattr(settings, "MINIMO_UNIDADES", 1),
        "despacho_horas": getattr(settings, "DESPACHO_HORAS", 48),
        "transferencia": _transferencia(settings),
        "default_og_image_url": default_og_image_url,
    }


def _transferencia(settings):
    """Datos para transferir, o None si todavia no estan cargados."""
    datos = getattr(settings, "TRANSFERENCIA", {}) or {}
    return datos if datos.get("numero") else None
