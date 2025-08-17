#!/usr/bin/env python
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgb_backend.settings')
django.setup()

from django.test import Client

def test_pagination():
    print("=== Testing Pagination ===")
    
    client = Client()
    
    # Test first page
    print("\n1. Testing first page")
    response = client.get('/api/products/?page=1&page_size=5')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Count: {data.get('count')}")
        print(f"Next: {data.get('next')}")
        print(f"Previous: {data.get('previous')}")
        print(f"Results length: {len(data.get('results', []))}")
        
        if data.get('results'):
            first_product = data['results'][0]
            print(f"First product: {first_product.get('name')}")
            print(f"Has primary_image: {'primary_image' in first_product}")
            if 'primary_image' in first_product:
                print(f"Primary image keys: {list(first_product['primary_image'].keys()) if first_product['primary_image'] else 'None'}")
    else:
        print(f"Error: {response.content}")
    
    # Test second page if available
    print("\n2. Testing second page")
    response = client.get('/api/products/?page=2&page_size=5')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Count: {data.get('count')}")
        print(f"Next: {data.get('next')}")
        print(f"Previous: {data.get('previous')}")
        print(f"Results length: {len(data.get('results', []))}")
    else:
        print(f"Error: {response.content}")
    
    # Test with filters
    print("\n3. Testing with search filter")
    response = client.get('/api/products/?search=honey&page=1&page_size=5')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Count: {data.get('count')}")
        print(f"Results length: {len(data.get('results', []))}")
        if data.get('results'):
            for product in data['results']:
                print(f"  - {product.get('name')}")

if __name__ == "__main__":
    test_pagination()