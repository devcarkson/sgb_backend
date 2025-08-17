#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgb_backend.settings')
django.setup()

from products.models import ProductImage, Product
from products.serializers import ProductListSerializer, ProductImageSerializer
from django.test import RequestFactory

def test_image_serialization():
    print("=== Testing Image Serialization ===")
    
    # Get a product with images
    product = Product.objects.prefetch_related('images').first()
    if not product:
        print("No products found!")
        return
    
    print(f"Testing product: {product.name}")
    print(f"Number of images: {product.images.count()}")
    
    # Test individual image serialization
    image = product.images.first()
    if image:
        print(f"\nTesting image: {image.image.name}")
        print(f"Image file exists: {image.image and bool(image.image.name)}")
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = 'localhost:8000'
        request.META['wsgi.url_scheme'] = 'http'
        
        # Test image serializer
        image_serializer = ProductImageSerializer(image, context={'request': request})
        image_data = image_serializer.data
        
        print(f"Serialized image data:")
        for key, value in image_data.items():
            print(f"  {key}: {value}")
    
    # Test product list serializer
    print(f"\n=== Testing Product List Serializer ===")
    factory = RequestFactory()
    request = factory.get('/')
    request.META['HTTP_HOST'] = 'localhost:8000'
    request.META['wsgi.url_scheme'] = 'http'
    
    serializer = ProductListSerializer(product, context={'request': request})
    data = serializer.data
    
    print(f"Product data:")
    print(f"  Name: {data.get('name')}")
    print(f"  Primary image: {data.get('primary_image')}")
    
    # Test thumbnail generation
    print(f"\n=== Testing Thumbnail Generation ===")
    if image:
        try:
            print(f"Trying to access thumbnail_small...")
            thumb_small = image.thumbnail_small
            print(f"Thumbnail small URL: {thumb_small.url if thumb_small else 'None'}")
        except Exception as e:
            print(f"Error accessing thumbnail_small: {e}")
        
        try:
            print(f"Trying to access thumbnail_medium...")
            thumb_medium = image.thumbnail_medium
            print(f"Thumbnail medium URL: {thumb_medium.url if thumb_medium else 'None'}")
        except Exception as e:
            print(f"Error accessing thumbnail_medium: {e}")

if __name__ == "__main__":
    test_image_serialization()