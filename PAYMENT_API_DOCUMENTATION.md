# Flutterwave Payment Integration API Documentation

## Overview

This document provides comprehensive documentation for the Flutterwave payment integration in the SGB E-commerce platform. The integration supports online payments alongside existing WhatsApp orders.

## Base URL
```
http://localhost:8000/api  # Development
https://your-domain.com/api  # Production
```

## Authentication

All payment endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Payment Flow

### 1. Checkout Process

**Endpoint:** `POST /orders/checkout/`

Create an order and initialize payment if payment method is 'flutterwave'.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "shipping_address": "123 Main Street",
  "shipping_city": "Lagos",
  "shipping_state": "Lagos State",
  "shipping_country": "Nigeria",
  "shipping_zip_code": "100001",
  "payment_method": "flutterwave",
  "save_shipping_info": false
}
```

**Response (Flutterwave):**
```json
{
  "payment_url": "https://checkout.flutterwave.com/v3/hosted/pay/...",
  "payment_id": "uuid-payment-id",
  "reference": "ORD-12345678",
  "order_id": 123,
  "order": { /* order details */ },
  "status": "pending",
  "payment_method": "flutterwave"
}
```

**Response (WhatsApp):**
```json
{
  "order_id": 123,
  "order": { /* order details */ },
  "reference": "ORD-12345678",
  "status": "pending",
  "payment_method": "whatsapp",
  "message": "Order created successfully. Please complete via WhatsApp."
}
```

### 2. Payment Initialization (Alternative)

**Endpoint:** `POST /payments/initialize/<order_number>/`

Initialize payment for an existing order.

**Response:**
```json
{
  "payment_link": "https://checkout.flutterwave.com/v3/hosted/pay/...",
  "payment_id": "uuid-payment-id",
  "tx_ref": "uuid-payment-id",
  "order_number": "ORD-12345678",
  "amount": "15000.00",
  "currency": "NGN"
}
```

### 3. Payment Callback Handling

**Endpoint:** `GET /payments/callback/`

Handle callback from Flutterwave after payment attempt.

**Query Parameters:**
- `tx_ref`: Transaction reference (payment ID)
- `transaction_id`: Flutterwave transaction ID
- `status`: Payment status

**Response:**
```json
{
  "status": "successful",
  "payment": { /* payment details */ },
  "redirect_url": "http://localhost:8080/orders/123"
}
```

### 4. Payment Verification

**Endpoint:** `GET /payments/verify/<payment_id>/`

Verify payment status with Flutterwave.

**Response:**
```json
{
  "status": "successful",
  "payment": {
    "payment_id": "uuid-payment-id",
    "order": { /* order details */ },
    "gateway": "flutterwave",
    "amount": "15000.00",
    "currency": "NGN",
    "status": "successful",
    "created_at": "2025-01-13T10:30:00Z",
    "paid_at": "2025-01-13T10:35:00Z"
  },
  "message": "Payment completed successfully"
}
```

### 5. Payment Status Polling

**Endpoint:** `GET /payments/status/<payment_id>/`

Get current payment status for polling.

**Response:**
```json
{
  "payment": { /* payment details */ },
  "order": {
    "id": 123,
    "order_number": "ORD-12345678",
    "status": "processing",
    "total": "15000.00"
  }
}
```

### 6. Payment Retry

**Endpoint:** `POST /payments/retry/<payment_id>/`

Retry a failed payment (max 3 retries).

**Response:**
```json
{
  "payment_link": "https://checkout.flutterwave.com/v3/hosted/pay/...",
  "payment_id": "uuid-payment-id",
  "tx_ref": "uuid-payment-id",
  "retry_count": 1
}
```

### 7. Payment History

**Endpoint:** `GET /payments/history/`

Get user's payment history.

**Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "payment_id": "uuid-payment-id",
      "order": { /* order details */ },
      "gateway": "flutterwave",
      "amount": "15000.00",
      "currency": "NGN",
      "status": "successful",
      "created_at": "2025-01-13T10:30:00Z",
      "paid_at": "2025-01-13T10:35:00Z"
    }
  ]
}
```

## Payment Statuses

- **pending**: Payment initialized but not completed
- **processing**: Payment is being processed
- **successful**: Payment completed successfully
- **failed**: Payment failed
- **cancelled**: Payment was cancelled
- **refunded**: Payment was refunded

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "error": "Order is already paid",
  "order_number": "ORD-12345678",
  "payment_status": true
}
```

**404 Not Found:**
```json
{
  "error": "Payment not found"
}
```

**429 Too Many Requests:**
```json
{
  "detail": "Request was throttled. Expected available in 60 seconds."
}
```

## Frontend Integration Guide

### 1. Checkout Flow

```javascript
// 1. Create order and get payment URL
const checkoutData = {
  first_name: 'John',
  last_name: 'Doe',
  shipping_address: '123 Main Street',
  shipping_city: 'Lagos',
  shipping_state: 'Lagos State',
  shipping_country: 'Nigeria',
  shipping_zip_code: '100001',
  payment_method: 'flutterwave',
  save_shipping_info: false
};

const response = await fetch('/api/orders/checkout/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(checkoutData)
});

const result = await response.json();

if (result.payment_url) {
  // Redirect to Flutterwave payment page
  window.location.href = result.payment_url;
}
```

### 2. Payment Status Polling

```javascript
// Poll payment status every 5 seconds
const pollPaymentStatus = async (paymentId) => {
  const response = await fetch(`/api/payments/status/${paymentId}/`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const result = await response.json();
  
  if (result.payment.status === 'successful') {
    // Payment successful - redirect to success page
    window.location.href = `/orders/${result.order.id}`;
  } else if (result.payment.status === 'failed') {
    // Payment failed - show retry option
    showRetryOption(paymentId);
  } else {
    // Still pending - continue polling
    setTimeout(() => pollPaymentStatus(paymentId), 5000);
  }
};
```

### 3. Payment Callback Handling

```javascript
// Handle callback from Flutterwave
const handlePaymentCallback = async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const txRef = urlParams.get('tx_ref');
  const transactionId = urlParams.get('transaction_id');
  const status = urlParams.get('status');
  
  if (txRef) {
    const response = await fetch(`/api/payments/callback/?tx_ref=${txRef}&transaction_id=${transactionId}&status=${status}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    const result = await response.json();
    
    if (result.redirect_url) {
      window.location.href = result.redirect_url;
    }
  }
};
```

### 4. Payment Retry

```javascript
const retryPayment = async (paymentId) => {
  const response = await fetch(`/api/payments/retry/${paymentId}/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const result = await response.json();
  
  if (result.payment_link) {
    window.location.href = result.payment_link;
  }
};
```

## Webhook Configuration

### Flutterwave Webhook URL
```
https://your-domain.com/api/payments/webhooks/flutterwave/
```

### Required Environment Variables

```bash
# Flutterwave Configuration
FLW_PUBLIC_KEY=FLWPUBK_TEST-your-public-key
FLW_SECRET_KEY=FLWSECK_TEST-your-secret-key
FLW_WEBHOOK_HASH=your-webhook-hash

# Frontend URL for redirects
FRONTEND_URL=http://localhost:8080
```

## Rate Limiting

- Payment endpoints: 10 requests per minute per user
- Webhook endpoint: 100 requests per minute
- General API: 1000 requests per hour per user

## Security Features

1. **JWT Authentication**: All endpoints require valid JWT tokens
2. **Webhook Verification**: Webhooks are verified using hash signatures
3. **Payment Verification**: All payments are verified with Flutterwave before marking as successful
4. **Amount Verification**: Webhook amounts are cross-checked with verification API
5. **Idempotency**: Duplicate webhook processing is prevented using caching
6. **Rate Limiting**: Prevents abuse with configurable rate limits

## Testing

### Test Cards (Flutterwave)

```
Card Number: 5531886652142950
CVV: 564
Expiry: 09/32
PIN: 3310
OTP: 12345
```

### Test Environment

Use Flutterwave test keys for development and testing. Switch to live keys for production.

## Support

For issues with the payment integration:

1. Check the payment logs: `sgb_backend/logs/payments.log`
2. Use the Django admin interface to view payment details
3. Run the cleanup command: `python manage.py cleanup_payments --verify-pending`

## Management Commands

### Payment Cleanup
```bash
# Verify pending payments
python manage.py cleanup_payments --verify-pending

# Timeout old pending payments
python manage.py cleanup_payments --timeout-pending

# Cleanup old failed payments
python manage.py cleanup_payments --cleanup-old

# Dry run (show what would be done)
python manage.py cleanup_payments --verify-pending --dry-run
```