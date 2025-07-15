from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order

def send_order_confirmation_email(order):
    subject = f"Order Confirmation - #{order.order_number}"
    html_message = render_to_string(
        'emails/order_confirmation.html',
        {'order': order}
    )
    plain_message = f"""
    Thank you for your order #{order.order_number}!
    
    Order Total: ${order.total}
    Status: {order.get_status_display()}
    
    We'll notify you when your order ships.
    """
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        html_message=html_message
    )

@receiver(post_save, sender=Order)
def order_status_change(sender, instance, created, **kwargs):
    if not created and instance.tracker.has_changed('status'):
        send_order_status_update_email(instance)

def send_order_status_update_email(order):
    subject = f"Order Update - #{order.order_number}"
    html_message = render_to_string(
        'emails/order_status_update.html',
        {'order': order}
    )
    plain_message = f"""
    Your order #{order.order_number} status has been updated to {order.get_status_display()}.
    
    Current Status: {order.get_status_display()}
    """
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        html_message=html_message
    )