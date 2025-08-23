from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from orders.models import Order, Cart
from payments.models import Payment
from decimal import Decimal
from django.contrib.auth.decorators import login_required

def debug_order_total(request, order_number):
    """Debug endpoint to check order total calculation"""
    try:
        order = get_object_or_404(Order, order_number=order_number)
        
        # Get all payments for this order
        payments = Payment.objects.filter(order=order).order_by('-created_at')
        
        payment_data = []
        for payment in payments:
            payment_data.append({
                'payment_id': str(payment.payment_id),
                'amount': str(payment.amount),
                'status': payment.status,
                'created_at': payment.created_at.isoformat(),
                'gateway_response': payment.gateway_response
            })
        
        return JsonResponse({
            'order_number': order.order_number,
            'order_id': order.id,
            'subtotal': str(order.subtotal),
            'shipping_fee': str(order.shipping_fee),
            'tax': str(order.tax),
            'total': str(order.total),
            'shipping_city': order.shipping_city,
            'shipping_state': order.shipping_state,
            'payment_method': order.payment_method,
            'payments': payment_data,
            'calculation_check': {
                'calculated_total': str(order.subtotal + order.shipping_fee + order.tax),
                'stored_total': str(order.total),
                'match': str(order.subtotal + order.shipping_fee + order.tax) == str(order.total)
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def debug_cart_total(request):
    """Debug endpoint to check cart total calculation"""
    try:
        cart = Cart.get_or_create_cart(request.user)
        
        # Get cart items with details
        cart_items = []
        total_calculated = Decimal('0')
        
        for item in cart.items.all():
            item_total = item.total_price
            total_calculated += item_total
            cart_items.append({
                'product_id': item.product.id,
                'product_name': item.product.name,
                'product_price': str(item.product.price),
                'quantity': item.quantity,
                'item_total': str(item_total)
            })
        
        return JsonResponse({
            'cart_id': cart.id,
            'user_email': request.user.email,
            'total_items': cart.total_items,
            'cart_subtotal_property': str(cart.subtotal),
            'calculated_total': str(total_calculated),
            'match': str(cart.subtotal) == str(total_calculated),
            'items': cart_items
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)