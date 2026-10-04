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
