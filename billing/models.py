import uuid
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from shared.validators import validate_cedula_ec


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')

    class Meta:
        verbose_name = 'Grupo de Producto'
        verbose_name_plural = 'Grupos de Productos'
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nombre')
    ruc = models.CharField(max_length=13, unique=True, verbose_name='RUC')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    email = models.EmailField(blank=True, verbose_name='Email')
    address = models.TextField(blank=True, verbose_name='Dirección')

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.ruc})'


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nombre')
    code = models.CharField(max_length=50, unique=True, verbose_name='Código')
    description = models.TextField(blank=True, verbose_name='Descripción')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio')
    stock = models.PositiveIntegerField(default=0, verbose_name='Stock')
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name='Imagen',
    )
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, verbose_name='Marca')
    group = models.ForeignKey(ProductGroup, on_delete=models.PROTECT, verbose_name='Grupo')
    suppliers = models.ManyToManyField(Supplier, blank=True, verbose_name='Proveedores')

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['name']

    def __str__(self):
        return f'{self.code} - {self.name}'

    @property
    def balance(self):
        """Valor total en inventario: precio × stock (no se almacena en BD)."""
        return self.price * self.stock


class Customer(models.Model):
    cedula = models.CharField(
        max_length=13,
        unique=True,
        verbose_name='Cédula/RUC',
        validators=[validate_cedula_ec],
    )
    first_name = models.CharField(max_length=100, verbose_name='Nombres')
    last_name = models.CharField(max_length=100, verbose_name='Apellidos')
    email = models.EmailField(blank=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    address = models.TextField(blank=True, verbose_name='Dirección')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name} {self.first_name} ({self.cedula})'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'


class CustomerProfile(models.Model):
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name='profile', verbose_name='Cliente'
    )
    notes = models.TextField(blank=True, verbose_name='Notas')
    credit_limit = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Límite de crédito'
    )
    is_vip = models.BooleanField(default=False, verbose_name='¿Es VIP?')

    class Meta:
        verbose_name = 'Perfil de Cliente'
        verbose_name_plural = 'Perfiles de Clientes'

    def __str__(self):
        return f'Perfil de {self.customer}'


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('paid', 'Pagada'),
        ('cancelled', 'Anulada'),
    ]
    number = models.CharField(max_length=20, unique=True, verbose_name='Número')
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, verbose_name='Cliente', related_name='invoices'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Creado por', null=True, blank=True
    )
    date = models.DateField(auto_now_add=True, verbose_name='Fecha')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Estado')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Subtotal')
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='IVA (15%)')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Total')

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'Factura #{self.number} - {self.customer}'

    def calculate_totals(self):
        subtotal = sum(d.subtotal for d in self.details.all())
        iva = subtotal * Decimal('0.15')
        self.subtotal = subtotal
        self.iva = iva
        self.total = subtotal + iva
        self.save(update_fields=['subtotal', 'iva', 'total'])


class InvoiceDetail(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='details', verbose_name='Factura'
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Producto')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Cantidad')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio unitario')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Subtotal', editable=False, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'Detalle de Factura'
        verbose_name_plural = 'Detalles de Factura'

    def __str__(self):
        return f'{self.product} x {self.quantity}'

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)


class Payment(models.Model):
    METHOD_CHOICES = [
        ('card',     'Tarjeta de Crédito/Débito'),
        ('paypal',   'PayPal'),
        ('transfer', 'Transferencia Bancaria'),
    ]
    STATUS_CHOICES = [
        ('approved', 'Aprobado'),
        ('pending',  'Pendiente'),
        ('rejected', 'Rechazado'),
    ]
    method      = models.CharField(max_length=20, choices=METHOD_CHOICES, verbose_name='Método')
    reference   = models.CharField(max_length=100, unique=True, verbose_name='Referencia')
    amount      = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved', verbose_name='Estado')
    paid_at     = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de pago')
    payer_name  = models.CharField(max_length=200, blank=True, verbose_name='Nombre del pagador')
    payer_email = models.EmailField(blank=True, verbose_name='Email del pagador')
    card_last4  = models.CharField(max_length=4, blank=True, verbose_name='Últimos 4 dígitos')

    class Meta:
        verbose_name        = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering            = ['-paid_at']

    def __str__(self):
        return f'Pago {self.reference} – {self.get_method_display()}'


class Purchase(models.Model):
    user         = models.ForeignKey(User, on_delete=models.PROTECT, related_name='purchases',   verbose_name='Usuario')
    invoice      = models.OneToOneField(Invoice, on_delete=models.PROTECT, related_name='purchase',  verbose_name='Factura')
    payment      = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name='purchase',  verbose_name='Pago', null=True, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de compra')

    class Meta:
        verbose_name        = 'Compra'
        verbose_name_plural = 'Compras'
        ordering            = ['-purchased_at']

    def __str__(self):
        return f'Compra de {self.user.username} – {self.invoice.number}'
