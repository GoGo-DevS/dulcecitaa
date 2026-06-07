from django.db import models
from django.utils import timezone

from BebesitaAPP.models import Producto  # se reutiliza el catálogo existente


class Cliente(models.Model):
    nombre = models.CharField(max_length=120)
    empresa = models.CharField(max_length=120, blank=True, default="")
    area = models.CharField(max_length=120, blank=True, default="")
    whatsapp = models.CharField(max_length=30, blank=True, default="")
    notas = models.TextField(blank=True, default="")
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("empresa", "nombre")
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        base = self.empresa or self.nombre
        return f"{base} · {self.area}" if self.area else base

    @property
    def titulo(self):
        return self.empresa or self.nombre

    @property
    def whatsapp_digits(self):
        """Solo dígitos, para armar enlaces wa.me."""
        return "".join(ch for ch in self.whatsapp if ch.isdigit())


class Pedido(models.Model):
    COTIZADO = "cotizado"
    CONFIRMADO = "confirmado"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"
    ESTADOS = [
        (COTIZADO, "Cotizado"),
        (CONFIRMADO, "Confirmado"),
        (ENTREGADO, "Entregado"),
        (CANCELADO, "Cancelado"),
    ]
    ESTADO_BADGE = {
        COTIZADO: "secondary",
        CONFIRMADO: "info",
        ENTREGADO: "success",
        CANCELADO: "danger",
    }

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    descripcion = models.CharField(max_length=200, blank=True, default="")
    fecha_pedido = models.DateField(default=timezone.now)
    fecha_entrega = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=COTIZADO)
    pagado = models.BooleanField(default=False)  # cobra por adelantado
    notas = models.TextField(blank=True, default="")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fecha_pedido", "-id")
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return f"Pedido #{self.id} · {self.cliente}"

    @property
    def badge(self):
        return self.ESTADO_BADGE.get(self.estado, "secondary")

    @property
    def precio_total(self):
        return sum(i.subtotal for i in self.items.all())

    @property
    def costo_estimado(self):
        return sum(i.costo_subtotal for i in self.items.all())

    @property
    def costo_real(self):
        return sum(c.monto for c in self.compras.all())

    @property
    def tiene_compras(self):
        return self.compras.exists()

    @property
    def costo_unidades(self):
        """Costo estimado por las UNIDADES producidas, usando el costo por
        unidad de cada producto (definido a mano en «Costos por unidad»)."""
        total = 0
        for caja in self.items.all():
            for comp in caja.componentes.all():
                cu = getattr(comp.producto, "gestion_costo", None)
                if cu and cu.costo_unidad:
                    total += cu.costo_unidad * comp.cantidad * caja.cantidad
        return total

    @property
    def costo_aplicado(self):
        """Prioridad: gasto real (compras) > costo por unidad > estimado por caja."""
        if self.tiene_compras:
            return self.costo_real
        if self.costo_unidades:
            return self.costo_unidades
        return self.costo_estimado

    @property
    def utilidad(self):
        return self.precio_total - self.costo_aplicado

    @property
    def margen_pct(self):
        return round(self.utilidad / self.precio_total * 100) if self.precio_total else 0

    @property
    def produccion(self):
        """Suma de cada producto a fabricar across todas las cajas del pedido.
        Devuelve [{'nombre': 'Alfajor', 'total': 40}, ...]"""
        totales = {}
        orden = []
        for caja in self.items.all():
            for comp in caja.componentes.all():
                nombre = comp.nombre
                if nombre not in totales:
                    totales[nombre] = 0
                    orden.append(nombre)
                totales[nombre] += comp.cantidad * caja.cantidad
        return [{"nombre": n, "total": totales[n]} for n in orden]

    @property
    def tiene_componentes(self):
        return any(caja.componentes.exists() for caja in self.items.all())

    @property
    def total_unidades(self):
        return sum(p["total"] for p in self.produccion)


class PedidoItem(models.Model):
    """Una CAJA del pedido: se vende `cantidad` veces, a `precio_unitario` c/u.
    Su contenido (qué productos lleva cada caja) vive en Componente."""
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(
        Producto, on_delete=models.SET_NULL, null=True, blank=True, related_name="gestion_items"
    )
    descripcion = models.CharField(max_length=200)            # nombre de la caja: "Caja día del padre"
    cantidad = models.PositiveIntegerField(default=1)         # nº de cajas a vender
    precio_unitario = models.PositiveIntegerField(default=0)  # CLP por caja
    costo_unitario = models.PositiveIntegerField(default=0)   # CLP estimado por caja

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.cantidad} × {self.descripcion}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    @property
    def costo_subtotal(self):
        return self.cantidad * self.costo_unitario

    @property
    def unidades_por_caja(self):
        return sum(c.cantidad for c in self.componentes.all())


class Componente(models.Model):
    """Un producto del catálogo que va DENTRO de una caja (ej: 4 alfajores)."""
    item = models.ForeignKey(PedidoItem, on_delete=models.CASCADE, related_name="componentes")
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="gestion_componentes"
    )
    cantidad = models.PositiveIntegerField(default=1)    # cuántos por caja

    class Meta:
        ordering = ("id",)

    @property
    def nombre(self):
        return self.producto.nombre

    def __str__(self):
        return f"{self.cantidad} × {self.nombre}"


class Compra(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.SET_NULL, null=True, blank=True, related_name="compras"
    )
    proveedor = models.CharField(max_length=120, blank=True, default="")  # texto: La Valledor…
    detalle = models.CharField(max_length=200, blank=True, default="")
    monto = models.PositiveIntegerField(default=0)  # CLP
    fecha = models.DateField(default=timezone.now)
    boleta = models.ImageField(upload_to="boletas/", null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fecha", "-id")
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

    def __str__(self):
        return f"${self.monto:,} · {self.proveedor or self.detalle}"


class CostoProducto(models.Model):
    """Costo de producción por UNIDAD de un producto (ej: 1 alfajor = $580).
    Lo define la dueña a mano; sirve para estimar el costo de cada pedido
    según cuántas unidades produce."""
    producto = models.OneToOneField(
        Producto, on_delete=models.CASCADE, related_name="gestion_costo"
    )
    costo_unidad = models.PositiveIntegerField(default=0)  # CLP por unidad
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Costo por unidad"
        verbose_name_plural = "Costos por unidad"

    def __str__(self):
        return f"{self.producto.nombre}: ${self.costo_unidad}"
