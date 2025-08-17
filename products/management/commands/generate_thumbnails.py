from django.core.management.base import BaseCommand
from products.models import ProductImage, Category
from imagekit.utils import get_cache


class Command(BaseCommand):
    help = 'Generate thumbnails for all existing images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of existing thumbnails',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write('Generating thumbnails for product images...')
        
        # Generate thumbnails for product images
        product_images = ProductImage.objects.all()
        total_product_images = product_images.count()
        
        for i, image in enumerate(product_images, 1):
            try:
                # Check if image file exists
                if not image.image or not image.image.name:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping {image.product.name} - No image file')
                    )
                    continue
                
                # Generate all thumbnail sizes
                try:
                    if force:
                        image.thumbnail_small.generate()
                        image.thumbnail_medium.generate()
                        image.thumbnail_large.generate()
                    else:
                        # Check if thumbnails exist, if not generate them
                        if not hasattr(image.thumbnail_small, 'url') or not image.thumbnail_small:
                            image.thumbnail_small.generate()
                        if not hasattr(image.thumbnail_medium, 'url') or not image.thumbnail_medium:
                            image.thumbnail_medium.generate()
                        if not hasattr(image.thumbnail_large, 'url') or not image.thumbnail_large:
                            image.thumbnail_large.generate()
                except Exception as thumb_error:
                    self.stdout.write(
                        self.style.WARNING(f'Thumbnail generation failed for {image.product.name}: {str(thumb_error)}')
                    )
                
                self.stdout.write(
                    f'Progress: {i}/{total_product_images} - Processed {image.product.name}'
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {image.product.name}: {str(e)}')
                )
        
        # Generate thumbnails for category images
        self.stdout.write('Generating thumbnails for category images...')
        categories = Category.objects.exclude(image='')
        total_categories = categories.count()
        
        for i, category in enumerate(categories, 1):
            try:
                # Check if image file exists
                if not category.image or not category.image.name:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping category {category.name} - No image file')
                    )
                    continue
                
                try:
                    if force:
                        category.thumbnail.generate()
                    else:
                        # Check if thumbnail exists, if not generate it
                        if not hasattr(category.thumbnail, 'url') or not category.thumbnail:
                            category.thumbnail.generate()
                except Exception as thumb_error:
                    self.stdout.write(
                        self.style.WARNING(f'Thumbnail generation failed for category {category.name}: {str(thumb_error)}')
                    )
                
                self.stdout.write(
                    f'Progress: {i}/{total_categories} - Processed category {category.name}'
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing category {category.name}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully generated all thumbnails!')
        )