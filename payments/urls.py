from django.urls import path
from .views import PaymentView, PaymentVerificationView, FlutterwaveWebhookView

urlpatterns = [
    path('orders/<str:order_number>/pay/', PaymentView.as_view(), name='initiate-payment'),
    path('verify/<str:payment_id>/', PaymentVerificationView.as_view(), name='verify-payment'),
    path('webhooks/flutterwave/', FlutterwaveWebhookView.as_view(), name='flutterwave-webhook'),
]