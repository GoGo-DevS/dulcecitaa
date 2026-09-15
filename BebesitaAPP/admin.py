from django.contrib import admin
from django.utils.html import format_html

from .models import (
    BeneficioDiferencial,
    CampanaEspecial,
    CategoriaProducto,
    ClicEnlace,
    Opcion,
    PrecioCombinacion,
    Pedido,
    PedidoItem,
    PreguntaFrecuente,
    Producto,
    ProductoImagen,
    Testimonio,
)


class ProductoImagenInline(admin.TabularInline):
    model = ProductoImagen
    extra = 1
    readonly_fields = ("preview",)
    fields = ("imagen", "preview")

    def preview(self, obj):
        if not obj or not obj.imagen:
            return "-"
        return format_html('<img src="{}" style="height:64px;width:64px;object-fit:cover;border-radius:8px;" />', obj.imagen.url)

    preview.short_description = "Preview"


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden", "activa")
    list_editable = ("orden", "activa")
    search_fields = ("nombre", "slug")
    list_filter = ("activa",)
    ordering = ("orden", "nombre")
    prepopulated_fields = {"slug": ("nombre",)}


class PrecioCombinacionInline(admin.TabularInline):
    model = PrecioCombinacion
    extra = 0
    filter_horizontal = ("opciones",)
    fields = ("opciones", "precio", "clave")
    readonly_fields = ("clave",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "preview",
        "nombre",
        "categoria",
        "precio",
        "stock",
        "disponible",
        "destacado",
        "visible",
        "orden",
    )
    list_editable = ("precio", "stock", "disponible", "destacado", "visible", "orden")
    search_fields = ("nombre", "descripcion", "categoria__nombre")
    list_filter = ("categoria", "destacado", "visible", "disponible")
    ordering = ("orden", "nombre")
    autocomplete_fields = ("categoria",)
    filter_horizontal = ("opciones",)
    inlines = [ProductoImagenInline, PrecioCombinacionInline]

    def preview(self, obj):
        if not obj.imagen:
            return "-"
        return format_html('<img src="{}" style="height:54px;width:54px;object-fit:cover;border-radius:8px;" />', obj.imagen.url)

    preview.short_description = "Preview"


class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 0
    readonly_fields = ("producto", "detalle", "cantidad", "precio")
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre_cliente",
        "email_cliente",
        "telefono",
        "tipo_entrega",
        "comuna_sector",
        "costo_despacho",
        "cantidad_cajas",
        "costo_caja",
        "total",
        "creado",
    )
    search_fields = ("nombre_cliente", "email_cliente", "telefono", "comuna_sector", "comentario_ocasion")
    list_filter = ("creado", "tipo_entrega")
    readonly_fields = ("creado", "total", "costo_despacho", "costo_caja")
    ordering = ("-creado",)
    inlines = [PedidoItemInline]


@admin.register(PedidoItem)
class PedidoItemAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "detalle", "cantidad", "precio")
    search_fields = ("pedido__nombre_cliente", "producto__nombre")
    list_filter = ("pedido__creado",)
    ordering = ("-pedido__creado",)


@admin.register(ClicEnlace)
class ClicEnlaceAdmin(admin.ModelAdmin):
    """Que botones de dulcecita.cl/links usa la gente.

    Arriba de la lista va el resumen de los ultimos 30 dias: es lo que la duena
    quiere saber (cuantos entran a pedir vs. cuantos escriben por WhatsApp), no
    cada clic suelto.
    """
    list_display = ("slug", "creado")
    list_filter = ("slug",)
    date_hierarchy = "creado"
    change_list_template = "admin/clics_enlace.html"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from .links import resumen_clics
        nombres = {"pedido": "Haz tu pedido", "whatsapp": "WhatsApp", "box": "Arma tu box",
                   "corporativo": "Regalos para empresas", "delivery": "Despacho y retiro",
                   "instagram": "Instagram"}
        resumen = []
        for slug, n in resumen_clics(30):
            if slug.startswith("p") and slug[1:].isdigit():
                producto = Producto.objects.filter(pk=int(slug[1:])).first()
                etiqueta = f"Producto: {producto.nombre}" if producto else slug
            else:
                etiqueta = nombres.get(slug, slug)
            resumen.append((etiqueta, n))
        extra_context = {**(extra_context or {}), "resumen_clics": resumen}
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Opcion)
class OpcionAdmin(admin.ModelAdmin):
    list_display = ("muestra", "nombre", "tipo", "recargo", "orden", "activa")
    list_editable = ("recargo", "orden", "activa")
    list_filter = ("tipo", "activa")
    ordering = ("tipo", "orden", "nombre")

    def muestra(self, obj):
        return format_html(
            '<span style="display:inline-block;width:22px;height:22px;border-radius:50%;'
            'background:{};border:1px solid #cfd6de;"></span>', obj.color)


@admin.register(BeneficioDiferencial)
class BeneficioDiferencialAdmin(admin.ModelAdmin):
    list_display = ("titulo", "activo", "orden")
    list_editable = ("activo", "orden")
    search_fields = ("titulo", "descripcion")
    list_filter = ("activo",)
    ordering = ("orden", "id")


@admin.register(Testimonio)
class TestimonioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rol", "destacado", "activo", "orden")
    list_editable = ("destacado", "activo", "orden")
    search_fields = ("nombre", "rol", "texto")
    list_filter = ("destacado", "activo")
    ordering = ("orden", "id")


@admin.register(PreguntaFrecuente)
class PreguntaFrecuenteAdmin(admin.ModelAdmin):
    list_display = ("pregunta", "activa", "orden")
    list_editable = ("activa", "orden")
    search_fields = ("pregunta", "respuesta")
    list_filter = ("activa",)
    ordering = ("orden", "id")


@admin.register(CampanaEspecial)
class CampanaEspecialAdmin(admin.ModelAdmin):
    list_display = ("titulo", "activa", "orden")
    list_editable = ("activa", "orden")
    search_fields = ("titulo", "descripcion", "cta_texto", "cta_url")
    list_filter = ("activa",)
    ordering = ("orden", "id")


from django.db.models.signals import m2m_changed  # noqa: E402
from django.dispatch import receiver  # noqa: E402


@receiver(m2m_changed, sender=PrecioCombinacion.opciones.through)
def _clave_precio(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        instance.actualizar_clave()
