from django.contrib import admin

from .models import Cliente, Componente, Compra, Pedido, PedidoItem


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "area", "whatsapp", "activo", "creado")
    list_filter = ("activo",)
    search_fields = ("nombre", "empresa", "area", "whatsapp")
    ordering = ("empresa", "nombre")


class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 1


class ComponenteInline(admin.TabularInline):
    model = Componente
    extra = 1


@admin.register(PedidoItem)
class PedidoItemAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "pedido", "cantidad", "precio_unitario")
    inlines = [ComponenteInline]


class CompraInline(admin.TabularInline):
    model = Compra
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "estado", "pagado", "fecha_pedido", "fecha_entrega")
    list_filter = ("estado", "pagado")
    search_fields = ("cliente__nombre", "cliente__empresa", "descripcion")
    date_hierarchy = "fecha_pedido"
    inlines = [PedidoItemInline, CompraInline]


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("fecha", "proveedor", "monto", "pedido")
    list_filter = ("fecha",)
    search_fields = ("proveedor", "detalle")
