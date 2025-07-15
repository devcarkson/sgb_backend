from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
from orders.signals import send_order_confirmation_email
from django.conf import settings
from .services import FlutterwaveService

class PaymentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, order_number):
        order = get_object_or_404(
            Order, 
            order_number=order_number,
            user=request.user
        )
        
        payment_response = FlutterwaveService.initialize_payment(order)
        
        return Response({
            "payment_link": payment_response.get('data', {}).get('link')
        })

class FlutterwaveWebhookView(APIView):
    def post(self, request):
        secret_hash = request.headers.get('verif-hash')
        if secret_hash != settings.FLW_WEBHOOK_HASH:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        data = request.data
        order_number = data.get('tx_ref')
        
        try:
            order = Order.objects.get(order_number=order_number)
            if data.get('status') == 'successful':
                order.payment_status = True
                order.status = 'processing'
                order.save()
                
                # Send confirmation email
                send_order_confirmation_email(order)
            
            return Response(status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)