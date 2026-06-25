from django.contrib import admin
from .models import (
    Brand, ProductGroup, Supplier, Product,
    Customer, CustomerProfile, Invoice, InvoiceDetail,
)


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    extra = 1


class InvoiceDetailInline(admin.TabularInline):
    model = InvoiceDetail
    extra = 1
    readonly_fields = ('subtotal',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'ruc', 'phone', 'email')
    search_fields = ('name', 'ruc')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'brand', 'group', 'price', 'stock')
    search_fields = ('code', 'name')
    list_filter = ('brand', 'group')
    filter_horizontal = ('suppliers',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('cedula', 'last_name', 'first_name', 'email', 'phone')
    search_fields = ('cedula', 'last_name', 'first_name')
    inlines = [CustomerProfileInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'customer', 'date', 'status', 'subtotal', 'iva', 'total')
    search_fields = ('number', 'customer__last_name', 'customer__cedula')
    list_filter = ('status', 'date')
    readonly_fields = ('subtotal', 'iva', 'total', 'date')
    inlines = [InvoiceDetailInline]
