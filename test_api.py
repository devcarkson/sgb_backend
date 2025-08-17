#!/usr/bin/env python
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgb_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def test_api_endpoints():
    print("=== Testing API Endpoints ===")
    
    client = Client()
    
    # Test product list endpoint
    print("\n1. Testing /api/products/")
    response = client.get('/api/products/')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total products: {data.get('count', 0)}")
        
        if data.get('results'):
            first_product = data['results'][0]
            print(f"First product: {first_product.get('name')}")
            print(f"Primary image: {first_product.get('primary_image')}")
        else:
            print("No products in results")
    else:
        print(f"Error: {response.content}")
    
    # Test featured products endpoint
    print("\n2. Testing /api/products/featured/")
    response = client.get('/api/products/featured/')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total featured products: {data.get('count', 0)}")
        
        if data.get('results'):
            first_product = data['results'][0]
            print(f"First featured product: {first_product.get('name')}")
            print(f"Primary image: {first_product.get('primary_image')}")
    else:
        print(f"Error: {response.content}")
    
    # Test product detail endpoint
    print("\n3. Testing product detail endpoint")
    from products.models import Product
    product = Product.objects.first()
    if product:
        response = client.get(f'/api/products/{product.slug}/')
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Product: {data.get('name')}")
            print(f"Number of images: {len(data.get('images', []))}")
            if data.get('images'):
                first_image = data['images'][0]
                print(f"First image data:")
                for key, value in first_image.items():
                    print(f"  {key}: {value}")
        else:
            print(f"Error: {response.content}")

if __name__ == "__main__":
    test_api_endpoints()