from django.urls import path
from .views import (
    CartDetailView,
    CartItemCreateView,
    CartItemDetailView,
    CartItemBulkUpdateView,
    ClearCartView,
    OrderListView,
    OrderDetailView,
    CheckoutView,
    OrderStatusUpdateView
)

urlpatterns = [
    # Cart endpoints
    path('cart/', CartDetailView.as_view(), name='cart-detail'),
    path('cart/clear/', ClearCartView.as_view(), name='clear-cart'),
    path('cart/items/', CartItemCreateView.as_view(), name='cart-item-create'),
    path('cart/items/bulk-update/', CartItemBulkUpdateView.as_view(), name='cart-item-bulk-update'),
    path('cart/items/<int:pk>/', CartItemDetailView.as_view(), name='cart-item-detail'),
    
    # Order endpoints
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<str:order_number>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
]