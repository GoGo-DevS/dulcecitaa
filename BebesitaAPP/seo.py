"""SEO tecnico de dulcecita.cl: datos estructurados, sitemap, robots y manifest.

Todo apunta al dominio oficial (settings.SITE_URL) aunque la visita llegue por
onrender.com: si no, Google indexa dos copias del sitio compitiendo entre si.

Los datos estructurados describen SOLO lo que la pagina muestra de verdad
(precios, productos, WhatsApp, Instagram). Un schema que promete algo que la
pagina no tiene es motivo de accion manual de Google.
"""
import json
import re

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from .models import Producto


def _abs(ruta):
    return settings.SITE_URL + ruta


def _telefono():
    """+56961192192 a partir del enlace de WhatsApp, o vacio."""
    numero = re.sub(r"\D", "", getattr(settings, "WHATSAPP_URL", "").split("?")[0])
    return f"+{numero}" if len(numero) >= 9 else ""


def json_ld(data):
    """Serializa para <script type="application/ld+json"> sin romper el HTML."""
    texto = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return mark_safe(texto.replace("</", "<\\/"))


def schema_negocio():
    """Bakery + WebSite, en todas las paginas."""
    negocio = {
        "@type": "Bakery",
        "@id": _abs("/#negocio"),
        "name": settings.BRAND_NAME,
        "url": _abs("/"),
        "logo": _abs(static("img/icono-512.png")),
        "image": _abs(static("img/sello-dulcecita.jpg")),
        "description": ("Repostería artesanal hecha a mano: alfajores, barquillos y cuchuflís "
                        "bañados en chocolate. Venta por volumen, box personalizados y regalos "
                        "corporativos con despacho a todo Chile."),
        "priceRange": "$",
        "currenciesAccepted": "CLP",
        "paymentAccepted": "Transferencia bancaria",
        "areaServed": {"@type": "Country", "name": "Chile"},
        "address": {"@type": "PostalAddress", "addressLocality": "Santiago",
                    "addressRegion": "Región Metropolitana", "addressCountry": "CL"},
        "sameAs": [u for u in [getattr(settings, "INSTAGRAM_URL", "")] if u],
    }
    if _telefono():
        negocio["telephone"] = _telefono()
    sitio = {
        "@type": "WebSite",
        "@id": _abs("/#sitio"),
        "url": _abs("/"),
        "name": settings.BRAND_NAME,
        "inLanguage": "es-CL",
        "publisher": {"@id": _abs("/#negocio")},
    }
    return json_ld({"@context": "https://schema.org", "@graph": [negocio, sitio]})


def _oferta(producto):
    return {
        "@type": "Offer",
        "url": _abs(producto.get_absolute_url()),
        "priceCurrency": "CLP",
        "price": str(producto.precio),
        "availability": "https://schema.org/InStock" if producto.disponible else "https://schema.org/OutOfStock",
        "itemCondition": "https://schema.org/NewCondition",
        "seller": {"@id": _abs("/#negocio")},
        "eligibleQuantity": {"@type": "QuantitativeValue", "minValue": settings.MINIMO_UNIDADES,
                             "unitText": "bolsita" if producto.unidades_por_pack > 1 else "unidad"},
        "shippingDetails": {
            "@type": "OfferShippingDetails",
            "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "CL"},
            "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "handlingTime": {"@type": "QuantitativeValue", "minValue": 2, "maxValue": 2, "unitCode": "DAY"},
            },
        },
    }


def schema_producto(producto, request=None):
    imagen = producto.imagen.url if producto.imagen else static("img/sello-dulcecita.jpg")
    if not imagen.startswith("http"):
        imagen = _abs(imagen)
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Product",
                "name": producto.nombre,
                "description": strip_tags(producto.descripcion)[:500],
                "image": [imagen],
                "brand": {"@type": "Brand", "name": settings.BRAND_NAME},
                "category": producto.categoria.nombre if producto.categoria_id else "Repostería",
                "offers": _oferta(producto),
            },
            migas([("Catálogo", reverse("productos")), (producto.nombre, producto.get_absolute_url())]),
        ],
    }
    return json_ld(data)


def schema_catalogo(productos):
    items = []
    for i, p in enumerate(productos, start=1):
        imagen = p.imagen.url if p.imagen else static("img/sello-dulcecita.jpg")
        items.append({
            "@type": "ListItem", "position": i,
            "item": {"@type": "Product", "name": p.nombre,
                     "url": _abs(p.get_absolute_url()),
                     "image": imagen if imagen.startswith("http") else _abs(imagen),
                     "offers": _oferta(p)},
        })
    return json_ld({"@context": "https://schema.org", "@graph": [
        {"@type": "ItemList", "name": f"Catálogo {settings.BRAND_NAME}", "itemListElement": items},
        migas([("Catálogo", reverse("productos"))]),
    ]})


def migas(tramos):
    """BreadcrumbList desde [(nombre, ruta)], siempre partiendo en Inicio."""
    todos = [("Inicio", "/")] + list(tramos)
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": nombre, "item": _abs(ruta)}
        for i, (nombre, ruta) in enumerate(todos, start=1)
    ]}


def schema_migas(*tramos):
    return json_ld({"@context": "https://schema.org", **migas(tramos)})


# --- sitemap.xml ---------------------------------------------------------

class _SitemapBase(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        return settings.SITE_URL.split("://", 1)[-1]


class PaginasSitemap(_SitemapBase):
    changefreq = "weekly"
    PAGINAS = [("home", 1.0), ("productos", 0.9), ("arma_tu_box", 0.8), ("corporativo", 0.8),
               ("delivery", 0.6), ("contacto", 0.5), ("links", 0.4)]

    def items(self):
        return [nombre for nombre, _ in self.PAGINAS]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return dict(self.PAGINAS)[item]


class ProductosSitemap(_SitemapBase):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Producto.objects.filter(visible=True, variante_de__isnull=True).order_by("orden", "pk")

    def location(self, producto):
        return producto.get_absolute_url()


SITEMAPS = {"paginas": PaginasSitemap, "productos": ProductosSitemap}


def robots_txt(request):
    lineas = [
        "User-agent: *",
        "Allow: /",
        # Paginas que no deben aparecer en Google: privadas, del proceso de
        # compra (cambian con cada visita) o redirecciones de conteo.
        "Disallow: /admin/",
        "Disallow: /panel/",
        "Disallow: /carrito/",
        "Disallow: /checkout/",
        "Disallow: /links/ir/",
        "",
        f"Sitemap: {settings.SITE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lineas) + "\n", content_type="text/plain; charset=utf-8")


def manifest(request):
    """Web app manifest: icono y color al guardar el sitio en el telefono."""
    return JsonResponse({
        "name": f"{settings.BRAND_NAME} Bakery",
        "short_name": settings.BRAND_NAME,
        "start_url": "/?utm_source=pwa",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#2a4057",
        "lang": "es-CL",
        "icons": [
            {"src": static("img/icono-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("img/icono-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("img/icono-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }, json_dumps_params={"ensure_ascii": False}, content_type="application/manifest+json")
