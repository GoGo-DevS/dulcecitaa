from django import forms
from django.contrib.auth.forms import AuthenticationForm

from BebesitaAPP.models import Producto
from BebesitaAPP.models import Promocion

from .models import Cliente, Componente, Compra, Pedido, PedidoItem


class GestionLoginForm(AuthenticationForm):
    """Login de la gestión, con placeholders personalizados."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": "form-control form-control-lg",
            "placeholder": "te amo",
            "autofocus": True,
        })
        self.fields["password"].widget.attrs.update({
            "class": "form-control form-control-lg",
            "placeholder": "mi vida",
        })


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ("nombre", "empresa", "area", "whatsapp", "notas", "activo")
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de contacto"}),
            "empresa": forms.TextInput(attrs={"class": "form-control", "placeholder": "Empresa (ej: AZA)"}),
            "area": forms.TextInput(attrs={"class": "form-control", "placeholder": "Área (ej: Laminación)"}),
            "whatsapp": forms.TextInput(attrs={"class": "form-control", "placeholder": "+569..."}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Notas (opcional)"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ("cliente", "descripcion", "fecha_pedido", "fecha_entrega", "notas")
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "descripcion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Box navidad empresa X"}),
            "fecha_pedido": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "fecha_entrega": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Notas (opcional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_pedido"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_entrega"].input_formats = ["%Y-%m-%d"]
        self.fields["cliente"].queryset = Cliente.objects.filter(activo=True)


class PedidoItemForm(forms.ModelForm):
    class Meta:
        model = PedidoItem
        fields = ("descripcion", "cantidad", "precio_unitario", "costo_unitario")
        widgets = {
            "descripcion": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Elige o escribe el box…",
                "list": "catalogo-cajas", "id": "id_caja_nombre", "autocomplete": "off",
            }),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": 1, "value": 1}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control", "min": 0, "placeholder": "Precio box"}),
            "costo_unitario": forms.NumberInput(attrs={"class": "form-control", "min": 0, "placeholder": "Costo box"}),
        }


class ComponenteForm(forms.ModelForm):
    class Meta:
        model = Componente
        fields = ("producto", "cantidad")
        widgets = {
            "producto": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control form-control-sm", "min": 1, "value": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = Producto.objects.all().order_by("nombre")
        self.fields["producto"].empty_label = "Elige un producto…"


class PedidoClienteForm(forms.ModelForm):
    """Cambiar el cliente del pedido desde el detalle."""
    class Meta:
        model = Pedido
        fields = ("cliente",)
        widgets = {"cliente": forms.Select(attrs={"class": "form-select", "onchange": "this.form.submit()"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.filter(activo=True)
        self.fields["cliente"].empty_label = None


class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ("proveedor", "detalle", "monto", "fecha", "boleta")
        widgets = {
            "proveedor": forms.TextInput(attrs={"class": "form-control", "placeholder": "La Valledor, Plaza Maipú..."}),
            "detalle": forms.TextInput(attrs={"class": "form-control", "placeholder": "Qué compró (opcional)"}),
            "monto": forms.NumberInput(attrs={"class": "form-control", "min": 0, "placeholder": "Monto total $"}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "boleta": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*", "capture": "environment"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]

class PromocionForm(forms.ModelForm):
    """Formulario de campana para el panel de la duena, no para el admin crudo.

    Los campos van con su texto de ayuda en palabras y el calendario nativo del
    telefono (type=date), que es desde donde ella lo va a llenar.
    """

    class Meta:
        model = Promocion
        fields = ("nombre", "porcentaje", "desde", "hasta", "etiqueta", "mensaje", "activa")
        labels = {
            "nombre": "Nombre de la campaña",
            "porcentaje": "Descuento",
            "desde": "Primer día",
            "hasta": "Último día",
            "etiqueta": "Sello sobre el precio",
            "mensaje": "Franja de arriba",
            "activa": "Encendida",
        }
        help_texts = {
            "nombre": "Para ti, no se muestra. Ej: Día del Profesor 2026.",
            "porcentaje": "Se aplica a todos los productos.",
            "desde": "Desde este día se ve el descuento.",
            "hasta": "Este día TODAVÍA tiene descuento. Al día siguiente se apaga sola.",
            "etiqueta": "Lo que dice el sello junto al precio. Ej: Día del Profesor.",
            "mensaje": "La franja rosada de arriba. Si la dejas vacía, no aparece la franja.",
            "activa": "Desmarcar la apaga sin borrar nada: las fechas quedan guardadas.",
        }
        widgets = {
            # type=date abre el calendario del telefono. Sin esto hay que
            # escribir la fecha a mano en el formato exacto o no guarda.
            "desde": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "hasta": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Día del Profesor 2026"}),
            "porcentaje": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 60}),
            "etiqueta": forms.TextInput(attrs={"class": "form-control", "placeholder": "Día del Profesor"}),
            "mensaje": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "10% en todo por el Día del Profesor · arma tu box"}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    # Que "hasta" no quede antes de "desde" lo valida Promocion.clean(), y el
    # ModelForm lo corre solo: el error cae en el campo "hasta". Validarlo acá
    # de nuevo era duplicar la regla en dos lugares, con el riesgo de que un
    # día digan cosas distintas.


class ProductoForm(forms.ModelForm):
    """Un producto de la tienda web, editado desde el panel (15-11-2026).

    Hasta hoy el catalogo solo se tocaba en /admin/, que la duena no usa: un
    cambio de precio pasaba por Diego. Aca van los campos que ella decide (que
    se vende, a cuanto, desde cuantas unidades, con que foto y si se ve), con
    ayuda en palabras.

    Lo que NO esta, a proposito:
    - la direccion web (slug): cambiarla rompe los enlaces ya compartidos y lo
      que Google tiene indexado;
    - borrar: los pedidos apuntan al producto con CASCADE, borrarlo se llevaria
      los pedidos que lo compraron. Un producto que ya no se vende se OCULTA.
    """

    FOTO_LADO_MAXIMO = 1400      # px del lado mas largo
    FOTO_PESO_MAXIMO = 12 * 1024 * 1024

    class Meta:
        model = Producto
        fields = ("nombre", "descripcion", "precio", "unidades_por_pack", "minimo", "imagen",
                  "opciones", "visible", "disponible", "destacado", "en_box", "pide_nota", "orden")
        labels = {
            "nombre": "Nombre",
            "descripcion": "Descripción",
            "precio": "Precio",
            "unidades_por_pack": "Unidades por paquete",
            "minimo": "Mínimo por pedido",
            "imagen": "Foto principal",
            "opciones": "Opciones que elige el cliente",
            "visible": "Se ve en la web",
            "disponible": "Se puede comprar",
            "destacado": "Destacado en la portada",
            "en_box": "Entra en Arma tu box",
            "pide_nota": "Pide una nota al cliente",
            "orden": "Orden en el catálogo",
        }
        help_texts = {
            "nombre": "Como aparece en el catálogo y en el carrito.",
            "descripcion": "Lo que se lee en la ficha del producto. Cuenta de qué es y cómo se vende.",
            "precio": "En pesos, sin puntos. Es el precio de UNA unidad (o de un paquete, si se vende por paquete).",
            "unidades_por_pack": "1 si se vende por unidad. 4 si el precio es de una bolsita de 4.",
            "minimo": "Desde cuántas se puede pedir. Con 0 usa el mínimo general de la tienda.",
            "imagen": "Una foto real, clara y de frente. Se achica sola antes de guardarse.",
            "opciones": "Coberturas o tamaños entre los que el cliente elige al pedir.",
            "visible": "Si lo desmarcas sale del catálogo y de Google, pero los pedidos antiguos no se pierden.",
            "disponible": "Si lo desmarcas se sigue viendo, con «No disponible» y sin botón de compra.",
            "destacado": "Los destacados salen primero en la portada.",
            "en_box": "Desmárcalo para lo que no cabe en una caja, como una torta.",
            "pide_nota": "En el carrito aparece un campo para escribir colores o decoración.",
            "orden": "Los números más bajos salen primero.",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "precio": forms.NumberInput(attrs={"class": "form-control", "min": 1, "inputmode": "numeric"}),
            "unidades_por_pack": forms.NumberInput(attrs={"class": "form-control", "min": 1, "inputmode": "numeric"}),
            "minimo": forms.NumberInput(attrs={"class": "form-control", "min": 0, "inputmode": "numeric"}),
            "orden": forms.NumberInput(attrs={"class": "form-control", "min": 0, "inputmode": "numeric"}),
            # FileInput y no ClearableFileInput: un producto no puede quedar sin foto.
            "imagen": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "opciones": forms.CheckboxSelectMultiple,
            "visible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "disponible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "destacado": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "en_box": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "pide_nota": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from BebesitaAPP.models import Opcion

        self.fields["opciones"].queryset = Opcion.objects.filter(activa=True).order_by("tipo", "orden", "nombre")
        self.fields["opciones"].required = False
        # Al editar, la foto que ya tiene se conserva si no se sube otra.
        self.fields["imagen"].required = not (self.instance and self.instance.pk)

    def clean_nombre(self):
        nombre = " ".join((self.cleaned_data.get("nombre") or "").split())
        if not nombre:
            raise forms.ValidationError("Ponle un nombre al producto.")
        # Dos productos principales con el mismo nombre se confunden en el
        # carrito, en el pedido y en el panel.
        repetido = Producto.objects.filter(nombre__iexact=nombre, variante_de__isnull=True)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError("Ya hay un producto con ese nombre.")
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data.get("precio")
        if precio is None or precio <= 0:
            raise forms.ValidationError("El precio tiene que ser mayor que cero.")
        return precio

    def clean_unidades_por_pack(self):
        unidades = self.cleaned_data.get("unidades_por_pack")
        if not unidades or unidades < 1:
            raise forms.ValidationError("Pon 1 si se vende por unidad.")
        return unidades

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        # Sin archivo nuevo queda la foto que ya tenia (no trae content_type).
        if not imagen or not hasattr(imagen, "content_type"):
            return imagen
        if imagen.size > self.FOTO_PESO_MAXIMO:
            raise forms.ValidationError("La foto pesa demasiado (máximo 12 MB).")
        return achicar_foto(imagen, self.FOTO_LADO_MAXIMO)


def achicar_foto(archivo, lado_maximo=1400, calidad=85):
    """La foto subida: enderezada, achicada y en JPEG.

    Una foto de celular pesa 4 a 8 MB y mide 4.000 px: publicada tal cual, la
    ficha tarda segundos en mostrar el producto, y eso pesa en Google y en la
    venta. Aca queda en 1.400 px de lado y unas decenas de KB.

    - Se endereza con el dato de orientacion de la camara (si no, la foto
      tomada con el telefono de lado sale acostada).
    - Una imagen con transparencia se pega sobre blanco: JPEG no la guarda.
    """
    from io import BytesIO

    from django.core.files.uploadedfile import InMemoryUploadedFile
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        archivo.seek(0)
        imagen = Image.open(archivo)
        imagen.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise forms.ValidationError("Ese archivo no es una foto que se pueda leer. Prueba con un JPG o PNG.")
    imagen = ImageOps.exif_transpose(imagen)
    if imagen.mode in ("RGBA", "LA", "P"):
        imagen = imagen.convert("RGBA")
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        fondo.paste(imagen, mask=imagen.getchannel("A"))
        imagen = fondo
    else:
        imagen = imagen.convert("RGB")
    imagen.thumbnail((lado_maximo, lado_maximo), Image.LANCZOS)

    salida = BytesIO()
    imagen.save(salida, format="JPEG", quality=calidad, optimize=True, progressive=True)
    peso = salida.tell()
    salida.seek(0)
    base = (getattr(archivo, "name", "") or "foto").rsplit(".", 1)[0][:60] or "foto"
    return InMemoryUploadedFile(salida, "imagen", f"{base}.jpg", "image/jpeg", peso, None)
