from django.urls import path
from .views import (
    PaymentView, 
    PaymentInitializeView,
    PaymentVerificationView, 
    PaymentCallbackView,
    PaymentStatusView,
    PaymentRetryView,
    PaymentListView,
    FlutterwaveWebhookView
)

urlpatterns = [
    # Payment initialization
    path('orders/<str:order_number>/pay/', PaymentView.as_view(), name='initiate-payment'),
    path('initialize/<str:order_number>/', PaymentInitializeView.as_view(), name='initialize-payment'),
    
    # Payment verification and status
    path('verify/<str:payment_id>/', PaymentVerificationView.as_view(), name='verify-payment'),
    path('status/<str:payment_id>/', PaymentStatusView.as_view(), name='payment-status'),
    
    # Payment callback from Flutterwave
    path('callback/', PaymentCallbackView.as_view(), name='payment-callback'),
    
    # Payment retry
    path('retry/<str:payment_id>/', PaymentRetryView.as_view(), name='retry-payment'),
    
    # Payment history
    path('history/', PaymentListView.as_view(), name='payment-history'),
    
    # Webhooks
    path('webhooks/flutterwave/', FlutterwaveWebhookView.as_view(), name='flutterwave-webhook'),
]