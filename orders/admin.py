# orders/admin.py
from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'payment_status', 'total', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    inlines = [OrderItemInline]

admin.site.register(Cart)
admin.site.register(CartItem)
