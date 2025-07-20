from django.core.management.base import BaseCommand
from django.core.files import File
from products.models import Category, Product, ProductImage
import os
from pathlib import Path

class Command(BaseCommand):
    help = 'Set up test data with products and images'

    def handle(self, *args, **options):
        self.stdout.write('Setting up test data...')
        
        # Create categories
        electronics, created = Category.objects.get_or_create(
            name='Electronics',
            defaults={'slug': 'electronics'}
        )
        if created:
            self.stdout.write(f'Created category: {electronics.name}')
        
        clothing, created = Category.objects.get_or_create(
            name='Clothing',
            defaults={'slug': 'clothing'}
        )
        if created:
            self.stdout.write(f'Created category: {clothing.name}')
        
        # Create products
        products_data = [
            {
                'name': 'Wireless Headphones',
                'description': 'High-quality wireless headphones with noise cancellation and 30-hour battery life.',
                'price': 199.99,
                'stock': 15,
                'category': electronics,
                'is_featured': True,
                'image_file': '1.jpg'
            },
            {
                'name': 'Smart Watch',
                'description': 'Feature-rich smartwatch with health tracking, GPS, and water resistance.',
                'price': 299.99,
                'stock': 8,
                'category': electronics,
                'is_featured': True,
                'image_file': 'SnapInsta.to_517195513_18114381490497623_4672993102228973079_n.jpg'
            },
            {
                'name': 'Cotton T-Shirt',
                'description': 'Comfortable 100% cotton t-shirt available in multiple colors and sizes.',
                'price': 24.99,
                'stock': 50,
                'category': clothing,
                'is_featured': False,
                'image_file': 'SnapInsta.to_518212817_18114381505497623_2927998923866283814_n.jpg'
            },
            {
                'name': 'Yoga Mat',
                'description': 'Non-slip yoga mat perfect for home workouts and studio sessions.',
                'price': 39.99,
                'stock': 30,
                'category': clothing,
                'is_featured': True,
                'image_file': 'SnapInsta.to_517338646_18114381514497623_5110580454683062765_n.jpg'
            }
        ]
        
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults={
                    'description': product_data['description'],
                    'price': product_data['price'],
                    'stock': product_data['stock'],
                    'category': product_data['category'],
                    'is_featured': product_data['is_featured'],
                    'is_new_arrival': True
                }
            )
            
            if created:
                self.stdout.write(f'Created product: {product.name}')
                
                # Add image to product
                image_path = Path(__file__).parent.parent.parent.parent / 'media' / 'products' / product_data['image_file']
                if image_path.exists():
                    with open(image_path, 'rb') as img_file:
                        product_image = ProductImage.objects.create(
                            product=product,
                            image=File(img_file, name=product_data['image_file']),
                            is_primary=True
                        )
                    self.stdout.write(f'Added image to {product.name}: {product_data["image_file"]}')
                else:
                    self.stdout.write(f'Warning: Image file not found: {image_path}')
        
        self.stdout.write(self.style.SUCCESS('Test data setup completed!')) 