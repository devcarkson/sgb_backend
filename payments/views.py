from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
from orders.signals import send_order_confirmation_email
from .services import FlutterwaveService
from .models import Payment
import logging

logger = logging.getLogger(__name__)

class PaymentView(APIView):
    """Initialize payment for an order"""
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        try:
            order = get_object_or_404(
                Order, 
                order_number=order_number, 
                user=request.user
            )
            
            # Check if order is already paid
            if order.payment_status:
                return Response({
                    "error": "Order is already paid"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if there's already a pending payment
            existing_payment = Payment.objects.filter(
                order=order,
                status='pending'
            ).first()
            
            if existing_payment:
                return Response({
                    "error": "Payment is already in progress for this order"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Initialize payment
            payment_response = FlutterwaveService.initialize_payment(order)
            
            return Response({
                "payment_link": payment_response.get('data', {}).get('link'),
                "payment_id": payment_response.get('data', {}).get('payment_id'),
                "tx_ref": payment_response.get('data', {}).get('tx_ref')
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Payment initialization error: {str(e)}")
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class PaymentVerificationView(APIView):
    """Verify payment status"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, payment_id):
        try:
            payment = get_object_or_404(
                Payment,
                payment_id=payment_id,
                order__user=request.user
            )
            
            # If payment is already successful, return success
            if payment.is_successful:
                return Response({
                    "status": "successful",
                    "payment": {
                        "id": str(payment.payment_id),
                        "amount": str(payment.amount),
                        "currency": payment.currency,
                        "status": payment.status,
                        "paid_at": payment.paid_at
                    },
                    "order": {
                        "id": payment.order.id,
                        "order_number": payment.order.order_number,
                        "status": payment.order.status
                    }
                })
            
            # If payment is pending, try to verify with Flutterwave
            if payment.is_pending and payment.gateway_transaction_id:
                try:
                    verification_data = FlutterwaveService.verify_payment(
                        payment.gateway_transaction_id
                    )
                    
                    if (verification_data.get('status') == 'success' and 
                        verification_data.get('data', {}).get('status') == 'successful'):
                        
                        payment.mark_as_successful(
                            gateway_transaction_id=payment.gateway_transaction_id,
                            gateway_response=verification_data
                        )
                        
                        return Response({
                            "status": "successful",
                            "payment": {
                                "id": str(payment.payment_id),
                                "amount": str(payment.amount),
                                "currency": payment.currency,
                                "status": payment.status,
                                "paid_at": payment.paid_at
                            },
                            "order": {
                                "id": payment.order.id,
                                "order_number": payment.order.order_number,
                                "status": payment.order.status
                            }
                        })
                except Exception as e:
                    logger.error(f"Payment verification error: {str(e)}")
            
            # Return current payment status
            return Response({
                "status": payment.status,
                "payment": {
                    "id": str(payment.payment_id),
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                    "status": payment.status,
                    "created_at": payment.created_at
                },
                "order": {
                    "id": payment.order.id,
                    "order_number": payment.order.order_number,
                    "status": payment.order.status
                }
            })
            
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class FlutterwaveWebhookView(APIView):
    """Handle Flutterwave webhook notifications"""
    authentication_classes = []  # Webhooks are anonymous
    permission_classes = []      # No auth required

    def post(self, request):
        try:
            # Verify the webhook hash
            incoming_hash = request.headers.get('verif-hash')
            if incoming_hash != settings.FLW_WEBHOOK_HASH:
                logger.warning("Invalid webhook hash received")
                return Response({
                    "error": "Unauthorized"
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Get the payload
            data = request.data
            logger.info(f"Received Flutterwave webhook: {data}")

            # Process the webhook
            success = FlutterwaveService.process_webhook(data)
            
            if success:
                # Send order confirmation email if payment was successful
                tx_ref = data.get('tx_ref')
                if data.get('status') == 'successful' and tx_ref:
                    try:
                        payment = Payment.objects.get(payment_id=tx_ref)
                        if payment.is_successful:
                            send_order_confirmation_email(payment.order)
                    except Payment.DoesNotExist:
                        logger.error(f"Payment not found for tx_ref: {tx_ref}")
                
                return Response({
                    "message": "Webhook processed successfully"
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Webhook processing failed"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return Response({
                "error": "Internal server error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
