from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Payment
import json

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 'order_link', 'user_email', 'gateway', 
        'amount', 'currency', 'status_badge', 'retry_count',
        'created_at', 'paid_at'
    ]
    list_filter = [
        'status', 'gateway', 'currency', 'created_at', 
        'paid_at', 'retry_count'
    ]
    search_fields = [
        'payment_id', 'order__order_number', 'order__user__email',
        'gateway_transaction_id', 'gateway_reference'
    ]
    readonly_fields = [
        'payment_id', 'created_at', 'updated_at', 'paid_at',
        'gateway_response_formatted', 'order_details'
    ]
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'payment_id', 'order', 'gateway', 'amount', 'currency'
            )
        }),
        ('Status & Tracking', {
            'fields': (
                'status', 'retry_count', 'last_error',
                'created_at', 'updated_at', 'paid_at'
            )
        }),
        ('Gateway Details', {
            'fields': (
                'gateway_transaction_id', 'gateway_reference',
                'gateway_response_formatted'
            ),
            'classes': ('collapse',)
        }),
        ('Order Details', {
            'fields': ('order_details',),
            'classes': ('collapse',)
        })
    )
    
    def user_email(self, obj):
        return obj.order.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'order__user__email'
    
    def order_link(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_link.short_description = 'Order'
    order_link.admin_order_field = 'order__order_number'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'successful': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'refunded': '#fd7e14'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def gateway_response_formatted(self, obj):
        if obj.gateway_response:
            try:
                formatted = json.dumps(obj.gateway_response, indent=2)
                return format_html('<pre style="font-size: 12px;">{}</pre>', formatted)
            except:
                return str(obj.gateway_response)
        return 'No response data'
    gateway_response_formatted.short_description = 'Gateway Response'
    
    def order_details(self, obj):
        order = obj.order
        details = f"""
        <strong>Order Number:</strong> {order.order_number}<br>
        <strong>User:</strong> {order.user.email}<br>
        <strong>Order Status:</strong> {order.status}<br>
        <strong>Order Total:</strong> {order.currency if hasattr(order, 'currency') else 'NGN'} {order.total}<br>
        <strong>Payment Status:</strong> {'Paid' if order.payment_status else 'Unpaid'}<br>
        <strong>Created:</strong> {order.created_at}<br>
        """
        return mark_safe(details)
    order_details.short_description = 'Order Information'
    
    actions = ['mark_as_successful', 'mark_as_failed', 'retry_payment']
    
    def mark_as_successful(self, request, queryset):
        count = 0
        for payment in queryset:
            if payment.status != 'successful':
                payment.mark_as_successful()
                count += 1
        self.message_user(request, f'{count} payments marked as successful.')
    mark_as_successful.short_description = 'Mark selected payments as successful'
    
    def mark_as_failed(self, request, queryset):
        count = 0
        for payment in queryset:
            if payment.status not in ['successful', 'failed']:
                payment.mark_as_failed(error_message='Manually marked as failed by admin')
                count += 1
        self.message_user(request, f'{count} payments marked as failed.')
    mark_as_failed.short_description = 'Mark selected payments as failed'
    
    def retry_payment(self, request, queryset):
        count = 0
        for payment in queryset:
            if payment.can_retry:
                try:
                    from .services import FlutterwaveService
                    FlutterwaveService.retry_failed_payment(payment)
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Error retrying payment {payment.payment_id}: {str(e)}', level='ERROR')
        self.message_user(request, f'{count} payments retried.')
    retry_payment.short_description = 'Retry selected failed payments'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'order__user')
    
    def has_add_permission(self, request):
        # Payments should only be created through the payment flow
        return False