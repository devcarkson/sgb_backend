from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from payments.models import Payment
from payments.services import FlutterwaveService
import logging

logger = logging.getLogger('payments')

class Command(BaseCommand):
    help = 'Cleanup and monitor payment statuses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verify-pending',
            action='store_true',
            help='Verify pending payments with Flutterwave',
        )
        parser.add_argument(
            '--cleanup-old',
            action='store_true',
            help='Cleanup old failed payments (older than 30 days)',
        )
        parser.add_argument(
            '--timeout-pending',
            action='store_true',
            help='Mark pending payments as failed if older than 1 hour',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        
        if options['verify_pending']:
            self.verify_pending_payments()
        
        if options['timeout_pending']:
            self.timeout_pending_payments()
        
        if options['cleanup_old']:
            self.cleanup_old_payments()
        
        if not any([options['verify_pending'], options['timeout_pending'], options['cleanup_old']]):
            self.stdout.write(
                self.style.WARNING(
                    'No action specified. Use --verify-pending, --timeout-pending, or --cleanup-old'
                )
            )

    def verify_pending_payments(self):
        """Verify pending payments with Flutterwave"""
        self.stdout.write('Verifying pending payments...')
        
        pending_payments = Payment.objects.filter(
            status='pending',
            gateway='flutterwave',
            gateway_transaction_id__isnull=False
        )
        
        verified_count = 0
        failed_count = 0
        
        for payment in pending_payments:
            try:
                if self.dry_run:
                    self.stdout.write(f'Would verify payment: {payment.payment_id}')
                    continue
                
                verification_data = FlutterwaveService.verify_payment(
                    payment.gateway_transaction_id
                )
                
                if (verification_data.get('status') == 'success' and 
                    verification_data.get('data', {}).get('status') == 'successful'):
                    
                    payment.mark_as_successful(
                        gateway_transaction_id=payment.gateway_transaction_id,
                        gateway_response=verification_data
                    )
                    verified_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Payment {payment.payment_id} verified as successful')
                    )
                    
                elif verification_data.get('data', {}).get('status') in ['failed', 'cancelled']:
                    payment.mark_as_failed(gateway_response=verification_data)
                    failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'✗ Payment {payment.payment_id} marked as failed')
                    )
                    
            except Exception as e:
                logger.error(f'Error verifying payment {payment.payment_id}: {str(e)}')
                self.stdout.write(
                    self.style.ERROR(f'Error verifying payment {payment.payment_id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Verification complete: {verified_count} successful, {failed_count} failed'
            )
        )

    def timeout_pending_payments(self):
        """Mark pending payments as failed if they're older than 1 hour"""
        self.stdout.write('Checking for timed out payments...')
        
        timeout_threshold = timezone.now() - timedelta(hours=1)
        timed_out_payments = Payment.objects.filter(
            status='pending',
            created_at__lt=timeout_threshold
        )
        
        count = 0
        for payment in timed_out_payments:
            if self.dry_run:
                self.stdout.write(f'Would timeout payment: {payment.payment_id}')
                continue
            
            payment.mark_as_failed(error_message='Payment timed out after 1 hour')
            count += 1
            self.stdout.write(
                self.style.WARNING(f'⏰ Payment {payment.payment_id} timed out')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Timed out {count} payments')
        )

    def cleanup_old_payments(self):
        """Delete old failed payments (older than 30 days)"""
        self.stdout.write('Cleaning up old failed payments...')
        
        cleanup_threshold = timezone.now() - timedelta(days=30)
        old_payments = Payment.objects.filter(
            status='failed',
            created_at__lt=cleanup_threshold
        )
        
        count = old_payments.count()
        
        if self.dry_run:
            self.stdout.write(f'Would delete {count} old failed payments')
            return
        
        old_payments.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Cleaned up {count} old failed payments')
        )

    def get_payment_stats(self):
        """Display payment statistics"""
        stats = {
            'pending': Payment.objects.filter(status='pending').count(),
            'successful': Payment.objects.filter(status='successful').count(),
            'failed': Payment.objects.filter(status='failed').count(),
            'total': Payment.objects.count(),
        }
        
        self.stdout.write('\n=== Payment Statistics ===')
        for status, count in stats.items():
            self.stdout.write(f'{status.title()}: {count}')
        self.stdout.write('=' * 27)