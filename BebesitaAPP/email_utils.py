import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _clean_recipients(recipients):
    return [email.strip() for email in recipients if email and email.strip()]


def _format_money(value):
    amount = Decimal(value or 0)
    return f"${amount:,.0f}".replace(",", ".")


def send_plain_notification(subject, body, recipients, reply_to=None):
    clean_recipients = _clean_recipients(recipients)
    if not clean_recipients:
        logger.error("No hay destinatarios para enviar correo: %s", subject)
        return False

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=clean_recipients,
            reply_to=reply_to or None,
        )
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception(
            "Fallo envio de correo. asunto=%s destinatarios=%s backend=%s",
            subject,
            clean_recipients,
            settings.EMAIL_BACKEND,
        )
        return False


def send_templated_email(subject, recipients, text_template, html_template, context, reply_to=None):
    clean_recipients = _clean_recipients(recipients)
    if not clean_recipients:
        logger.error("No hay destinatarios para correo HTML: %s", subject)
        return False

    try:
        text_body = render_to_string(text_template, context)
        html_body = render_to_string(html_template, context)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=clean_recipients,
            reply_to=reply_to or None,
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception(
            "Fallo envio de correo HTML. asunto=%s destinatarios=%s backend=%s",
            subject,
            clean_recipients,
            settings.EMAIL_BACKEND,
        )
        return False


def send_checkout_emails(pedido, items):
    line_items = []
    subtotal = Decimal("0")
    for item in items:
        producto = item["producto"]
        cantidad = item["cantidad"]
        subtotal += Decimal(item["subtotal"])
        line_items.append(
            {
                "nombre": producto.nombre,
                "cantidad": cantidad,
                "subtotal": _format_money(item["subtotal"]),
                "precio_unitario": _format_money(producto.precio),
            }
        )

    delivery_label = "Retiro en punto" if pedido.tipo_entrega == pedido.TIPO_ENTREGA_RETIRO else "Despacho a domicilio"
    context = {
        "site_brand": getattr(settings, "BRAND_NAME", "Dulcecitaa"),
        "pedido": pedido,
        "line_items": line_items,
        "subtotal_formatted": _format_money(subtotal),
        "shipping_formatted": _format_money(pedido.costo_despacho),
        "total_formatted": _format_money(pedido.total),
        "delivery_label": delivery_label,
        "contact_email": getattr(settings, "CONTACT_EMAIL", ""),
        "whatsapp_url": getattr(settings, "WHATSAPP_URL", ""),
        "website_url": getattr(settings, "WEBSITE_URL", ""),
    }

    customer_subject = f"Confirmacion de pedido #{pedido.id} | {context['site_brand']}"
    internal_subject = f"Nuevo pedido #{pedido.id} | {context['site_brand']}"

    customer_ok = send_templated_email(
        subject=customer_subject,
        recipients=[pedido.email_cliente],
        text_template="emails/pedido_cliente.txt",
        html_template="emails/pedido_cliente.html",
        context=context,
        reply_to=[getattr(settings, "CONTACT_EMAIL", "")],
    )
    internal_ok = send_templated_email(
        subject=internal_subject,
        recipients=[getattr(settings, "CONTACT_EMAIL", "")],
        text_template="emails/pedido_negocio.txt",
        html_template="emails/pedido_negocio.html",
        context=context,
        reply_to=[pedido.email_cliente],
    )
    return {"customer_ok": customer_ok, "internal_ok": internal_ok}


def send_contact_email(data):
    context = {
        "site_brand": getattr(settings, "BRAND_NAME", "Dulcecitaa"),
        "nombre": data["nombre"],
        "email": data["email"],
        "mensaje": data["mensaje"],
        "contact_email": getattr(settings, "CONTACT_EMAIL", ""),
        "website_url": getattr(settings, "WEBSITE_URL", ""),
    }
    subject = f"Contacto Web - {data['nombre']}"
    return send_templated_email(
        subject=subject,
        recipients=[getattr(settings, "CONTACT_EMAIL", "")],
        text_template="emails/contacto.txt",
        html_template="emails/contacto.html",
        context=context,
        reply_to=[data["email"]],
    )


def send_corporate_email(data):
    context = {
        "site_brand": getattr(settings, "BRAND_NAME", "Dulcecitaa"),
        "nombre": data["nombre"],
        "empresa": data["empresa"],
        "email": data["email"],
        "telefono": data["telefono"],
        "mensaje": data["mensaje"],
        "contact_email": getattr(settings, "CONTACT_EMAIL", ""),
        "website_url": getattr(settings, "WEBSITE_URL", ""),
    }
    subject = f"Solicitud Corporativa - {data['empresa']}"
    return send_templated_email(
        subject=subject,
        recipients=[getattr(settings, "CONTACT_EMAIL", "")],
        text_template="emails/corporativo.txt",
        html_template="emails/corporativo.html",
        context=context,
        reply_to=[data["email"]],
    )
