from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from accounts.email_service import EmailService
from django.contrib.auth import get_user_model
from orders.models import Order

User = get_user_model()

class Command(BaseCommand):
    help = 'Test email functionality by sending test emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send test emails to',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['welcome', 'order', 'password', 'status'],
            default='welcome',
            help='Type of test email to send',
        )

    def handle(self, *args, **options):
        test_email = options['email']
        email_type = options['type']

        if not test_email:
            self.stdout.write(self.style.ERROR('Please provide an email address using --email'))
            return

        try:
            # Create a test user if it doesn't exist
            user, created = User.objects.get_or_create(
                email=test_email,
                defaults={
                    'username': test_email.split('@')[0],
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )

            if email_type == 'welcome':
                # Test welcome email
                success = EmailService.send_welcome_email(user)
                message = "Welcome email"

            elif email_type == 'order':
                # Get or create a test order
                order = Order.objects.filter(user=user).first()
                if not order:
                    self.stdout.write("No orders found for testing. Please create an order first.")
                    return
                success = EmailService.send_order_confirmation_email(order)
                message = "Order confirmation email"

            elif email_type == 'status':
                # Get or create a test order
                order = Order.objects.filter(user=user).first()
                if not order:
                    self.stdout.write("No orders found for testing. Please create an order first.")
                    return
                success = EmailService.send_order_status_update_email(order)
                message = "Order status update email"

            elif email_type == 'password':
                # Test basic email functionality
                success = send_mail(
                    subject='Test Email from SGB Store',
                    message='This is a test email to verify email configuration.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[test_email],
                    fail_silently=False,
                )
                message = "Test email"

            if success:
                self.stdout.write(self.style.SUCCESS(
                    f'{message} sent successfully to {test_email}'
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f'Failed to send {message.lower()} to {test_email}'
                ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error sending email: {str(e)}'
            ))