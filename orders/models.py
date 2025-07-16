from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import uuid
from accounts.models import User
from products.models import Product

class Cart(models.Model):
    """
    Represents a user's shopping cart with automatic creation on user registration.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name="User"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"
        ordering = ['-updated_at']

    def __str__(self):
        return f"Cart #{self.id} - {self.user.email}"

    @property
    def total_items(self):
        """Returns the total quantity of items in cart"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0

    @property
    def subtotal(self):
        """Calculates the subtotal of all cart items"""
        return sum(item.total_price for item in self.items.all())

    @classmethod
    def get_or_create_cart(cls, user):
        """Safely gets or creates a cart for user"""
        cart, created = cls.objects.get_or_create(user=user)
        return cart


class CartItem(models.Model):
    """
    Represents an individual product item in a shopping cart.
    """
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name="Cart"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name="Product"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantity"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ('cart', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quantity}x {self.product.name[:20]} (Cart #{self.cart.id})"

    @property
    def total_price(self):
        """Calculates total price for this cart item"""
        return self.product.price * self.quantity


class Order(models.Model):
    """
    Represents a completed order with payment and shipping information.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('flutterwave', 'Flutterwave'),
        ('paystack', 'Paystack'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="User"
    )
    order_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Order Number"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    
    # Shipping information
    shipping_address = models.TextField(verbose_name="Shipping Address")
    shipping_city = models.CharField(max_length=100, verbose_name="City")
    shipping_state = models.CharField(max_length=100, verbose_name="State")
    shipping_country = models.CharField(max_length=100, verbose_name="Country")
    shipping_zip_code = models.CharField(max_length=20, verbose_name="ZIP Code")
    
    # Payment information
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHODS,
        verbose_name="Payment Method"
    )
    payment_status = models.BooleanField(
        default=False,
        verbose_name="Payment Completed"
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Payment Reference"
    )
    
    # Order totals
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Subtotal"
    )
    shipping_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Shipping Fee"
    )
    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Tax Amount"
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total Amount"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Payment Date"
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Completion Date"
    )

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        """Generate order number on creation"""
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        """Generate a unique order number"""
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"

    @property
    def status_display(self):
        """Get human-readable status"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def update_status(self, new_status, commit=True):
        """Safely update order status with timestamp updates"""
        if new_status in dict(self.STATUS_CHOICES):
            self.status = new_status
            if new_status == 'delivered' and not self.completed_at:
                self.completed_at = timezone.now()
            if commit:
                self.save()


class OrderItem(models.Model):
    """
    Represents a product item within an order, preserving product details at time of purchase.
    """
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name="Order"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name="Product"
    )
    quantity = models.PositiveIntegerField(verbose_name="Quantity")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Unit Price"
    )
    
    # Preserved product details
    product_name = models.CharField(
        max_length=255,
        verbose_name="Product Name (Snapshot)"
    )
    product_image = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Product Image (Snapshot)"
    )
    product_description = models.TextField(
        blank=True,
        verbose_name="Product Description (Snapshot)"
    )

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ['-id']

    def __str__(self):
        return f"{self.quantity}x {self.product_name[:20]} (Order #{self.order.order_number})"

    def save(self, *args, **kwargs):
        """Capture product details at time of order creation"""
        if not self.pk:  # Only on initial creation
            self.product_name = self.product.name
            if self.product.images.exists():
                self.product_image = self.product.images.first().image.url
            self.product_description = self.product.description
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        """Calculate total price for this order item"""
        return self.price * self.quantity


# Signal to automatically create cart when user is created
@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(user=instance)