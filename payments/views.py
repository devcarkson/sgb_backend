import json
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from orders.models import Order
from orders.signals import send_order_confirmation_email
from .services import FlutterwaveService
from .models import Payment
from .serializers import (
    PaymentSerializer, 
    PaymentInitializationSerializer,
    PaymentVerificationSerializer,
    PaymentCallbackSerializer
)
import logging

logger = logging.getLogger(__name__)

class PaymentRateThrottle(UserRateThrottle):
    scope = 'payment'
    rate = '10/min'  # 10 payment requests per minute per user

class WebhookRateThrottle(AnonRateThrottle):
    scope = 'webhook'
    rate = '100/min'  # 100 webhook requests per minute

@method_decorator(never_cache, name='dispatch')
class PaymentInitializeView(APIView):
    """Initialize payment for an order"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [PaymentRateThrottle]

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
                    "error": "Order is already paid",
                    "order_number": order.order_number,
                    "payment_status": True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if there's already a pending payment
            existing_payment = Payment.objects.filter(
                order=order,
                status='pending'
            ).first()
            
            if existing_payment:
                # Try to reuse existing payment if it has a valid link
                if (existing_payment.gateway_response and 
                    existing_payment.gateway_response.get('data', {}).get('link')):
                    return Response({
                        "payment_link": existing_payment.gateway_response['data']['link'],
                        "payment_id": str(existing_payment.payment_id),
                        "tx_ref": str(existing_payment.payment_id),
                        "order_number": order.order_number,
                        "amount": str(existing_payment.amount),
                        "currency": existing_payment.currency
                    }, status=status.HTTP_200_OK)
            
            # Initialize new payment
            payment_response = FlutterwaveService.initialize_payment(order)
            
            return Response({
                "payment_link": payment_response.get('data', {}).get('link'),
                "payment_id": payment_response.get('data', {}).get('payment_id'),
                "tx_ref": payment_response.get('data', {}).get('tx_ref'),
                "order_number": order.order_number,
                "amount": str(order.total),
                "currency": "NGN"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Payment initialization error for order {order_number}: {str(e)}")
            return Response({
                "error": str(e),
                "order_number": order_number
            }, status=status.HTTP_400_BAD_REQUEST)

# Keep the old PaymentView for backward compatibility
@method_decorator(never_cache, name='dispatch')
class PaymentView(PaymentInitializeView):
    """Legacy payment initialization view - redirects to PaymentInitializeView"""
    pass

@method_decorator(never_cache, name='dispatch')
class PaymentVerificationView(APIView):
    """Verify payment status"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [PaymentRateThrottle]
    
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
                    "payment": PaymentSerializer(payment).data,
                    "message": "Payment completed successfully"
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
                            "payment": PaymentSerializer(payment).data,
                            "message": "Payment verified and completed successfully"
                        })
                except Exception as e:
                    logger.error(f"Payment verification error: {str(e)}")
            
            # Return current payment status
            return Response({
                "status": payment.status,
                "payment": PaymentSerializer(payment).data,
                "message": f"Payment is currently {payment.status}"
            })
            
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(never_cache, name='dispatch')
class PaymentCallbackView(APIView):
    """Handle payment callback from Flutterwave"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Handle GET callback from Flutterwave"""
        try:
            tx_ref = request.GET.get('tx_ref')
            transaction_id = request.GET.get('transaction_id')
            status_param = request.GET.get('status')
            
            if not tx_ref:
                return Response({
                    "error": "Missing transaction reference"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                payment = Payment.objects.get(
                    payment_id=tx_ref,
                    order__user=request.user
                )
            except Payment.DoesNotExist:
                return Response({
                    "error": "Payment not found"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # If payment is already successful, return success
            if payment.is_successful:
                return Response({
                    "status": "successful",
                    "payment": PaymentSerializer(payment).data,
                    "redirect_url": f"{settings.FRONTEND_URL}/orders/{payment.order.id}"
                })
            
            # Verify payment with Flutterwave if transaction_id is provided
            if transaction_id and status_param == 'successful':
                try:
                    verification_data = FlutterwaveService.verify_payment(transaction_id)
                    
                    if (verification_data.get('status') == 'success' and 
                        verification_data.get('data', {}).get('status') == 'successful'):
                        
                        payment.mark_as_successful(
                            gateway_transaction_id=transaction_id,
                            gateway_response=verification_data
                        )
                        
                        return Response({
                            "status": "successful",
                            "payment": PaymentSerializer(payment).data,
                            "redirect_url": f"{settings.FRONTEND_URL}/orders/{payment.order.id}"
                        })
                except Exception as e:
                    logger.error(f"Callback verification error: {str(e)}")
            
            # Return current status
            return Response({
                "status": payment.status,
                "payment": PaymentSerializer(payment).data,
                "redirect_url": f"{settings.FRONTEND_URL}/payment/status/{payment.payment_id}"
            })
            
        except Exception as e:
            logger.error(f"Payment callback error: {str(e)}")
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(never_cache, name='dispatch')
class PaymentStatusView(APIView):
    """Get payment status for polling"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [PaymentRateThrottle]
    
    def get(self, request, payment_id):
        try:
            payment = get_object_or_404(
                Payment,
                payment_id=payment_id,
                order__user=request.user
            )
            
            return Response({
                "payment": PaymentSerializer(payment).data,
                "order": {
                    "id": payment.order.id,
                    "order_number": payment.order.order_number,
                    "status": payment.order.status,
                    "total": str(payment.order.total)
                }
            })
            
        except Exception as e:
            logger.error(f"Payment status error: {str(e)}")
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(never_cache, name='dispatch')
class PaymentRetryView(APIView):
    """Retry a failed payment"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [PaymentRateThrottle]
    
    def post(self, request, payment_id):
        try:
            payment = get_object_or_404(
                Payment,
                payment_id=payment_id,
                order__user=request.user
            )
            
            if not payment.can_retry:
                return Response({
                    "error": "Payment cannot be retried",
                    "reason": "Maximum retries reached or payment not failed"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Retry the payment
            payment_response = FlutterwaveService.retry_failed_payment(payment)
            
            return Response({
                "payment_link": payment_response.get('data', {}).get('link'),
                "payment_id": payment_response.get('data', {}).get('payment_id'),
                "tx_ref": payment_response.get('data', {}).get('tx_ref'),
                "retry_count": payment.retry_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Payment retry error: {str(e)}")
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(never_cache, name='dispatch')
class PaymentListView(generics.ListAPIView):
    """List user's payments"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(
            order__user=self.request.user
        ).select_related('order').order_by('-created_at')

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class FlutterwaveWebhookView(APIView):
    """Handle Flutterwave webhook notifications with enhanced security"""
    authentication_classes = []  # Webhooks are anonymous
    permission_classes = []      # No auth required
    throttle_classes = [WebhookRateThrottle]

    def post(self, request):
        try:
            # Get raw body for signature validation
            raw_body = request.body.decode('utf-8')
            
            # Verify the webhook hash
            incoming_hash = request.headers.get('verif-hash')
            if not incoming_hash or incoming_hash != settings.FLW_WEBHOOK_HASH:
                logger.warning(f"Invalid webhook hash received: {incoming_hash}")
                return Response({
                    "error": "Unauthorized"
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Parse the payload
            try:
                data = json.loads(raw_body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in webhook payload")
                return Response({
                    "error": "Invalid JSON payload"
                }, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"Received Flutterwave webhook: {data.get('tx_ref', 'unknown')} - {data.get('status', 'unknown')}")

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