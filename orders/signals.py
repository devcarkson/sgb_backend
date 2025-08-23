from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order
from products.models import Notification
from accounts.email_service import EmailService
import logging

logger = logging.getLogger(__name__)

def send_order_confirmation_email(order):
    """
    Send order confirmation email to customer
    """
    try:
        EmailService.send_order_confirmation_email(order)
        logger.info(f"Order confirmation email sent for order {order.order_number}")
        
        # Create notification for order placement
        Notification.objects.create(
            user=order.user,
            message=f"Your order #{order.order_number} has been placed successfully."
        )
    except Exception as e:
        logger.error(f"Failed to send order confirmation email for order {order.order_number}: {str(e)}")

@receiver(post_save, sender=Order)
def order_status_change(sender, instance, created, **kwargs):
    """
    Handle order status changes and send appropriate emails
    """
    if not created and instance.tracker.has_changed('status'):
        try:
            EmailService.send_order_status_update_email(instance)
            logger.info(f"Order status update email sent for order {instance.order_number}")
            
            # Create notification for order status update
            Notification.objects.create(
                user=instance.user,
                message=f"Your order #{instance.order_number} status has been updated to {instance.get_status_display()}."
            )
        except Exception as e:
            logger.error(f"Failed to send order status update email for order {instance.order_number}: {str(e)}")

def send_order_status_update_email(order):
    """
    Send order status update email to customer
    """
    try:
        EmailService.send_order_status_update_email(order)
        logger.info(f"Order status update email sent for order {order.order_number}")
        
        # Create notification for order status update
        Notification.objects.create(
            user=order.user,
            message=f"Your order #{order.order_number} status has been updated to {order.get_status_display()}."
        )
    except Exception as e:
        logger.error(f"Failed to send order status update email for order {order.order_number}: {str(e)}")