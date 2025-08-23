from django.db import models
from django.utils import timezone
from orders.models import Order
import uuid
import logging
from .realtime import broadcast_realtime_update

logger = logging.getLogger(__name__)

class Payment(models.Model):
    """
    Model to track payment transactions
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_GATEWAY_CHOICES = [
        ('flutterwave', 'Flutterwave'),
        ('paystack', 'Paystack'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    # Basic payment info
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Order"
    )
    payment_id = models.CharField(
        max_length=100,
        unique=True,
        default=uuid.uuid4,
        verbose_name="Payment ID"
    )
    
    # Payment gateway details
    gateway = models.CharField(
        max_length=50,
        choices=PAYMENT_GATEWAY_CHOICES,
        verbose_name="Payment Gateway"
    )
    gateway_transaction_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Gateway Transaction ID"
    )
    gateway_reference = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Gateway Reference"
    )
    
    # Payment amounts
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Payment Amount"
    )
    currency = models.CharField(
        max_length=3,
        default='NGN',
        verbose_name="Currency"
    )
    
    # Payment status and timestamps
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name="Payment Status"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Payment Date"
    )
    
    # Gateway response data (for debugging and records)
    gateway_response = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Gateway Response Data"
    )
    
    # Additional fields for better tracking
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Retry Count"
    )
    last_error = models.TextField(
        blank=True,
        null=True,
        verbose_name="Last Error Message"
    )
    
    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['gateway_transaction_id']),
            models.Index(fields=['status']),
            models.Index(fields=['order', 'status']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.order.order_number} ({self.status})"
    
    def mark_as_successful(self, gateway_transaction_id=None, gateway_response=None):
        """Mark payment as successful and update related order"""
        self.status = 'successful'
        self.paid_at = timezone.now()
        
        if gateway_transaction_id:
            self.gateway_transaction_id = gateway_transaction_id
        
        if gateway_response:
            self.gateway_response = gateway_response
        
        self.save()
        
        # Update the related order
        if not self.order.payment_status:
            self.order.payment_status = True
            self.order.payment_reference = self.payment_id
            self.order.paid_at = self.paid_at
            
            # Update order status to processing if it's still pending
            if self.order.status == 'pending':
                self.order.status = 'processing'
            
            self.order.save()
            
            # Clear the cart after successful payment
            self._clear_user_cart()
            
            logger.info(f"Payment {self.payment_id} marked as successful for order {self.order.order_number}")

        # Realtime push for payment success
        from .serializers import PaymentSerializer
        payment_data = PaymentSerializer(self).data
        broadcast_realtime_update(
            user_id=str(self.order.user.id),
            data={
                "type": "payment_update",
                "payment": payment_data,
                "order_number": self.order.order_number,
                "status": "successful"
            }
        )
    
    def mark_as_failed(self, gateway_response=None, error_message=None):
        """Mark payment as failed"""
        self.status = 'failed'
        
        if gateway_response:
            self.gateway_response = gateway_response
            
        if error_message:
            self.last_error = error_message
        
        self.save()
        logger.warning(f"Payment {self.payment_id} marked as failed for order {self.order.order_number}")

        # Realtime push for payment failure
        from .serializers import PaymentSerializer
        payment_data = PaymentSerializer(self).data
        broadcast_realtime_update(
            user_id=str(self.order.user.id),
            data={
                "type": "payment_update",
                "payment": payment_data,
                "order_number": self.order.order_number,
                "status": "failed"
            }
        )
    
    def increment_retry_count(self):
        """Increment retry count for failed payments"""
        self.retry_count += 1
        self.save()
    
    def _clear_user_cart(self):
        """Clear user's cart after successful payment"""
        try:
            cart = self.order.user.cart
            deleted_count, _ = cart.items.all().delete()
            logger.info(f"Cleared {deleted_count} items from cart for user {self.order.user.email}")
        except Exception as e:
            logger.error(f"Error clearing cart for user {self.order.user.email}: {str(e)}")
    
    @property
    def is_successful(self):
        return self.status == 'successful'
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_failed(self):
        return self.status == 'failed'
    
    @property
    def can_retry(self):
        """Check if payment can be retried (max 3 retries)"""
        return self.is_failed and self.retry_count < 3
    
    def get_display_status(self):
        """Get human-readable status"""
        return dict(self.PAYMENT_STATUS_CHOICES).get(self.status, self.status)