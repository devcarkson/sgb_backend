#!/usr/bin/env python
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgb_backend.settings')
django.setup()

from django.test import Client

def test_pagination_detailed():
    print("=== Testing Detailed Pagination ===")
    
    client = Client()
    
    # Test with smaller page size to ensure multiple pages
    print("\n1. Testing with page_size=3 to ensure multiple pages")
    response = client.get('/api/products/?page=1&page_size=3')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Count: {data.get('count')}")
        print(f"Next: {data.get('next')}")
        print(f"Previous: {data.get('previous')}")
        print(f"Results length: {len(data.get('results', []))}")
        print(f"Total pages: {data.get('total_pages')}")
        print(f"Current page: {data.get('current_page')}")
        
        # Test if we can parse the next URL
        next_url = data.get('next')
        if next_url:
            print(f"Next URL: {next_url}")
            # Try to fetch the next page
            print("\n2. Testing next page fetch")
            next_response = client.get(next_url)
            print(f"Next page status: {next_response.status_code}")
            if next_response.status_code == 200:
                next_data = next_response.json()
                print(f"Next page count: {next_data.get('count')}")
                print(f"Next page results: {len(next_data.get('results', []))}")
                print(f"Next page has next: {bool(next_data.get('next'))}")
    else:
        print(f"Error: {response.content}")

if __name__ == "__main__":
    test_pagination_detailed()