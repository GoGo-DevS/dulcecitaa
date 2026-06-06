from django import forms

from BebesitaAPP.models import Producto

from .models import Cliente, Componente, Compra, Pedido, PedidoItem


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
            "descripcion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Cajas navidad empresa X"}),
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
                "class": "form-control", "placeholder": "Elige o escribe la caja…",
                "list": "catalogo-cajas", "id": "id_caja_nombre", "autocomplete": "off",
            }),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": 1, "value": 1}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control", "min": 0, "placeholder": "Precio caja"}),
            "costo_unitario": forms.NumberInput(attrs={"class": "form-control", "min": 0, "placeholder": "Costo caja"}),
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
