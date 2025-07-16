# from django.shortcuts import get_object_or_404
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# from orders.models import Order
# from orders.signals import send_order_confirmation_email
# from django.conf import settings
# from .services import FlutterwaveService

# class PaymentView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request, order_number):
#         order = get_object_or_404(
#             Order, 
#             order_number=order_number,
#             user=request.user
#         )
        
#         payment_response = FlutterwaveService.initialize_payment(order)
        
#         return Response({
#             "payment_link": payment_response.get('data', {}).get('link')
#         })

# class FlutterwaveWebhookView(APIView):
#     def post(self, request):
#         secret_hash = request.headers.get('verif-hash')
#         if secret_hash != settings.FLW_WEBHOOK_HASH:
#             return Response(status=status.HTTP_401_UNAUTHORIZED)

#         data = request.data
#         order_number = data.get('tx_ref')
        
#         try:
#             order = Order.objects.get(order_number=order_number)
#             if data.get('status') == 'successful':
#                 order.payment_status = True
#                 order.status = 'processing'
#                 order.save()
                
#                 # Send confirmation email
#                 send_order_confirmation_email(order)
            
#             return Response(status=status.HTTP_200_OK)
#         except Order.DoesNotExist:


from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from orders.models import Order
from orders.signals import send_order_confirmation_email

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
from .services import FlutterwaveService

class PaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        payment_response = FlutterwaveService.initialize_payment(order)
        return Response({
            "payment_link": payment_response.get('data', {}).get('link')
        }, status=status.HTTP_200_OK)
        

class FlutterwaveWebhookView(APIView):
    authentication_classes = []  # Webhooks are anonymous
    permission_classes = []      # No auth required

    def post(self, request):
        # ✅ Verify the webhook hash
        incoming_hash = request.headers.get('verif-hash')
        if incoming_hash != settings.FLW_WEBHOOK_HASH:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        # ✅ Get the payload
        data = request.data

        tx_ref = data.get('tx_ref')
        status_received = data.get('status')

        # ✅ Debug log (optional, remove in production)
        print("Received Flutterwave webhook:", data)

        # ✅ Check order exists
        try:
            order = Order.objects.get(order_number=tx_ref)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Only update if successful
        if status_received == "successful":
            if not order.payment_status:  # prevent re-processing
                order.payment_status = True
                order.status = "processing"
                order.save()

                send_order_confirmation_email(order)

        return Response({"message": "Webhook processed"}, status=status.HTTP_200_OK)
