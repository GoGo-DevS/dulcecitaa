from django import forms


class BaseStyledForm(forms.Form):
    """Aplica clases base neutrales para estilos propios del proyecto."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "field-input"
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("rows", 4)
                css_class = "field-input field-textarea"
            current = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{current} {css_class}".strip()


class ContactoForm(BaseStyledForm):
    nombre = forms.CharField(max_length=100, label="Nombre")
    email = forms.EmailField(label="Email")
    mensaje = forms.CharField(label="Mensaje", widget=forms.Textarea)


class CorporativoForm(BaseStyledForm):
    nombre = forms.CharField(max_length=100, label="Tu nombre")
    empresa = forms.CharField(max_length=120, label="Empresa")
    email = forms.EmailField(label="Correo")
    telefono = forms.CharField(max_length=20, label="Telefono")
    mensaje = forms.CharField(label="Describe tu pedido", widget=forms.Textarea)

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"].strip()
        permitidos = set("+0123456789 -()")
        if len(telefono) < 8 or any(char not in permitidos for char in telefono):
            raise forms.ValidationError("Ingresa un telefono valido.")
        return telefono


class CheckoutForm(BaseStyledForm):
    TIPO_ENTREGA_RETIRO = "retiro"
    TIPO_ENTREGA_DESPACHO = "despacho"
    TIPOS_ENTREGA = [
        (TIPO_ENTREGA_RETIRO, "Retiro en punto"),
        (TIPO_ENTREGA_DESPACHO, "Despacho a domicilio"),
    ]

    nombre = forms.CharField(max_length=100, label="Nombre")
    email = forms.EmailField(label="Email")
    telefono = forms.CharField(max_length=20, label="Telefono")
    tipo_entrega = forms.ChoiceField(label="Metodo de entrega", choices=TIPOS_ENTREGA)
    comuna_sector = forms.CharField(max_length=120, label="Comuna o sector")
    direccion = forms.CharField(label="Direccion", widget=forms.Textarea(attrs={"rows": 3}))

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"].strip()
        permitidos = set("+0123456789 -()")
        if len(telefono) < 8 or any(char not in permitidos for char in telefono):
            raise forms.ValidationError("Ingresa un telefono valido.")
        return telefono

    def clean(self):
        cleaned = super().clean()
        tipo_entrega = cleaned.get("tipo_entrega")
        direccion = (cleaned.get("direccion") or "").strip()

        if tipo_entrega == self.TIPO_ENTREGA_DESPACHO and len(direccion) < 8:
            self.add_error("direccion", "Ingresa una direccion completa para el despacho.")

        return cleaned
