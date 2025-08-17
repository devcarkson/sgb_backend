from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 
        'order', 
        'gateway', 
        'amount', 
        'currency', 
        'status', 
        'created_at',
        'paid_at'
    ]
    list_filter = [
        'gateway', 
        'status', 
        'currency', 
        'created_at',
        'paid_at'
    ]
    search_fields = [
        'payment_id', 
        'order__order_number', 
        'order__user__email',
        'gateway_transaction_id',
        'gateway_reference'
    ]
    readonly_fields = [
        'payment_id', 
        'created_at', 
        'updated_at',
        'gateway_response'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'payment_id',
                'order',
                'gateway',
                'status'
            )
        }),
        ('Payment Details', {
            'fields': (
                'amount',
                'currency',
                'gateway_transaction_id',
                'gateway_reference'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'paid_at'
            )
        }),
        ('Gateway Response', {
            'fields': ('gateway_response',),
            'classes': ('collapse',)
        })
    )
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of successful payments
        if obj and obj.is_successful:
            return False
        return super().has_delete_permission(request, obj)
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        
        # Make successful payments mostly read-only
        if obj and obj.is_successful:
            readonly_fields.extend([
                'order',
                'gateway',
                'amount',
                'currency',
                'gateway_transaction_id',
                'gateway_reference'
            ])
        
        return readonly_fields
