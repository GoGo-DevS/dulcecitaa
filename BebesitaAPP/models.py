from django.conf import settings
from django.db import models


class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ("orden", "nombre")
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.IntegerField()
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.SET_NULL, null=True, blank=True, related_name="productos")
    destacado = models.BooleanField(default=False)
    visible = models.BooleanField(default=True)
    disponible = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)
    orden = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(upload_to='productos/')

    class Meta:
        ordering = ("orden", "nombre")

    def __str__(self):
        return self.nombre

class Carrito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    # estado por ejemplo: activo, pagado, cancelado (opcional)

class CarritoItem(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)


# --- Pedido y PedidoItem (checkout) ---
class Pedido(models.Model):
    TIPO_ENTREGA_RETIRO = "retiro"
    TIPO_ENTREGA_DESPACHO = "despacho"
    TIPOS_ENTREGA = [
        (TIPO_ENTREGA_RETIRO, "Retiro en punto"),
        (TIPO_ENTREGA_DESPACHO, "Despacho a domicilio"),
    ]

    nombre_cliente = models.CharField(max_length=100)
    email_cliente = models.EmailField()
    telefono = models.CharField(max_length=20)
    tipo_entrega = models.CharField(max_length=20, choices=TIPOS_ENTREGA, default=TIPO_ENTREGA_RETIRO)
    comuna_sector = models.CharField(max_length=120, default="")
    direccion = models.TextField()
    costo_despacho = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Pedido {self.id} - {self.nombre_cliente}"


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio = models.DecimalField(max_digits=10, decimal_places=2)  # precio unitario al momento de compra

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} (Pedido {self.pedido_id})"


class ProductoImagen(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="imagenes")
    imagen = models.ImageField(upload_to="productos/galeria/")

    def __str__(self):
        return f"Imagen de {self.producto.nombre}"


class BeneficioDiferencial(models.Model):
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField()
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("orden", "id")
        verbose_name = "Beneficio diferencial"
        verbose_name_plural = "Beneficios diferenciales"

    def __str__(self):
        return self.titulo


class Testimonio(models.Model):
    nombre = models.CharField(max_length=100)
    texto = models.TextField()
    rol = models.CharField(max_length=120, blank=True, default="")
    destacado = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("orden", "id")

    def __str__(self):
        return self.nombre


class PreguntaFrecuente(models.Model):
    pregunta = models.CharField(max_length=180)
    respuesta = models.TextField()
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ("orden", "id")
        verbose_name = "Pregunta frecuente"
        verbose_name_plural = "Preguntas frecuentes"

    def __str__(self):
        return self.pregunta


class CampanaEspecial(models.Model):
    titulo = models.CharField(max_length=130)
    descripcion = models.TextField()
    cta_texto = models.CharField(max_length=50, blank=True, default="")
    cta_url = models.CharField(max_length=180, blank=True, default="")
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ("orden", "id")
        verbose_name = "Campana especial"
        verbose_name_plural = "Campanas especiales"

    def __str__(self):
        return self.titulo

