import requests
from django.conf import settings
import logging
from decimal import Decimal
from .models import Payment

logger = logging.getLogger(__name__)

class FlutterwaveService:
    BASE_URL = "https://api.flutterwave.com/v3"

    @classmethod
    def initialize_payment(cls, order):
        """Initialize a Flutterwave payment for an order"""
        try:
            # Create a payment record
            payment = Payment.objects.create(
                order=order,
                gateway='flutterwave',
                amount=order.total,
                currency='NGN',
                status='pending'
            )
            
            headers = {
                "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            # Prepare customer data
            customer_name = f"{order.user.first_name} {order.user.last_name}".strip()
            if not customer_name:
                customer_name = order.user.email.split('@')[0]

            payload = {
                "tx_ref": str(payment.payment_id),  # Use payment ID as transaction reference
                "amount": str(order.total),
                "currency": "NGN",
                "redirect_url": f"{settings.FRONTEND_URL}/payment/callback",
                "customer": {
                    "email": order.user.email,
                    "name": customer_name,
                    "phone_number": getattr(order.user, 'phone', '') or ''
                },
                "customizations": {
                    "title": "SGB Store Payment",
                    "description": f"Payment for Order #{order.order_number}",
                    "logo": f"{settings.FRONTEND_URL}/logo.png"
                },
                "meta": {
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "payment_id": str(payment.payment_id)
                }
            }

            logger.info(f"Initializing Flutterwave payment for order {order.order_number}")
            
            response = requests.post(
                f"{cls.BASE_URL}/payments",
                headers=headers,
                json=payload,
                timeout=30
            )

            data = response.json()
            
            # Log the response for debugging
            logger.info(f"Flutterwave payment response for order {order.order_number}: {data}")
            
            # Check for successful initialization
            if data.get('status') == 'success' and data.get('data', {}).get('link'):
                # Update payment record with gateway reference
                payment.gateway_reference = data.get('data', {}).get('tx_ref', '')
                payment.gateway_response = data
                payment.save()
                
                return {
                    'status': 'success',
                    'data': {
                        'link': data['data']['link'],
                        'payment_id': str(payment.payment_id),
                        'tx_ref': str(payment.payment_id)
                    }
                }
            else:
                # Mark payment as failed
                payment.mark_as_failed(gateway_response=data)
                error_message = data.get('message', 'Payment initialization failed')
                logger.error(f"Flutterwave payment initialization failed for order {order.order_number}: {error_message}")
                raise Exception(f"Payment initialization failed: {error_message}")
                
        except requests.RequestException as e:
            logger.error(f"Network error during Flutterwave payment initialization: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error initializing Flutterwave payment: {str(e)}")
            raise

    @classmethod
    def verify_payment(cls, transaction_id):
        """Verify a Flutterwave payment transaction"""
        try:
            headers = {
                "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            logger.info(f"Verifying Flutterwave transaction: {transaction_id}")
            
            response = requests.get(
                f"{cls.BASE_URL}/transactions/{transaction_id}/verify",
                headers=headers,
                timeout=30
            )

            data = response.json()
            logger.info(f"Flutterwave verification response: {data}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Network error during Flutterwave payment verification: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error verifying Flutterwave payment: {str(e)}")
            raise

    @classmethod
    def process_webhook(cls, webhook_data):
        """Process Flutterwave webhook data"""
        try:
            tx_ref = webhook_data.get('tx_ref')
            status = webhook_data.get('status')
            transaction_id = webhook_data.get('id')
            
            logger.info(f"Processing Flutterwave webhook for tx_ref: {tx_ref}, status: {status}")
            
            if not tx_ref:
                logger.error("No tx_ref in webhook data")
                return False
            
            # Find the payment record
            try:
                payment = Payment.objects.get(payment_id=tx_ref)
            except Payment.DoesNotExist:
                logger.error(f"Payment not found for tx_ref: {tx_ref}")
                return False
            
            # Update payment based on status
            if status == 'successful':
                # Verify the payment with Flutterwave to ensure authenticity
                verification_data = cls.verify_payment(transaction_id)
                
                if (verification_data.get('status') == 'success' and 
                    verification_data.get('data', {}).get('status') == 'successful'):
                    
                    # Mark payment as successful
                    payment.mark_as_successful(
                        gateway_transaction_id=transaction_id,
                        gateway_response=webhook_data
                    )
                    
                    logger.info(f"Payment {payment.payment_id} marked as successful")
                    return True
                else:
                    logger.warning(f"Payment verification failed for tx_ref: {tx_ref}")
                    payment.mark_as_failed(gateway_response=verification_data)
                    return False
            
            elif status in ['failed', 'cancelled']:
                payment.mark_as_failed(gateway_response=webhook_data)
                logger.info(f"Payment {payment.payment_id} marked as failed/cancelled")
                return True
            
            else:
                logger.info(f"Payment {payment.payment_id} status updated to: {status}")
                payment.status = 'processing' if status == 'pending' else payment.status
                payment.gateway_response = webhook_data
                payment.save()
                return True
                
        except Exception as e:
            logger.error(f"Error processing Flutterwave webhook: {str(e)}")
            return False