def cart_count(request):
    cart = request.session.get("cart", {})
    return {"cart_count": sum(cart.values())}


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
        "default_og_image_url": default_og_image_url,
    }
