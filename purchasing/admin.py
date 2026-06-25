from django.contrib import admin
from .models import Purchase, PurchaseDetail


class PurchaseDetailInline(admin.TabularInline):
    model = PurchaseDetail
    extra = 1
    readonly_fields = ('subtotal',)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'document_number', 'purchase_date', 'total')
    search_fields = ('document_number', 'supplier__name')
    list_filter = ('purchase_date', 'supplier')
    readonly_fields = ('subtotal', 'tax', 'total', 'purchase_date')
    inlines = [PurchaseDetailInline]
