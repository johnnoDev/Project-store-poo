from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import inlineformset_factory

from .models import Brand, ProductGroup, Supplier, Product, Customer, Invoice, InvoiceDetail
from shared.validators import validate_cedula_ec


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Correo electrónico')
    first_name = forms.CharField(max_length=100, required=True, label='Nombres')
    last_name = forms.CharField(max_length=100, required=True, label='Apellidos')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ProductGroupForm(forms.ModelForm):
    class Meta:
        model = ProductGroup
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ('name', 'ruc', 'phone', 'email', 'address')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'ruc': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ProductForm(forms.ModelForm):
    """
    Formulario centralizado para Producto.
    Toda configuración de widgets, validaciones y estilos vive aquí.
    """

    # ── Validación server-side del precio ─────────────────────────────
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError('El precio unitario debe ser mayor que cero.')
        return price

    class Meta:
        model = Product
        fields = (
            'code', 'name', 'description',
            'brand', 'group', 'suppliers',
            'price', 'stock',
            'image',
        )
        labels = {
            'code':        'Código',
            'name':        'Nombre',
            'description': 'Descripción',
            'brand':       'Marca',
            'group':       'Grupo / Categoría',
            'suppliers':   'Proveedores',
            'price':       'Precio unitario',
            'stock':       'Stock disponible',
            'image':       'Imagen del producto',
        }
        widgets = {
            'code': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Ej: PROD-001',
                'autofocus':   True,
            }),
            'name': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Nombre descriptivo del producto',
            }),
            'description': forms.Textarea(attrs={
                'class':       'form-control',
                'placeholder': 'Descripción detallada, características, uso...',
                'rows':        3,
            }),
            'brand': forms.Select(attrs={
                'class': 'form-select',
            }),
            'group': forms.Select(attrs={
                'class': 'form-select',
            }),
            'suppliers': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size':  '4',
            }),
            'price': forms.NumberInput(attrs={
                'class':       'form-control text-end',
                'step':        '0.01',
                'min':         '0.01',
                'placeholder': '0.00',
                'id':          'id_price',
            }),
            'stock': forms.NumberInput(attrs={
                'class':       'form-control text-end',
                'min':         '0',
                'placeholder': '0',
                'id':          'id_stock',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
        }
        help_texts = {
            'code':        'Identificador único del producto en el sistema.',
            'price':       'Valor de venta. Debe ser mayor a $0.00.',
            'stock':       'Unidades disponibles en inventario.',
            'suppliers':   'Ctrl + clic para seleccionar varios proveedores.',
            'image':       'Formatos aceptados: JPG, PNG, WebP. Máximo 5 MB.',
        }
        error_messages = {
            'code':  {'unique':   'Ya existe un producto con este código.'},
            'name':  {'required': 'El nombre del producto es obligatorio.'},
            'price': {
                'required':    'El precio es obligatorio.',
                'invalid':     'Ingresa un valor numérico válido.',
            },
            'stock': {
                'required': 'El stock es obligatorio.',
                'invalid':  'Ingresa un número entero válido.',
            },
        }


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ('cedula', 'first_name', 'last_name', 'email', 'phone', 'address')
        widgets = {
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ('customer', 'number', 'status')
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


InvoiceDetailFormSet = inlineformset_factory(
    Invoice,
    InvoiceDetail,
    fields=('product', 'quantity', 'unit_price'),
    extra=3,
    can_delete=True,
    widgets={
        'product': forms.Select(attrs={'class': 'form-select'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    },
)


# ──────────────────────────────────────────────
# Shop – Checkout & Payment
# ──────────────────────────────────────────────

class CheckoutForm(forms.Form):
    cedula  = forms.CharField(
        max_length=13,
        label='Cédula / RUC',
        validators=[validate_cedula_ec],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0000000000'}),
    )
    phone   = forms.CharField(
        max_length=20,
        required=False,
        label='Teléfono',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09XXXXXXXX'}),
    )
    address = forms.CharField(
        required=False,
        label='Dirección de entrega',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class PaymentForm(forms.Form):
    METHOD_CHOICES = [
        ('card',     'Tarjeta de Crédito/Débito'),
        ('paypal',   'PayPal'),
        ('transfer', 'Transferencia Bancaria'),
    ]
    method = forms.ChoiceField(
        choices=METHOD_CHOICES,
        label='Método de pago',
        widget=forms.RadioSelect(),
    )

    # ── Card fields ──────────────────────────────────────────────────────
    card_number = forms.CharField(
        max_length=19, required=False, label='Número de tarjeta',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': '0000 0000 0000 0000',
            'maxlength': '19', 'autocomplete': 'cc-number',
        }),
    )
    card_holder = forms.CharField(
        max_length=100, required=False, label='Titular de la tarjeta',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Nombre como aparece en la tarjeta',
            'autocomplete': 'cc-name',
        }),
    )
    card_expiry = forms.CharField(
        max_length=5, required=False, label='Vencimiento (MM/AA)',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'MM/AA',
            'maxlength': '5', 'autocomplete': 'cc-exp',
        }),
    )
    card_cvv = forms.CharField(
        max_length=4, required=False, label='CVV',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': '000',
            'maxlength': '4', 'autocomplete': 'cc-csc',
        }),
    )

    # ── PayPal fields ─────────────────────────────────────────────────────
    paypal_email = forms.EmailField(
        required=False, label='Email de PayPal',
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'correo@paypal.com',
        }),
    )

    # ── Bank transfer fields ──────────────────────────────────────────────
    transfer_ref = forms.CharField(
        max_length=50, required=False, label='Número de comprobante',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'REF-000000',
        }),
    )

    def clean(self):
        data   = super().clean()
        method = data.get('method')

        if method == 'card':
            raw = data.get('card_number', '').replace(' ', '').replace('-', '')
            if not raw:
                self.add_error('card_number', 'Ingresa el número de tarjeta.')
            elif not raw.isdigit() or len(raw) < 13:
                self.add_error('card_number', 'Número de tarjeta inválido (mínimo 13 dígitos).')
            else:
                data['card_last4'] = raw[-4:]
            if not data.get('card_holder'):
                self.add_error('card_holder', 'Ingresa el nombre del titular.')
            if not data.get('card_expiry'):
                self.add_error('card_expiry', 'Ingresa la fecha de vencimiento.')
            if not data.get('card_cvv'):
                self.add_error('card_cvv', 'Ingresa el CVV.')

        elif method == 'paypal':
            if not data.get('paypal_email'):
                self.add_error('paypal_email', 'Ingresa el email de tu cuenta PayPal.')

        elif method == 'transfer':
            if not data.get('transfer_ref'):
                self.add_error('transfer_ref', 'Ingresa el número de comprobante de la transferencia.')

        return data
