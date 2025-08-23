from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from orders.models import Cart, Order
from payments.models import Payment
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Debug cart and order data for a user'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email to debug')

    def handle(self, *args, **options):
        email = options['email']
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f"\n=== DEBUGGING USER: {user.email} ===")
            
            # Get user's cart
            cart = Cart.get_or_create_cart(user)
            self.stdout.write(f"\nCART INFO:")
            self.stdout.write(f"Cart ID: {cart.id}")
            self.stdout.write(f"Total Items: {cart.total_items}")
            self.stdout.write(f"Cart Subtotal: ₦{cart.subtotal}")
            
            # List cart items
            self.stdout.write(f"\nCART ITEMS:")
            total_calculated = Decimal('0')
            for item in cart.items.all():
                item_total = item.total_price
                total_calculated += item_total
                self.stdout.write(f"- {item.product.name}")
                self.stdout.write(f"  Price: ₦{item.product.price}")
                self.stdout.write(f"  Quantity: {item.quantity}")
                self.stdout.write(f"  Item Total: ₦{item_total}")
            
            self.stdout.write(f"\nCART CALCULATION CHECK:")
            self.stdout.write(f"Cart.subtotal property: ₦{cart.subtotal}")
            self.stdout.write(f"Manual calculation: ₦{total_calculated}")
            self.stdout.write(f"Match: {cart.subtotal == total_calculated}")
            
            # Get recent orders
            recent_orders = Order.objects.filter(user=user).order_by('-created_at')[:3]
            self.stdout.write(f"\nRECENT ORDERS:")
            for order in recent_orders:
                self.stdout.write(f"- Order: {order.order_number}")
                self.stdout.write(f"  Status: {order.status}")
                self.stdout.write(f"  Subtotal: ₦{order.subtotal}")
                self.stdout.write(f"  Shipping: ₦{order.shipping_fee}")
                self.stdout.write(f"  Total: ₦{order.total}")
                self.stdout.write(f"  City: {order.shipping_city}")
                self.stdout.write(f"  Created: {order.created_at}")
                
                # Check payments for this order
                payments = Payment.objects.filter(order=order)
                for payment in payments:
                    self.stdout.write(f"    Payment: {payment.payment_id}")
                    self.stdout.write(f"    Amount: ₦{payment.amount}")
                    self.stdout.write(f"    Status: {payment.status}")
                self.stdout.write("")
            
            self.stdout.write("=== END DEBUG ===\n")
            
        except User.DoesNotExist:
            self.stdout.write(f"User with email '{email}' not found")
        except Exception as e:
            self.stdout.write(f"Error: {str(e)}")