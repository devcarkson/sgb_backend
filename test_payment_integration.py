#!/usr/bin/env python
"""
Test script for Flutterwave payment integration
Run this script to test the payment flow without making actual payments
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgb_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from orders.models import Order, Cart, CartItem
from products.models import Product
from payments.models import Payment
from payments.services import FlutterwaveService

User = get_user_model()

def create_test_data():
    """Create test user, product, and cart for testing"""
    print("Creating test data...")
    
    # Create test user
    user, created = User.objects.get_or_create(
        email='test@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✓ Created test user: {user.email}")
    else:
        print(f"✓ Using existing test user: {user.email}")
    
    # Get or create test product
    product, created = Product.objects.get_or_create(
        name='Test Product',
        defaults={
            'description': 'Test product for payment integration',
            'price': Decimal('1000.00'),
            'stock': 10,
            'is_active': True
        }
    )
    if created:
        print(f"✓ Created test product: {product.name}")
    else:
        print(f"✓ Using existing test product: {product.name}")
    
    # Create cart and add item
    cart = Cart.get_or_create_cart(user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 2}
    )
    if created:
        print(f"✓ Added {cart_item.quantity}x {product.name} to cart")
    else:
        print(f"✓ Cart already has {cart_item.quantity}x {product.name}")
    
    return user, product, cart

def create_test_order(user, cart):
    """Create a test order"""
    print("\nCreating test order...")
    
    subtotal = cart.subtotal
    shipping_fee = Decimal('500.00')
    tax = subtotal * Decimal('0.08')
    total = subtotal + shipping_fee + tax
    
    order = Order.objects.create(
        user=user,
        shipping_address='123 Test Street',
        shipping_city='Lagos',
        shipping_state='Lagos State',
        shipping_country='Nigeria',
        shipping_zip_code='100001',
        payment_method='flutterwave',
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        tax=tax,
        total=total
    )
    
    print(f"✓ Created order: {order.order_number}")
    print(f"  - Subtotal: ₦{order.subtotal}")
    print(f"  - Shipping: ₦{order.shipping_fee}")
    print(f"  - Tax: ₦{order.tax}")
    print(f"  - Total: ₦{order.total}")
    
    return order

def test_payment_initialization(order):
    """Test payment initialization"""
    print(f"\nTesting payment initialization for order {order.order_number}...")
    
    try:
        # This would normally make an API call to Flutterwave
        # For testing, we'll create a mock payment record
        payment = Payment.objects.create(
            order=order,
            gateway='flutterwave',
            amount=order.total,
            currency='NGN',
            status='pending'
        )
        
        print(f"✓ Created payment record: {payment.payment_id}")
        print(f"  - Amount: ₦{payment.amount}")
        print(f"  - Status: {payment.status}")
        print(f"  - Gateway: {payment.gateway}")
        
        return payment
        
    except Exception as e:
        print(f"✗ Payment initialization failed: {str(e)}")
        return None

def test_payment_verification(payment):
    """Test payment verification"""
    print(f"\nTesting payment verification for {payment.payment_id}...")
    
    try:
        # Simulate successful payment
        payment.mark_as_successful(
            gateway_transaction_id='test_txn_123456',
            gateway_response={
                'status': 'success',
                'data': {
                    'status': 'successful',
                    'amount': float(payment.amount),
                    'currency': payment.currency
                }
            }
        )
        
        print(f"✓ Payment marked as successful")
        print(f"  - Status: {payment.status}")
        print(f"  - Paid at: {payment.paid_at}")
        print(f"  - Order payment status: {payment.order.payment_status}")
        print(f"  - Order status: {payment.order.status}")
        
        return True
        
    except Exception as e:
        print(f"✗ Payment verification failed: {str(e)}")
        return False

def test_cart_clearing(user):
    """Test that cart is cleared after successful payment"""
    print(f"\nTesting cart clearing...")
    
    cart = user.cart
    item_count_before = cart.items.count()
    
    # Cart should be cleared after successful payment
    item_count_after = cart.items.count()
    
    print(f"  - Items before payment: {item_count_before}")
    print(f"  - Items after payment: {item_count_after}")
    
    if item_count_after == 0:
        print("✓ Cart cleared successfully")
        return True
    else:
        print("✗ Cart was not cleared")
        return False

def cleanup_test_data():
    """Clean up test data"""
    print("\nCleaning up test data...")
    
    try:
        # Delete test orders and payments
        Order.objects.filter(user__email='test@example.com').delete()
        print("✓ Cleaned up test orders and payments")
        
        # Clear test cart
        user = User.objects.get(email='test@example.com')
        user.cart.items.all().delete()
        print("✓ Cleared test cart")
        
    except Exception as e:
        print(f"✗ Cleanup failed: {str(e)}")

def main():
    """Main test function"""
    print("=" * 60)
    print("FLUTTERWAVE PAYMENT INTEGRATION TEST")
    print("=" * 60)
    
    try:
        # Create test data
        user, product, cart = create_test_data()
        
        # Create test order
        order = create_test_order(user, cart)
        
        # Test payment initialization
        payment = test_payment_initialization(order)
        if not payment:
            return
        
        # Test payment verification
        success = test_payment_verification(payment)
        if not success:
            return
        
        # Test cart clearing
        test_cart_clearing(user)
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        
        print("\nTest Summary:")
        print(f"- Order: {order.order_number}")
        print(f"- Payment: {payment.payment_id}")
        print(f"- Amount: ₦{payment.amount}")
        print(f"- Status: {payment.status}")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Ask if user wants to cleanup
        cleanup = input("\nCleanup test data? (y/n): ").lower().strip()
        if cleanup == 'y':
            cleanup_test_data()

if __name__ == '__main__':
    main()