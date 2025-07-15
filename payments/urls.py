from django.urls import path
from .views import PaymentView, FlutterwaveWebhookView

urlpatterns = [
    path('orders/<str:order_number>/pay/', PaymentView.as_view(), name='initiate-payment'),
    path('webhooks/flutterwave/', FlutterwaveWebhookView.as_view(), name='flutterwave-webhook'),
]