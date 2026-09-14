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


def seo(request):
    """Dominio oficial, IDs de medicion y el schema del negocio para todas las paginas."""
    from django.conf import settings
    from .seo import schema_negocio

    site_url = getattr(settings, "SITE_URL", "https://dulcecita.cl")
    ids = {k: getattr(settings, k, "") for k in (
        "GA4_ID", "GTM_ID", "CLARITY_ID", "META_PIXEL_ID",
        "GOOGLE_SITE_VERIFICATION", "BING_SITE_VERIFICATION")}
    # Ni el admin ni el panel interno se miden: son la duena trabajando, no clientes.
    ruta = getattr(request, "path", "")
    medir = not (ruta.startswith("/admin") or ruta.startswith("/panel"))
    return {
        "site_url": site_url,
        "canonical_url": site_url + ruta,
        "medir": medir and any(ids[k] for k in ("GA4_ID", "GTM_ID", "CLARITY_ID", "META_PIXEL_ID")),
        "schema_negocio": schema_negocio(),
        **{k.lower(): v for k, v in ids.items()},
    }
