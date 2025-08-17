from django.db import models
from django.utils import timezone
from orders.models import Order
import uuid

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
    
    def mark_as_failed(self, gateway_response=None):
        """Mark payment as failed"""
        self.status = 'failed'
        
        if gateway_response:
            self.gateway_response = gateway_response
        
        self.save()
    
    @property
    def is_successful(self):
        return self.status == 'successful'
    
    @property
    def is_pending(self):
        return self.status == 'pending'
