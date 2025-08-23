from rest_framework import serializers
from .models import Payment
from orders.serializers import OrderSerializer

class PaymentSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    gateway_display = serializers.CharField(source='get_gateway_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'payment_id', 'order', 'gateway', 'gateway_display',
            'gateway_transaction_id', 'gateway_reference', 'amount',
            'currency', 'status', 'status_display', 'created_at',
            'updated_at', 'paid_at', 'gateway_response'
        ]
        read_only_fields = fields

class PaymentInitializationSerializer(serializers.Serializer):
    order_number = serializers.CharField(
        max_length=20,
        help_text="Order number to initialize payment for"
    )
    
    def validate_order_number(self, value):
        from orders.models import Order
        request = self.context.get('request')
        
        try:
            order = Order.objects.get(
                order_number=value,
                user=request.user
            )
            
            if order.payment_status:
                raise serializers.ValidationError("Order is already paid")
                
            # Check if there's already a pending payment
            existing_payment = Payment.objects.filter(
                order=order,
                status='pending'
            ).first()
            
            if existing_payment:
                raise serializers.ValidationError("Payment is already in progress for this order")
                
            return value
            
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found")

class PaymentVerificationSerializer(serializers.Serializer):
    payment_id = serializers.CharField(
        max_length=100,
        help_text="Payment ID to verify"
    )
    transaction_id = serializers.CharField(
        max_length=200,
        required=False,
        help_text="Flutterwave transaction ID (optional)"
    )

class PaymentCallbackSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="Payment status from callback")
    tx_ref = serializers.CharField(help_text="Transaction reference")
    transaction_id = serializers.CharField(help_text="Flutterwave transaction ID")