from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem, Order
from .serializers import CartSerializer, OrderSerializer, CheckoutSerializer
from products.models import Product
from payments.services import FlutterwaveService
from orders.signals import send_order_confirmation_email

class CartView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

class AddToCartView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id)
        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response({"detail": "Product added to cart"}, status=status.HTTP_200_OK)

class UpdateCartItemView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, item_id):
        quantity = int(request.data.get('quantity', 1))

        cart_item = get_object_or_404(CartItem, id=item_id, cart=request.user.cart)

        if quantity <= 0:
            cart_item.delete()
            return Response({"detail": "Item removed from cart"}, status=status.HTTP_200_OK)

        cart_item.quantity = quantity
        cart_item.save()

        return Response({"detail": "Cart item updated"}, status=status.HTTP_200_OK)

class RemoveFromCartView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart=request.user.cart)
        cart_item.delete()
        return Response({"detail": "Item removed from cart"}, status=status.HTTP_200_OK)

class ClearCartView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        request.user.cart.items.all().delete()
        return Response({"detail": "Cart cleared"}, status=status.HTTP_200_OK)

class CheckoutView(generics.CreateAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        payment = FlutterwaveService.initialize_payment(order)

        return Response({
            "success": True,
            "order": OrderSerializer(order).data,
            "payment_url": payment.get('data', {}).get('link')
        }, status=status.HTTP_201_CREATED)

class OrderHistoryView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
