from decimal import Decimal
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count

from .models import Purchase, PurchaseDetail
from .forms import PurchaseForm, PurchaseDetailFormSet
from billing.models import Supplier


def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Solo el personal autorizado puede acceder a esa sección.')
            return redirect('billing:shop_catalog')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@staff_required
def purchase_list(request):
    purchases = Purchase.objects.select_related('supplier')

    supplier_id = request.GET.get('supplier', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    year = request.GET.get('year', '')

    if supplier_id:
        purchases = purchases.filter(supplier__id=supplier_id)
    if date_from:
        purchases = purchases.filter(purchase_date__date__gte=date_from)
    if date_to:
        purchases = purchases.filter(purchase_date__date__lte=date_to)
    if year:
        purchases = purchases.filter(purchase_date__year=year)

    suppliers = Supplier.objects.order_by('name')

    return render(request, 'purchasing/purchase_list.html', {
        'purchases': purchases,
        'suppliers': suppliers,
        'filter_supplier': supplier_id,
        'filter_date_from': date_from,
        'filter_date_to': date_to,
        'filter_year': year,
    })


@login_required
@staff_required
def purchase_create(request):
    form = PurchaseForm(request.POST or None)
    formset = PurchaseDetailFormSet(request.POST or None)

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        purchase = form.save()
        formset.instance = purchase
        formset.save()
        subtotal = sum(d.subtotal for d in purchase.details.all())
        purchase.subtotal = subtotal
        purchase.tax = subtotal * Decimal('0.15')
        purchase.total = purchase.subtotal + purchase.tax
        purchase.save()
        messages.success(request, f'Purchase #{purchase.id} created successfully.')
        return redirect('purchasing:purchase_detail', pk=purchase.pk)

    return render(request, 'purchasing/purchase_form.html', {'form': form, 'formset': formset})


@login_required
@staff_required
def purchase_detail(request, pk):
    purchase = get_object_or_404(
        Purchase.objects.select_related('supplier').prefetch_related('details__product'),
        pk=pk,
    )
    return render(request, 'purchasing/purchase_detail.html', {'purchase': purchase})


@login_required
@staff_required
def purchase_delete(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    if request.method == 'POST':
        purchase.delete()
        messages.success(request, 'Purchase deleted successfully.')
        return redirect('purchasing:purchase_list')
    return render(request, 'purchasing/purchase_confirm_delete.html', {'object': purchase})


@login_required
@staff_required
def purchase_cost_report(request):
    report = (
        PurchaseDetail.objects
        .values('product', 'product__code', 'product__name')
        .annotate(avg_cost=Avg('unit_cost'), purchase_count=Count('id'))
        .order_by('product__name')
    )
    return render(request, 'purchasing/purchase_cost_report.html', {'report': report})
