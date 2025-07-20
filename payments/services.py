import requests
from django.conf import settings
import logging

class FlutterwaveService:
    BASE_URL = "https://api.flutterwave.com/v3"

    @classmethod
    def initialize_payment(cls, order):
        headers = {
            "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "tx_ref": order.order_number,
            "amount": str(order.total),
            "currency": "NGN",
            "redirect_url": f"{settings.FRONTEND_URL}/order/{order.order_number}",
            "customer": {
                "email": order.user.email,
                "name": f"{order.user.first_name} {order.user.last_name}",
                "phone_number": order.user.phone
            },
            "customizations": {
                "title": "SGB Store Payment",
                "logo": "https://your-logo-url.com/logo.png"
            }
        }

        response = requests.post(
            f"{cls.BASE_URL}/payments",
            headers=headers,
            json=payload
        )

        data = response.json()
        # Log the full response for debugging
        logging.error(f"Flutterwave payment response: {data}")
        # Check for payment link
        if not data.get('status') == 'success' or not data.get('data', {}).get('link'):
            raise Exception(f"Payment initialization failed: {data}")
        return data

    @classmethod
    def verify_payment(cls, transaction_id):
        headers = {
            "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.get(
            f"{cls.BASE_URL}/transactions/{transaction_id}/verify",
            headers=headers
        )

        return response.json()