from django.urls import path
from .views import (
    CartView, AddToCartView, UpdateCartItemView, RemoveFromCartView, 
    ClearCartView, CheckoutView, OrderHistoryView, OrderDetailView
)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', AddToCartView.as_view(), name='add-to-cart'),
    path('cart/item/<int:item_id>/update/', UpdateCartItemView.as_view(), name='update-cart-item'),
    path('cart/item/<int:item_id>/remove/', RemoveFromCartView.as_view(), name='remove-from-cart'),
    path('cart/clear/', ClearCartView.as_view(), name='clear-cart'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),  # Existing
    path('orders/create/', CheckoutView.as_view(), name='order-create'),  # ✅ NEW LINE
    path('orders/', OrderHistoryView.as_view(), name='order-history'),
    path('orders/<str:order_number>/', OrderDetailView.as_view(), name='order-detail'),
]
