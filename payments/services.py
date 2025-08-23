import requests
import hashlib
import hmac
from django.conf import settings
from django.core.cache import cache
import logging
from decimal import Decimal
from .models import Payment

logger = logging.getLogger(__name__)

class FlutterwaveService:
    BASE_URL = "https://api.flutterwave.com/v3"
    TIMEOUT = 30
    MAX_RETRIES = 3

    @classmethod
    def initialize_payment(cls, order):
        """Initialize a Flutterwave payment for an order"""
        try:
            # Check if there's already a pending payment for this order
            existing_payment = Payment.objects.filter(
                order=order,
                status='pending',
                gateway='flutterwave'
            ).first()
            
            if existing_payment:
                logger.info(f"Found existing pending payment {existing_payment.payment_id} for order {order.order_number}")
                logger.info(f"Existing payment amount: {existing_payment.amount}, Current order total: {order.total}")
                
                # Check if the existing payment amount matches the current order total
                if existing_payment.amount == order.total:
                    # Try to get the payment link from the existing payment
                    if existing_payment.gateway_response and existing_payment.gateway_response.get('data', {}).get('link'):
                        logger.info(f"Reusing existing payment with matching amount")
                        return {
                            'status': 'success',
                            'data': {
                                'link': existing_payment.gateway_response['data']['link'],
                                'payment_id': str(existing_payment.payment_id),
                                'tx_ref': str(existing_payment.payment_id)
                            }
                        }
                else:
                    logger.info(f"Existing payment amount ({existing_payment.amount}) doesn't match current order total ({order.total}). Creating new payment.")
                    # Mark the old payment as cancelled and create a new one
                    existing_payment.status = 'cancelled'
                    existing_payment.save()
            
            # Create a new payment record
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

            # Get user phone number safely
            phone_number = ""
            if hasattr(order.user, 'phone') and order.user.phone:
                phone_number = str(order.user.phone)
            elif hasattr(order.user, 'profile') and hasattr(order.user.profile, 'phone') and order.user.profile.phone:
                phone_number = str(order.user.profile.phone)

            # Ensure amount is properly formatted as string without decimals for Flutterwave
            amount_str = f"{float(order.total):.2f}"
            
            payload = {
                "tx_ref": str(payment.payment_id),  # Use payment ID as transaction reference
                "amount": amount_str,
                "currency": "NGN",
                "redirect_url": f"{settings.FRONTEND_URL}/payment/callback",
                "customer": {
                    "email": order.user.email,
                    "name": customer_name,
                    "phone_number": phone_number
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

            logger.info(f"=== FLUTTERWAVE PAYMENT DEBUG ===")
            logger.info(f"Order Number: {order.order_number}")
            logger.info(f"Order ID: {order.id}")
            logger.info(f"Order Details:")
            logger.info(f"  - Subtotal: {order.subtotal}")
            logger.info(f"  - Shipping Fee: {order.shipping_fee}")
            logger.info(f"  - Tax: {order.tax}")
            logger.info(f"  - Total: {order.total}")
            logger.info(f"  - Shipping City: {order.shipping_city}")
            logger.info(f"  - Shipping State: {order.shipping_state}")
            logger.info(f"Payment Record:")
            logger.info(f"  - Payment ID: {payment.payment_id}")
            logger.info(f"  - Payment Amount: {payment.amount}")
            logger.info(f"Flutterwave Payload:")
            logger.info(f"  - Amount String: {amount_str}")
            logger.info(f"  - TX Ref: {payload['tx_ref']}")
            logger.info(f"  - Currency: {payload['currency']}")
            logger.info(f"=== END DEBUG ===")
            
            response = requests.post(
                f"{cls.BASE_URL}/payments",
                headers=headers,
                json=payload,
                timeout=cls.TIMEOUT
            )

            data = response.json()
            
            # Log the response for debugging (without sensitive data)
            safe_data = {k: v for k, v in data.items() if k not in ['data']}
            if 'data' in data and isinstance(data['data'], dict):
                safe_data['data'] = {k: v for k, v in data['data'].items() if k != 'link'}
                safe_data['data']['link_available'] = bool(data['data'].get('link'))
            
            logger.info(f"Flutterwave payment response for order {order.order_number}: {safe_data}")
            
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
                error_message = data.get('message', 'Payment initialization failed')
                payment.mark_as_failed(gateway_response=data, error_message=error_message)
                logger.error(f"Flutterwave payment initialization failed for order {order.order_number}: {error_message}")
                raise Exception(f"Payment initialization failed: {error_message}")
                
        except requests.RequestException as e:
            logger.error(f"Network error during Flutterwave payment initialization: {str(e)}")
            if 'payment' in locals():
                payment.mark_as_failed(error_message=f"Network error: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error initializing Flutterwave payment: {str(e)}")
            if 'payment' in locals():
                payment.mark_as_failed(error_message=str(e))
            raise

    @classmethod
    def verify_payment(cls, transaction_id):
        """Verify a Flutterwave payment transaction"""
        try:
            # Check cache first to avoid repeated API calls
            cache_key = f"flw_verify_{transaction_id}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Using cached verification result for transaction {transaction_id}")
                return cached_result

            headers = {
                "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            logger.info(f"Verifying Flutterwave transaction: {transaction_id}")
            
            response = requests.get(
                f"{cls.BASE_URL}/transactions/{transaction_id}/verify",
                headers=headers,
                timeout=cls.TIMEOUT
            )

            data = response.json()
            logger.info(f"Flutterwave verification response for {transaction_id}: status={data.get('status')}")
            
            # Cache successful verifications for 5 minutes
            if data.get('status') == 'success':
                cache.set(cache_key, data, 300)
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Network error during Flutterwave payment verification: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error verifying Flutterwave payment: {str(e)}")
            raise

    @classmethod
    def process_webhook(cls, webhook_data):
        """Process Flutterwave webhook data with enhanced security"""
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
            
            # Prevent processing the same webhook multiple times
            webhook_cache_key = f"webhook_processed_{tx_ref}_{transaction_id}"
            if cache.get(webhook_cache_key):
                logger.info(f"Webhook already processed for tx_ref: {tx_ref}")
                return True
            
            # Update payment based on status
            if status == 'successful':
                # Verify the payment with Flutterwave to ensure authenticity
                verification_data = cls.verify_payment(transaction_id)
                
                if (verification_data.get('status') == 'success' and 
                    verification_data.get('data', {}).get('status') == 'successful'):
                    
                    # Additional security check: verify amount matches
                    webhook_amount = webhook_data.get('amount')
                    verified_amount = verification_data.get('data', {}).get('amount')
                    
                    if webhook_amount and verified_amount and float(webhook_amount) != float(verified_amount):
                        logger.error(f"Amount mismatch for tx_ref {tx_ref}: webhook={webhook_amount}, verified={verified_amount}")
                        return False
                    
                    # Mark payment as successful
                    payment.mark_as_successful(
                        gateway_transaction_id=transaction_id,
                        gateway_response=webhook_data
                    )
                    
                    # Cache that this webhook was processed
                    cache.set(webhook_cache_key, True, 3600)  # Cache for 1 hour
                    
                    logger.info(f"Payment {payment.payment_id} marked as successful")
                    return True
                else:
                    logger.warning(f"Payment verification failed for tx_ref: {tx_ref}")
                    payment.mark_as_failed(gateway_response=verification_data)
                    return False
            
            elif status in ['failed', 'cancelled']:
                payment.mark_as_failed(gateway_response=webhook_data)
                cache.set(webhook_cache_key, True, 3600)
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

    @classmethod
    def validate_webhook_signature(cls, payload, signature):
        """Validate Flutterwave webhook signature"""
        try:
            if not settings.FLW_WEBHOOK_HASH:
                logger.warning("FLW_WEBHOOK_HASH not configured")
                return False
                
            expected_signature = hmac.new(
                settings.FLW_WEBHOOK_HASH.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Error validating webhook signature: {str(e)}")
            return False

    @classmethod
    def retry_failed_payment(cls, payment):
        """Retry a failed payment"""
        try:
            if not payment.can_retry:
                raise Exception("Payment cannot be retried (max retries reached or not failed)")
            
            payment.increment_retry_count()
            payment.status = 'pending'
            payment.save()
            
            # Re-initialize the payment
            return cls.initialize_payment(payment.order)
            
        except Exception as e:
            logger.error(f"Error retrying payment {payment.payment_id}: {str(e)}")
            raise

    @classmethod
    def get_payment_status(cls, payment_id):
        """Get current payment status from Flutterwave"""
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            
            if payment.gateway_transaction_id:
                verification_data = cls.verify_payment(payment.gateway_transaction_id)
                return verification_data
            else:
                return {"status": "error", "message": "No transaction ID available"}
                
        except Payment.DoesNotExist:
            return {"status": "error", "message": "Payment not found"}
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            return {"status": "error", "message": str(e)}