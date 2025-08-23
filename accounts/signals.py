from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django_rest_passwordreset.signals import reset_password_token_created
from .email_service import EmailService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def send_welcome_email_on_registration(sender, instance, created, **kwargs):
    """
    Send welcome email when a new user is created
    """
    if created:
        try:
            EmailService.send_welcome_email(instance)
            logger.info(f"Welcome email sent to {instance.email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {instance.email}: {str(e)}")

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Send password reset email when a reset token is created
    """
    try:
        EmailService.send_password_reset_email(reset_password_token)
        logger.info(f"Password reset email sent to {reset_password_token.user.email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {reset_password_token.user.email}: {str(e)}")