from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from products.models import Product
from products.serializers import ProductSerializer
from accounts.serializers import UserSerializer

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_id', 'quantity', 
            'total_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return obj.total_price

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'items', 'subtotal', 
            'total_items', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_subtotal(self, obj):
        return obj.subtotal

    def get_total_items(self, obj):
        return obj.total_items


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'quantity', 'price', 
            'total_price', 'product_name', 'product_image',
            'product_description'
        ]
        read_only_fields = fields

    def get_total_price(self, obj):
        return obj.total_price


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', 
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'status', 'status_display',
            'shipping_address', 'shipping_city', 'shipping_state',
            'shipping_country', 'shipping_zip_code', 'payment_method',
            'payment_method_display', 'payment_status', 'payment_reference',
            'subtotal', 'shipping_fee', 'tax', 'total', 'items',
            'created_at', 'updated_at', 'paid_at', 'completed_at'
        ]
        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    shipping_address = serializers.CharField(
        required=True, 
        max_length=500,
        help_text="Full shipping address"
    )
    shipping_city = serializers.CharField(
        required=True, 
        max_length=100,
        help_text="City for shipping"
    )
    shipping_state = serializers.CharField(
        required=True, 
        max_length=100,
        help_text="State/Province/Region"
    )
    shipping_country = serializers.CharField(
        required=True, 
        max_length=100,
        help_text="Country for shipping"
    )
    shipping_zip_code = serializers.CharField(
        required=True, 
        max_length=20,
        help_text="Postal/ZIP code"
    )
    payment_method = serializers.ChoiceField(
        required=True,
        choices=Order.PAYMENT_METHODS,
        help_text="Payment method to use"
    )
    save_shipping_info = serializers.BooleanField(
        default=False,
        help_text="Whether to save shipping info for future orders"
    )

    def validate(self, data):
        request = self.context.get('request')
        cart = request.user.cart
        
        if not cart.items.exists():
            raise serializers.ValidationError(
                {"cart": "Cannot checkout with an empty cart"}
            )
        
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        cart = user.cart
        
        # Calculate order totals
        subtotal = cart.subtotal
        shipping_fee = 0 if subtotal > 50000 else 999  # Free shipping over ₦50,000
        tax = subtotal * 0.08  # 8% tax
        total = subtotal + shipping_fee + tax
        
        # Create order
        order = Order.objects.create(
            user=user,
            shipping_address=validated_data['shipping_address'],
            shipping_city=validated_data['shipping_city'],
            shipping_state=validated_data['shipping_state'],
            shipping_country=validated_data['shipping_country'],
            shipping_zip_code=validated_data['shipping_zip_code'],
            payment_method=validated_data['payment_method'],
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            tax=tax,
            total=total
        )
        
        # Create order items from cart items
        order_items = []
        for cart_item in cart.items.all():
            order_items.append(OrderItem(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
                product_name=cart_item.product.name,
                product_description=cart_item.product.description,
                product_image=cart_item.product.images.first().image.url if cart_item.product.images.exists() else ''
            ))
        
        OrderItem.objects.bulk_create(order_items)
        
        # Clear the cart
        cart.items.all().delete()
        
        # Optionally save shipping info to user profile
        if validated_data.get('save_shipping_info'):
            user.profile.shipping_address = validated_data['shipping_address']
            user.profile.shipping_city = validated_data['shipping_city']
            user.profile.shipping_state = validated_data['shipping_state']
            user.profile.shipping_country = validated_data['shipping_country']
            user.profile.shipping_zip_code = validated_data['shipping_zip_code']
            user.profile.save()
        
        return order


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Order.STATUS_CHOICES,
        required=True,
        help_text="New status for the order"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional notes about the status update"
    )

    def update(self, instance, validated_data):
        new_status = validated_data['status']
        instance.update_status(new_status)
        
        # Add status change note if provided
        if validated_data.get('notes'):
            instance.notes.create(
                content=validated_data['notes'],
                author=self.context['request'].user
            )
            
        return instance