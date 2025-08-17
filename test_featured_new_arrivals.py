#!/usr/bin/env python
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgb_backend.settings')
django.setup()

from django.test import Client

def test_featured_and_new_arrivals():
    print("=== Testing Featured and New Arrivals ===")
    
    client = Client()
    
    # Test featured products endpoint
    print("\n1. Testing Featured Products")
    response = client.get('/api/products/featured/')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Count: {data.get('count', 'N/A')}")
            results = data.get('results', [])
            print(f"Featured products found: {len(results)}")
            
            for i, product in enumerate(results[:3]):  # Show first 3
                print(f"  {i+1}. {product.get('name')} - Featured: {product.get('is_featured')}")
        else:
            print(f"Featured products found: {len(data)}")
            for i, product in enumerate(data[:3]):  # Show first 3
                print(f"  {i+1}. {product.get('name')} - Featured: {product.get('is_featured')}")
    else:
        print(f"Error: {response.content}")
    
    # Test new arrivals endpoint
    print("\n2. Testing New Arrivals")
    response = client.get('/api/products/new_arrival/')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Count: {data.get('count', 'N/A')}")
            results = data.get('results', [])
            print(f"New arrival products found: {len(results)}")
            
            for i, product in enumerate(results[:3]):  # Show first 3
                print(f"  {i+1}. {product.get('name')} - New Arrival: {product.get('is_new_arrival')}")
        else:
            print(f"New arrival products found: {len(data)}")
            for i, product in enumerate(data[:3]):  # Show first 3
                print(f"  {i+1}. {product.get('name')} - New Arrival: {product.get('is_new_arrival')}")
    else:
        print(f"Error: {response.content}")
    
    # Test regular products with filters
    print("\n3. Testing Regular Products with is_featured=true")
    response = client.get('/api/products/?is_featured=true')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        print(f"Featured products via filter: {len(results)}")
        
        for i, product in enumerate(results[:3]):  # Show first 3
            print(f"  {i+1}. {product.get('name')} - Featured: {product.get('is_featured')}")
    
    print("\n4. Testing Regular Products with is_new_arrival=true")
    response = client.get('/api/products/?is_new_arrival=true')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        print(f"New arrival products via filter: {len(results)}")
        
        for i, product in enumerate(results[:3]):  # Show first 3
            print(f"  {i+1}. {product.get('name')} - New Arrival: {product.get('is_new_arrival')}")

if __name__ == "__main__":
    test_featured_and_new_arrivals()