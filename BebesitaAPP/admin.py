from django.contrib import admin
from django.utils.html import format_html

from .models import (
    BeneficioDiferencial,
    CampanaEspecial,
    CategoriaProducto,
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
    inlines = [ProductoImagenInline]

    def preview(self, obj):
        if not obj.imagen:
            return "-"
        return format_html('<img src="{}" style="height:54px;width:54px;object-fit:cover;border-radius:8px;" />', obj.imagen.url)

    preview.short_description = "Preview"


class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 0
    readonly_fields = ("producto", "cantidad", "precio")
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
        "total",
        "creado",
    )
    search_fields = ("nombre_cliente", "email_cliente", "telefono", "comuna_sector")
    list_filter = ("creado", "tipo_entrega")
    readonly_fields = ("creado", "total", "costo_despacho")
    ordering = ("-creado",)
    inlines = [PedidoItemInline]


@admin.register(PedidoItem)
class PedidoItemAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio")
    search_fields = ("pedido__nombre_cliente", "producto__nombre")
    list_filter = ("pedido__creado",)
    ordering = ("-pedido__creado",)


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
