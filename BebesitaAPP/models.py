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

class Opcion(models.Model):
    """Lo que el cliente elige dentro de un producto: cobertura, relleno...

    No es un producto aparte. Antes cada cobertura era un Producto propio y el
    alfajor blanco se duplicaba en el catalogo; con relleno ademas de cobertura
    habria que crear un producto por cada combinacion. Aca se carga UNA vez
    ("Chocolate blanco") y se marca en los productos que la ofrecen.
    """
    TIPO_COBERTURA = "cobertura"
    TIPO_RELLENO = "relleno"
    TIPOS = [
        (TIPO_COBERTURA, "Cobertura"),
        (TIPO_RELLENO, "Relleno"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPOS, default=TIPO_COBERTURA)
    nombre = models.CharField(max_length=60)
    color = models.CharField(
        'Color de la muestra', max_length=7, default="#5b3a29",
        help_text='Hex del circulito que se ve en la tarjeta. Ej: #5b3a29 chocolate.')
    recargo = models.IntegerField(
        default=0, help_text='Se suma al precio por unidad. 0 si cuesta lo mismo.')
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ("tipo", "orden", "nombre")
        verbose_name = "Opción"
        verbose_name_plural = "Opciones (coberturas, rellenos)"

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.nombre}"


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

    # Variantes de un mismo producto (por ejemplo, la cobertura del alfajor).
    # Cada variante es un Producto propio que apunta al principal: asi el
    # carrito, el stock y el pedido siguen funcionando igual, sin tocar nada,
    # y cada cobertura puede tener su precio y su foto.
    variante_de = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='variantes', verbose_name='Es variante de',
        help_text='Dejar vacío si es un producto normal.')
    variante_nombre = models.CharField(
        'Nombre de la variante', max_length=60, blank=True,
        help_text='Lo que se lee en el selector. Ej: Chocolate blanco.')
    # Cuando el producto se vende en pack, aca se dice de cuantas unidades.
    unidades_por_pack = models.PositiveIntegerField(
        'Unidades por paquete', default=1,
        help_text='Ej: 4 si la bolsita trae 4. Se usa solo para explicarlo.')
    opciones = models.ManyToManyField(
        Opcion, blank=True, related_name='productos',
        help_text='Coberturas y rellenos que el cliente puede elegir.')

    class Meta:
        ordering = ("orden", "nombre")

    def __str__(self):
        return self.nombre

    def grupos_opciones(self):
        """[(tipo, "Cobertura", [opciones])], un grupo por tipo, en orden."""
        etiquetas = dict(Opcion.TIPOS)
        grupos = {}
        for op in self.opciones.all():
            if op.activa:
                grupos.setdefault(op.tipo, []).append(op)
        return [(t, etiquetas[t], grupos[t]) for t, _ in Opcion.TIPOS if t in grupos]

    def clave_inicial(self):
        """La linea de carrito con la primera opcion de cada grupo: "15-1"."""
        ids = sorted(opciones[0].id for _, _, opciones in self.grupos_opciones())
        return "-".join(str(x) for x in [self.id, *ids])

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
    cantidad_cajas = models.PositiveIntegerField(default=1)
    costo_caja = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    comentario_ocasion = models.TextField(default="")
    creado = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Pedido {self.id} - {self.nombre_cliente}"


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio = models.DecimalField(max_digits=10, decimal_places=2)  # precio unitario al momento de compra
    # Texto y no FK: el pedido tiene que seguir diciendo "Chocolate blanco"
    # aunque mañana esa cobertura se renombre o se borre.
    detalle = models.CharField(max_length=200, blank=True, default="")

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



class ClicEnlace(models.Model):
    """Un toque en un boton de dulcecita.cl/links.

    La pagina de links vive en la bio de Instagram: sin esto no hay forma de
    saber si la gente entra a pedir, escribe por WhatsApp o solo mira. Se
    guarda solo el boton y la hora; nada que identifique a la persona.
    """
    slug = models.CharField(max_length=40, db_index=True)
    creado = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-creado",)
        verbose_name = "Clic en links"
        verbose_name_plural = "Clics en links (bio de Instagram)"

    def __str__(self):
        return f"{self.slug} · {self.creado:%d-%m %H:%M}"
