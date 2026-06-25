import json
import uuid
from decimal import Decimal
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q


# ──────────────────────────────────────────────
# Staff-only guard (FBV decorator)
# ──────────────────────────────────────────────

def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Solo el personal autorizado puede acceder a esa sección.')
            return redirect('billing:shop_catalog')
        return view_func(request, *args, **kwargs)
    return wrapper


# ──────────────────────────────────────────────
# Definición de columnas del listado de Productos
# ──────────────────────────────────────────────
PRODUCT_COLUMNS = [
    {'key': 'image',       'label': 'Imagen',       'default': True,
     'accessor': None},
    {'key': 'code',        'label': 'Código',        'default': True,
     'accessor': 'code'},
    {'key': 'name',        'label': 'Nombre',        'default': True,
     'accessor': 'name'},
    {'key': 'description', 'label': 'Descripción',   'default': False,
     'accessor': 'description'},
    {'key': 'brand',       'label': 'Marca',         'default': True,
     'accessor': 'brand.name'},
    {'key': 'group',       'label': 'Grupo',         'default': True,
     'accessor': 'group.name'},
    {'key': 'price',       'label': 'Precio ($)',    'default': True,
     'accessor': 'price'},
    {'key': 'stock',       'label': 'Stock',         'default': True,
     'accessor': 'stock'},
    {'key': 'suppliers',   'label': 'Proveedores',   'default': True,
     'accessor': lambda obj: ', '.join(s.name for s in obj.suppliers.all())},
    {'key': 'balance',     'label': 'Balance ($)',   'default': False,
     'accessor': lambda obj: f'{obj.balance:.2f}'},
]
PRODUCT_COLUMNS_DEFAULT = [c['key'] for c in PRODUCT_COLUMNS if c['default']]
_PRODUCT_COLUMNS_VALID  = {c['key'] for c in PRODUCT_COLUMNS}

from .models import (
    Brand, ProductGroup, Supplier, Product,
    Customer, Invoice, InvoiceDetail, Payment, Purchase,
)
from .forms import (
    SignUpForm, BrandForm, ProductGroupForm, SupplierForm,
    ProductForm, CustomerForm, InvoiceForm, InvoiceDetailFormSet,
    CheckoutForm, PaymentForm,
)
from shared.decorators import audit_action
from shared.mixins import StaffRequiredMixin, ExportMixin


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────

class SignUpView(CreateView):
    form_class    = SignUpForm
    template_name = 'registration/signup.html'
    success_url   = reverse_lazy('billing:shop_catalog')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f'¡Bienvenido, {user.first_name}! Explora nuestros productos.')
        return redirect(self.success_url)


# ──────────────────────────────────────────────
# Home / Dashboard  (redirige usuarios normales a la tienda)
# ──────────────────────────────────────────────

@login_required
def home(request):
    if not request.user.is_staff:
        return redirect('billing:shop_catalog')
    brands_count   = Brand.objects.count()
    products_count = Product.objects.count()
    customers_count= Customer.objects.count()
    invoices_count = Invoice.objects.count()
    recent_invoices= Invoice.objects.select_related('customer').order_by('-date', '-id')[:5]
    low_stock      = Product.objects.filter(stock__lt=5).select_related('brand')
    return render(request, 'billing/home.html', {
        'brands_count':    brands_count,
        'products_count':  products_count,
        'customers_count': customers_count,
        'invoices_count':  invoices_count,
        'recent_invoices': recent_invoices,
        'low_stock':       low_stock,
    })


# ──────────────────────────────────────────────
# Product column-selector (AJAX)  – staff only
# ──────────────────────────────────────────────

@login_required
@staff_required
def product_columns_save(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    try:
        cols = json.loads(request.body).get('columns', [])
        cols = [k for k in cols if k in _PRODUCT_COLUMNS_VALID]
        if not cols:
            cols = PRODUCT_COLUMNS_DEFAULT
        request.session['product_visible_columns'] = cols
        return JsonResponse({'ok': True, 'columns': cols})
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)


# ──────────────────────────────────────────────
# Brand (FBV) – staff only
# ──────────────────────────────────────────────

@login_required
@staff_required
@audit_action('brand_list')
def brand_list(request):
    q = request.GET.get('q', '')
    brands = Brand.objects.all()
    if q:
        brands = brands.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, 'billing/brand_list.html', {'brands': brands, 'q': q})


@login_required
@staff_required
@audit_action('brand_create')
def brand_create(request):
    form = BrandForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Marca creada exitosamente.')
        return redirect('billing:brand_list')
    return render(request, 'billing/brand_form.html', {'form': form, 'title': 'Nueva Marca'})


@login_required
@staff_required
@audit_action('brand_edit')
def brand_edit(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    form  = BrandForm(request.POST or None, instance=brand)
    if form.is_valid():
        form.save()
        messages.success(request, 'Marca actualizada exitosamente.')
        return redirect('billing:brand_list')
    return render(request, 'billing/brand_form.html', {'form': form, 'title': 'Editar Marca'})


@login_required
@staff_required
@audit_action('brand_delete')
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        brand.delete()
        messages.success(request, 'Marca eliminada exitosamente.')
        return redirect('billing:brand_list')
    return render(request, 'billing/brand_confirm_delete.html', {'object': brand})


# ──────────────────────────────────────────────
# ProductGroup (CBV) – staff only
# ──────────────────────────────────────────────

class ProductGroupListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = ProductGroup
    template_name = 'billing/productgroup_list.html'
    context_object_name = 'groups'


class ProductGroupCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model      = ProductGroup
    form_class = ProductGroupForm
    template_name = 'billing/productgroup_form.html'
    success_url   = reverse_lazy('billing:productgroup_list')

    def form_valid(self, form):
        messages.success(self.request, 'Grupo creado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nuevo Grupo'
        return ctx


class ProductGroupUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model      = ProductGroup
    form_class = ProductGroupForm
    template_name = 'billing/productgroup_form.html'
    success_url   = reverse_lazy('billing:productgroup_list')

    def form_valid(self, form):
        messages.success(self.request, 'Grupo actualizado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Editar Grupo'
        return ctx


class ProductGroupDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model       = ProductGroup
    template_name = 'billing/productgroup_confirm_delete.html'
    success_url   = reverse_lazy('billing:productgroup_list')

    def form_valid(self, form):
        messages.success(self.request, 'Grupo eliminado exitosamente.')
        return super().form_valid(form)


# ──────────────────────────────────────────────
# Supplier (CBV) – staff only
# ──────────────────────────────────────────────

class SupplierListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Supplier
    template_name = 'billing/supplier_list.html'
    context_object_name = 'suppliers'


class SupplierCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model      = Supplier
    form_class = SupplierForm
    template_name = 'billing/supplier_form.html'
    success_url   = reverse_lazy('billing:supplier_list')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor creado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nuevo Proveedor'
        return ctx


class SupplierUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model      = Supplier
    form_class = SupplierForm
    template_name = 'billing/supplier_form.html'
    success_url   = reverse_lazy('billing:supplier_list')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor actualizado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Editar Proveedor'
        return ctx


class SupplierDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model       = Supplier
    template_name = 'billing/supplier_confirm_delete.html'
    success_url   = reverse_lazy('billing:supplier_list')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor eliminado exitosamente.')
        return super().form_valid(form)


# ──────────────────────────────────────────────
# Product (CBV) – staff only
# ──────────────────────────────────────────────

class ProductListView(LoginRequiredMixin, StaffRequiredMixin, ExportMixin, ListView):
    model       = Product
    template_name = 'billing/product_list.html'
    context_object_name = 'products'
    paginate_by     = 10
    export_filename = 'productos'

    def get_export_fields(self):
        visible = set(self.request.session.get('product_visible_columns', PRODUCT_COLUMNS_DEFAULT))
        return [
            (col['label'], col['accessor'])
            for col in PRODUCT_COLUMNS
            if col['key'] in visible and col['accessor'] is not None
        ]

    def get_queryset(self):
        qs = Product.objects.select_related('brand', 'group').prefetch_related('suppliers')
        p  = self.request.GET
        if p.get('code'):      qs = qs.filter(code__icontains=p['code'])
        if p.get('name'):      qs = qs.filter(name__icontains=p['name'])
        if p.get('brand'):     qs = qs.filter(brand__pk=p['brand'])
        if p.get('group'):     qs = qs.filter(group__pk=p['group'])
        if p.get('price_min'): qs = qs.filter(price__gte=p['price_min'])
        if p.get('price_max'): qs = qs.filter(price__lte=p['price_max'])
        if p.get('stock_min'): qs = qs.filter(stock__gte=p['stock_min'])
        if p.get('stock_max'): qs = qs.filter(stock__lte=p['stock_max'])
        if p.get('supplier'):  qs = qs.filter(suppliers__pk=p['supplier']).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['brands']         = Brand.objects.order_by('name')
        ctx['groups']         = ProductGroup.objects.order_by('name')
        ctx['suppliers_list'] = Supplier.objects.order_by('name')

        visible_keys = set(self.request.session.get('product_visible_columns', PRODUCT_COLUMNS_DEFAULT))
        ctx['all_columns']      = [{**col, 'visible': col['key'] in visible_keys, 'accessor': None} for col in PRODUCT_COLUMNS]
        ctx['visible_count']    = len(visible_keys)
        ctx['total_col_count']  = len(PRODUCT_COLUMNS)
        ctx['col_defaults_json']= json.dumps(PRODUCT_COLUMNS_DEFAULT)
        ctx['col_all_keys_json']= json.dumps([c['key'] for c in PRODUCT_COLUMNS])

        params = self.request.GET.copy()
        params.pop('page', None)
        params.pop('export', None)
        ctx['query_params'] = params.urlencode()
        ctx['search']       = self.request.GET
        return ctx


class ProductDetailView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model         = Product
    template_name = 'billing/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.select_related('brand', 'group').prefetch_related('suppliers')


class ProductCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model      = Product
    form_class = ProductForm
    template_name = 'billing/product_form.html'
    success_url   = reverse_lazy('billing:product_list')

    def form_valid(self, form):
        messages.success(self.request, 'Producto creado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nuevo Producto'
        return ctx


class ProductUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model      = Product
    form_class = ProductForm
    template_name = 'billing/product_form.html'
    success_url   = reverse_lazy('billing:product_list')

    def form_valid(self, form):
        messages.success(self.request, 'Producto actualizado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Editar Producto'
        return ctx


class ProductDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model       = Product
    template_name = 'billing/product_confirm_delete.html'
    success_url   = reverse_lazy('billing:product_list')

    def form_valid(self, form):
        messages.success(self.request, 'Producto eliminado exitosamente.')
        return super().form_valid(form)


# ──────────────────────────────────────────────
# Customer (CBV) – staff only
# ──────────────────────────────────────────────

class CustomerListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Customer
    template_name = 'billing/customer_list.html'
    context_object_name = 'customers'


class CustomerCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model      = Customer
    form_class = CustomerForm
    template_name = 'billing/customer_form.html'
    success_url   = reverse_lazy('billing:customer_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente creado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nuevo Cliente'
        return ctx


class CustomerUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model      = Customer
    form_class = CustomerForm
    template_name = 'billing/customer_form.html'
    success_url   = reverse_lazy('billing:customer_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente actualizado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Editar Cliente'
        return ctx


class CustomerDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model       = Customer
    template_name = 'billing/customer_confirm_delete.html'
    success_url   = reverse_lazy('billing:customer_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente eliminado exitosamente.')
        return super().form_valid(form)


# ──────────────────────────────────────────────
# Invoice (FBV) – staff only
# ──────────────────────────────────────────────

@login_required
@staff_required
def invoice_list(request):
    invoices = Invoice.objects.select_related('customer').order_by('-date', '-id')
    return render(request, 'billing/invoice_list.html', {'invoices': invoices})


@login_required
@staff_required
def invoice_create(request):
    form    = InvoiceForm(request.POST or None)
    formset = InvoiceDetailFormSet(request.POST or None)

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        invoice = form.save(commit=False)
        invoice.created_by = request.user
        invoice.save()
        formset.instance = invoice
        formset.save()
        invoice.calculate_totals()
        messages.success(request, f'Factura #{invoice.number} creada exitosamente.')
        return redirect('billing:invoice_detail', pk=invoice.pk)

    return render(request, 'billing/invoice_form.html', {'form': form, 'formset': formset})


@login_required
@staff_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('customer', 'created_by').prefetch_related('details__product'),
        pk=pk,
    )
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})


@login_required
@staff_required
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, 'Factura eliminada exitosamente.')
        return redirect('billing:invoice_list')
    return render(request, 'billing/invoice_confirm_delete.html', {'object': invoice})


# ══════════════════════════════════════════════
# TIENDA (Shop) – clientes registrados
# ══════════════════════════════════════════════

# ── Helpers de carrito (session) ─────────────────────────────────────────

def _get_cart(request):
    return request.session.get('cart', {})


def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def _cart_totals(cart, products_qs):
    """Devuelve (items, subtotal, iva, total) usando los productos del carrito."""
    items    = []
    subtotal = Decimal('0.00')
    for pid, entry in cart.items():
        try:
            prod = products_qs.get(pk=int(pid))
            line = (Decimal(str(entry['qty'])) * prod.price).quantize(Decimal('0.01'))
            items.append({'product': prod, 'qty': entry['qty'], 'line_total': line})
            subtotal += line
        except Product.DoesNotExist:
            pass
    iva   = (subtotal * Decimal('0.15')).quantize(Decimal('0.01'))
    total = (subtotal + iva).quantize(Decimal('0.01'))
    return items, subtotal.quantize(Decimal('0.01')), iva, total


# ── Catálogo ──────────────────────────────────────────────────────────────

@login_required
def shop_catalog(request):
    q        = request.GET.get('q', '')
    group_id = request.GET.get('group', '')
    products = Product.objects.filter(stock__gt=0).select_related('brand', 'group')
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(code__icontains=q)
        )
    if group_id:
        products = products.filter(group__pk=group_id)
    groups = ProductGroup.objects.all()
    cart   = _get_cart(request)
    return render(request, 'billing/shop/catalog.html', {
        'products':   products,
        'groups':     groups,
        'q':          q,
        'group_id':   group_id,
        'cart_count': sum(v['qty'] for v in cart.values()),
    })


# ── Carrito ───────────────────────────────────────────────────────────────

@login_required
def cart_add(request, pk):
    if request.method != 'POST':
        return redirect('billing:shop_catalog')
    product = get_object_or_404(Product, pk=pk, stock__gt=0)
    cart    = _get_cart(request)
    pid     = str(pk)
    qty     = max(1, int(request.POST.get('qty', 1)))
    if pid in cart:
        cart[pid]['qty'] = min(cart[pid]['qty'] + qty, product.stock)
    else:
        cart[pid] = {'qty': min(qty, product.stock)}
    _save_cart(request, cart)
    messages.success(request, f'"{product.name}" agregado al carrito.')
    next_url = request.POST.get('next', '')
    return redirect(next_url) if next_url else redirect('billing:shop_catalog')


@login_required
def cart_view(request):
    cart     = _get_cart(request)
    pids     = [int(k) for k in cart]
    products = Product.objects.filter(pk__in=pids)
    items, subtotal, iva, total = _cart_totals(cart, products)
    return render(request, 'billing/shop/cart.html', {
        'items': items, 'subtotal': subtotal, 'iva': iva, 'total': total,
    })


@login_required
def cart_update(request, pk):
    if request.method != 'POST':
        return redirect('billing:cart_view')
    pid     = str(pk)
    cart    = _get_cart(request)
    product = get_object_or_404(Product, pk=pk)
    qty     = int(request.POST.get('qty', 1))
    if qty < 1:
        cart.pop(pid, None)
        messages.info(request, f'"{product.name}" eliminado del carrito.')
    else:
        cart[pid] = {'qty': min(qty, product.stock)}
    _save_cart(request, cart)
    return redirect('billing:cart_view')


@login_required
def cart_remove(request, pk):
    if request.method != 'POST':
        return redirect('billing:cart_view')
    pid     = str(pk)
    cart    = _get_cart(request)
    product = get_object_or_404(Product, pk=pk)
    cart.pop(pid, None)
    _save_cart(request, cart)
    messages.info(request, f'"{product.name}" eliminado del carrito.')
    return redirect('billing:cart_view')


# ── Checkout ──────────────────────────────────────────────────────────────

@login_required
def shop_checkout(request):
    cart = _get_cart(request)
    if not cart:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('billing:shop_catalog')

    pids     = [int(k) for k in cart]
    products = Product.objects.filter(pk__in=pids)
    items, subtotal, iva, total = _cart_totals(cart, products)

    checkout_form = CheckoutForm(request.POST or None)
    payment_form  = PaymentForm(request.POST or None)

    if request.method == 'POST' and checkout_form.is_valid() and payment_form.is_valid():
        cd     = checkout_form.cleaned_data
        pd     = payment_form.cleaned_data
        method = pd['method']

        # Crear / recuperar cliente
        customer, _ = Customer.objects.get_or_create(
            cedula=cd['cedula'],
            defaults={
                'first_name': request.user.first_name or request.user.username,
                'last_name':  request.user.last_name or '',
                'email':      request.user.email,
                'phone':      cd.get('phone', ''),
                'address':    cd.get('address', ''),
            },
        )

        # Generar número de factura único
        inv_number = f'SHP-{uuid.uuid4().hex[:8].upper()}'

        invoice = Invoice.objects.create(
            number=inv_number,
            customer=customer,
            created_by=request.user,
            status='paid',
        )

        # Crear detalles y descontar stock
        for item in items:
            InvoiceDetail.objects.create(
                invoice=invoice,
                product=item['product'],
                quantity=item['qty'],
                unit_price=item['product'].price,
            )
            item['product'].stock = max(0, item['product'].stock - item['qty'])
            item['product'].save(update_fields=['stock'])

        invoice.calculate_totals()

        # Datos del pago
        reference   = f'PAY-{uuid.uuid4().hex[:12].upper()}'
        payer_name  = request.user.get_full_name() or request.user.username
        payer_email = request.user.email
        card_last4  = ''

        if method == 'card':
            card_last4  = pd.get('card_last4', '')
            payer_name  = pd.get('card_holder') or payer_name
        elif method == 'paypal':
            payer_email = pd.get('paypal_email', payer_email)
        elif method == 'transfer':
            reference = pd.get('transfer_ref') or reference

        payment = Payment.objects.create(
            method=method,
            reference=reference,
            amount=invoice.total,
            status='approved',
            payer_name=payer_name,
            payer_email=payer_email,
            card_last4=card_last4,
        )

        Purchase.objects.create(
            user=request.user,
            invoice=invoice,
            payment=payment,
        )

        # Vaciar carrito
        request.session['cart'] = {}
        request.session.modified = True

        messages.success(request, f'¡Compra realizada! Factura #{invoice.number}')
        return redirect('billing:order_receipt', pk=invoice.pk)

    return render(request, 'billing/shop/checkout.html', {
        'checkout_form': checkout_form,
        'payment_form':  payment_form,
        'items':         items,
        'subtotal':      subtotal,
        'iva':           iva,
        'total':         total,
    })


# ── Mis compras / recibo ──────────────────────────────────────────────────

@login_required
def my_orders(request):
    purchases = (
        Purchase.objects
        .filter(user=request.user)
        .select_related('invoice__customer', 'payment')
        .prefetch_related('invoice__details__product')
        .order_by('-purchased_at')
    )
    return render(request, 'billing/shop/order_history.html', {'purchases': purchases})


@login_required
def order_receipt(request, pk):
    invoice = get_object_or_404(
        Invoice.objects
        .select_related('customer', 'created_by')
        .prefetch_related('details__product'),
        pk=pk,
    )
    if not request.user.is_staff:
        purchase = get_object_or_404(Purchase, invoice=invoice, user=request.user)
    else:
        purchase = getattr(invoice, 'purchase', None)

    return render(request, 'billing/shop/order_receipt.html', {
        'invoice':  invoice,
        'purchase': purchase,
    })
