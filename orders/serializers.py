from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from products.models import Product
from products.serializers import ProductSerializer
from accounts.serializers import UserSerializer
from accounts.models import Address
from decimal import Decimal

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
    total = serializers.SerializerMethodField()  # Add total field for frontend compatibility
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'items', 'subtotal', 'total',
            'total_items', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_subtotal(self, obj):
        return obj.subtotal
    
    def get_total(self, obj):
        # Return the same as subtotal for frontend compatibility
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
    first_name = serializers.CharField(
        required=True,
        max_length=150,
        help_text="First name of the recipient"
    )
    last_name = serializers.CharField(
        required=True,
        max_length=150,
        help_text="Last name of the recipient"
    )
    phone = serializers.CharField(
        required=False,
        max_length=20,
        help_text="Phone number for delivery coordination"
    )
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
        required=False, 
        allow_blank=True,
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

    def _calculate_shipping_fee(self, subtotal, state, city):
        """Calculate shipping fee based on location and order value"""
        # Only operate in Lagos State
        if not state or state.lower() not in ['lagos', 'lagos state']:
            raise serializers.ValidationError({
                "shipping_state": "We currently only deliver within Lagos State. Please use WhatsApp order for other locations."
            })
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Calculating shipping - Subtotal: {subtotal}, State: {state}, City: {city}")
        
        # Free shipping for orders over ₦100,000 (increased threshold)
        if subtotal >= Decimal('100000'):
            logger.info(f"Free shipping applied - subtotal {subtotal} >= 100000")
            return Decimal('0')
        
        # Lagos Island areas (₦4,500 shipping)
        lagos_island_areas = [
            'apapa', 'lagos island', 'lagos mainland', 'surulere', 'yaba', 'ebute metta',
            'victoria island', 'ikoyi', 'banana island', 'lekki phase 1', 'lekki phase 2',
            'ajah', 'eti-osa', 'ibeju-lekki', 'epe', 'badagry', 'vi', 'lekki'
        ]
        
        # Check if it's Lagos Island area (₦4,500)
        if city:
            city_lower = city.lower()
            for island_area in lagos_island_areas:
                if island_area in city_lower or city_lower in island_area:
                    logger.info(f"Lagos Island shipping applied for city: {city}")
                    return Decimal('4500')  # ₦4,500 for Lagos Island
        
        # Default to Lagos Mainland (₦3,500)
        logger.info(f"Lagos Mainland shipping applied for city: {city}")
        return Decimal('3500')  # ₦3,500 for Lagos Mainland

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        cart = user.cart

        # Update user's first and last name if provided
        user.first_name = validated_data['first_name']
        user.last_name = validated_data['last_name']
        user.save()
        
        # Calculate order totals
        subtotal = cart.subtotal
        
        # Shipping fee calculation based on location and subtotal
        shipping_fee = self._calculate_shipping_fee(subtotal, validated_data.get('shipping_state', ''), validated_data.get('shipping_city', ''))
        
        # No tax for now (can be enabled later if needed)
        tax = Decimal('0')
        total = subtotal + shipping_fee + tax
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Order calculation - Subtotal: {subtotal}, Shipping: {shipping_fee}, Tax: {tax}, Total: {total}")
        logger.info(f"Shipping details - State: {validated_data.get('shipping_state')}, City: {validated_data.get('shipping_city')}")
        
        # Create order
        order = Order.objects.create(
            user=user,
            shipping_address=validated_data['shipping_address'],
            shipping_city=validated_data['shipping_city'],
            shipping_state=validated_data['shipping_state'],
            shipping_country=validated_data['shipping_country'],
            shipping_zip_code=validated_data.get('shipping_zip_code', ''),
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
        # cart.items.all().delete()  # <-- Do not clear cart here! Only clear after payment is successful
        
        # Automatically save shipping info as address if save_shipping_info is True
        if validated_data.get('save_shipping_info'):
            # Check if this exact address already exists
            existing_address = Address.objects.filter(
                user=user,
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                street=validated_data['shipping_address'],
                city=validated_data['shipping_city'],
                state=validated_data['shipping_state'],
                country=validated_data['shipping_country']
            ).first()
            
            if not existing_address:
                # Determine if this should be the default address
                is_default = not Address.objects.filter(user=user).exists()
                
                # Create new address
                Address.objects.create(
                    user=user,
                    type='home',  # Default to home address
                    first_name=validated_data['first_name'],
                    last_name=validated_data['last_name'],
                    phone=validated_data.get('phone', ''),
                    street=validated_data['shipping_address'],
                    city=validated_data['shipping_city'],
                    state=validated_data['shipping_state'],
                    country=validated_data['shipping_country'],
                    zip_code=validated_data.get('shipping_zip_code', ''),
                    is_default=is_default
                )
        
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