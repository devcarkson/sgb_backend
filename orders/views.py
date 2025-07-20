from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Cart, CartItem, Order
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
    CheckoutSerializer
)
from products.models import Product

class CartDetailView(generics.RetrieveAPIView):
    """
    Retrieve the authenticated user's shopping cart
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return Cart.get_or_create_cart(self.request.user)


class CartItemCreateView(generics.CreateAPIView):
    """
    Add a product to the user's cart or update quantity if already exists
    """
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        cart = Cart.get_or_create_cart(self.request.user)
        product = serializer.validated_data['product']
        quantity = serializer.validated_data.get('quantity', 1)
        
        # Update quantity if product already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        # Return the created/updated cart item
        return cart_item

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart_item = self.perform_create(serializer)
        
        # Return the cart item with proper serialization
        return Response(
            CartItemSerializer(cart_item).data,
            status=status.HTTP_201_CREATED
        )


class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update quantity, or remove a cart item
    """
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def perform_destroy(self, instance):
        if instance.cart.user != self.request.user:
            raise permissions.PermissionDenied
        instance.delete()


class CartItemBulkUpdateView(APIView):
    """
    Update multiple cart items at once (for cart page)
    """
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, *args, **kwargs):
        cart = Cart.get_or_create_cart(request.user)
        items_data = request.data.get('items', [])
        
        with transaction.atomic():
            # First validate all items
            for item_data in items_data:
                if 'id' not in item_data or 'quantity' not in item_data:
                    return Response(
                        {"detail": "Each item must have 'id' and 'quantity'"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if not isinstance(item_data['quantity'], int) or item_data['quantity'] < 1:
                    return Response(
                        {"detail": "Quantity must be a positive integer"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Then update all items
            updated_items = []
            for item_data in items_data:
                try:
                    item = CartItem.objects.get(
                        id=item_data['id'],
                        cart=cart
                    )
                    item.quantity = item_data['quantity']
                    item.save()
                    updated_items.append(item)
                except CartItem.DoesNotExist:
                    return Response(
                        {"detail": f"Cart item {item_data['id']} not found in your cart"},
                        status=status.HTTP_404_NOT_FOUND
                    )
        
        return Response(
            CartItemSerializer(updated_items, many=True).data,
            status=status.HTTP_200_OK
        )


class OrderListView(generics.ListAPIView):
    """
    List all orders for the authenticated user
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)\
            .select_related('user')\
            .prefetch_related('items__product')\
            .order_by('-created_at')


class OrderDetailView(generics.RetrieveAPIView):
    """
    Retrieve details of a specific order
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)\
            .select_related('user')\
            .prefetch_related('items__product')


class CheckoutView(generics.CreateAPIView):
    """
    Process checkout and create an order from the cart
    """
    serializer_class = CheckoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            order = serializer.save()
            # Payment initialization (Flutterwave only for now)
            payment_url = None
            reference = order.order_number
            payment_method = order.payment_method
            payment_response = None
            if payment_method == 'flutterwave':
                from payments.services import FlutterwaveService
                try:
                    payment_response = FlutterwaveService.initialize_payment(order)
                    payment_url = payment_response.get('data', {}).get('link')
                except Exception as e:
                    return Response(
                        {"detail": f"Payment initialization failed: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {"detail": f"Payment method '{payment_method}' is not supported yet."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not payment_url:
                return Response(
                    {"detail": "Payment initialization failed: No payment URL returned."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {
                    "payment_url": payment_url,
                    "reference": reference,
                    "order_id": order.id,
                    "order": OrderSerializer(order).data,
                    "status": order.status
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ClearCartView(APIView):
    """
    Clear all items from the user's cart
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        cart = Cart.get_or_create_cart(request.user)
        deleted_count, _ = cart.items.all().delete()
        return Response(
            {"detail": f"Removed {deleted_count} items from your cart"},
            status=status.HTTP_200_OK
        )


class OrderStatusUpdateView(generics.UpdateAPIView):
    """
    Update order status (admin only)
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Order.objects.all()
    lookup_field = 'order_number'

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {"detail": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order.update_status(new_status)
            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )