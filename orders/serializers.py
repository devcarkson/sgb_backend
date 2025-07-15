from rest_framework import serializers
from products.serializers import ProductSerializer
from .models import Cart, CartItem, Order, OrderItem

# orders/serializers.py
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price']
    
    def get_total_price(self, obj):
        return obj.product.price * obj.quantity

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'subtotal', 'total']
    
    def get_subtotal(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())
    
    def get_total(self, obj):
        subtotal = self.get_subtotal(obj)
        shipping = 0 if subtotal > 50000 else 999
        tax = subtotal * 0.08
        return subtotal + shipping + tax

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'order_number', 'status', 'created_at', 
            'shipping_address', 'shipping_city', 'shipping_state', 
            'shipping_country', 'shipping_zip_code',
            'payment_method', 'payment_status',
            'subtotal', 'shipping_fee', 'tax', 'total', 'items'
        ]

class CheckoutSerializer(serializers.Serializer):
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField()
    shipping_state = serializers.CharField()
    shipping_country = serializers.CharField()
    shipping_zip_code = serializers.CharField()
    payment_method = serializers.CharField()
    
    def create(self, validated_data):
        request = self.context.get('request')
        cart = request.user.cart
        
        # Calculate totals
        subtotal = sum(item.product.price * item.quantity for item in cart.items.all())
        shipping_fee = 0 if subtotal > 50000 else 999  # 9.99 in minor units
        tax = subtotal * 0.08
        total = subtotal + shipping_fee + tax
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            order_number=self.generate_order_number(),
            **validated_data,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            tax=tax,
            total=total
        )
        
        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
        
        # Clear cart
        cart.items.all().delete()
        
        return order
    
    def generate_order_number(self):
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))