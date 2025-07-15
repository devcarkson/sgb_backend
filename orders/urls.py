from django.urls import path
from .views import (
    CartView, AddToCartView, UpdateCartItemView,
    RemoveFromCartView, ClearCartView, CheckoutView,
    OrderHistoryView, OrderDetailView
)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', AddToCartView.as_view(), name='add-to-cart'),
    path('cart/items/<int:item_id>/', UpdateCartItemView.as_view(), name='update-cart-item'),
    path('cart/items/<int:item_id>/remove/', RemoveFromCartView.as_view(), name='remove-cart-item'),
    path('cart/clear/', ClearCartView.as_view(), name='clear-cart'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('orders/', OrderHistoryView.as_view(), name='order-history'),
    path('orders/<str:order_number>/', OrderDetailView.as_view(), name='order-detail'),
]