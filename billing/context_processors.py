def cart_count(request):
    """Inyecta cart_count en todos los templates para mostrar el badge del carrito."""
    cart = request.session.get('cart', {})
    return {'cart_count': sum(v['qty'] for v in cart.values())}
