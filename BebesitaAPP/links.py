"""dulcecita.cl/links: la pagina de la bio de Instagram.

Cada boton pasa por /links/ir/<slug>/, que anota el clic y redirige. Los
destinos salen de una lista fija armada aqui: el slug no es una URL, asi que
no se puede usar la redireccion para mandar gente a otro sitio.
"""
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings
from django.db.models import Count
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from . import box as arma_box
from .models import ClicEnlace, Producto

UTM = {"utm_source": "instagram", "utm_medium": "bio", "utm_campaign": "links"}


def _con_parametros(url, extra):
    partes = urlparse(url)
    query = dict(parse_qsl(partes.query))
    query.update(extra)
    return urlunparse(partes._replace(query=urlencode(query)))


def _whatsapp():
    base = getattr(settings, "WHATSAPP_URL", "").strip()
    if not base:
        return ""
    texto = f"Hola {settings.BRAND_NAME}! Vengo de Instagram y quiero hacer un pedido"
    return _con_parametros(base, {"text": texto})


def _destinos():
    """slug -> (url, externo). Los internos llevan UTM; los externos no."""
    destinos = {
        "pedido": (reverse("productos"), False),
        "box": (reverse("arma_tu_box"), False),
        "corporativo": (reverse("corporativo"), False),
        "delivery": (reverse("delivery"), False),
        "whatsapp": (_whatsapp(), True),
        "instagram": (getattr(settings, "INSTAGRAM_URL", ""), True),
    }
    return {slug: d for slug, d in destinos.items() if d[0]}


def links(request):
    instagram = getattr(settings, "INSTAGRAM_URL", "")
    usuario_ig = urlparse(instagram).path.strip("/") if instagram else ""
    return render(request, "links.html", {
        "destinos": _destinos(),
        "usuario_ig": usuario_ig,
        "precio_caja": arma_box.precio_caja(),
        "minimo_box": arma_box.minimo_box(),
    })


def links_ir(request, slug):
    destinos = _destinos()
    if slug in destinos:
        url, externo = destinos[slug]
    elif slug.startswith("p") and slug[1:].isdigit():
        producto = Producto.objects.filter(pk=int(slug[1:]), visible=True).first()
        if not producto:
            raise Http404("Producto no encontrado")
        url, externo = reverse("producto_detalle", args=[producto.pk]), False
    else:
        raise Http404("Enlace no encontrado")

    # Los bots que revisan enlaces (vista previa de WhatsApp, Instagram) no
    # son personas: si se contaran, cada vez que alguien comparte la pagina
    # sumaria clics falsos.
    agente = request.META.get("HTTP_USER_AGENT", "").lower()
    if request.method == "GET" and not any(b in agente for b in ("bot", "facebookexternalhit", "whatsapp", "preview", "crawler", "spider")):
        ClicEnlace.objects.create(slug=slug)

    return redirect(url if externo else _con_parametros(url, UTM))


def resumen_clics(dias=30):
    """[(slug, clics)] de los ultimos dias, para el admin."""
    desde = timezone.now() - timedelta(days=dias)
    return list(ClicEnlace.objects.filter(creado__gte=desde)
                .values_list("slug").annotate(n=Count("id")).order_by("-n"))
