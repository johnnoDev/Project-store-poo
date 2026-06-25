from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Auth
    path('accounts/signup/', views.SignUpView.as_view(), name='signup'),

    # Brand (FBV)
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/new/', views.brand_create, name='brand_create'),
    path('brands/<int:pk>/edit/', views.brand_edit, name='brand_edit'),
    path('brands/<int:pk>/delete/', views.brand_delete, name='brand_delete'),

    # ProductGroup (CBV)
    path('groups/', views.ProductGroupListView.as_view(), name='productgroup_list'),
    path('groups/new/', views.ProductGroupCreateView.as_view(), name='productgroup_create'),
    path('groups/<int:pk>/edit/', views.ProductGroupUpdateView.as_view(), name='productgroup_edit'),
    path('groups/<int:pk>/delete/', views.ProductGroupDeleteView.as_view(), name='productgroup_delete'),

    # Supplier (CBV)
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/new/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),

    # Product (CBV)
    path('products/columns/', views.product_columns_save, name='product_columns_save'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/new/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),

    # Customer (CBV)
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/new/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),

    # Invoice (FBV)
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/new/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),

    # Shop – tienda para clientes
    path('shop/', views.shop_catalog, name='shop_catalog'),
    path('shop/cart/', views.cart_view, name='cart_view'),
    path('shop/cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('shop/cart/update/<int:pk>/', views.cart_update, name='cart_update'),
    path('shop/cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('shop/checkout/', views.shop_checkout, name='shop_checkout'),
    path('shop/orders/', views.my_orders, name='my_orders'),
    path('shop/orders/<int:pk>/receipt/', views.order_receipt, name='order_receipt'),
]
