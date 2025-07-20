from rest_framework import serializers
from .models import Category, Product, ProductImage

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'image']

# class ProductSerializer(serializers.ModelSerializer):
#     images = ProductImageSerializer(many=True, read_only=True)
#     category = CategorySerializer(read_only=True)
    
#     class Meta:
#         model = Product
#         fields = [
#             'id', 'name', 'slug', 'description', 'price', 'stock', 
#             'rating', 'review_count', 'category', 'images', 'created_at'
#         ]

# products/serializers.py
class ProductSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 
            'stock', 'rating', 'review_count', 'category', 
            'images', 'created_at', 'is_featured', 'is_new_arrival'
        ]
    
    def get_images(self, obj):
        return [image.image.url for image in obj.images.all()]
    
    def get_rating(self, obj):
        # Return a default rating since we don't have a review system yet
        return 4.5
    
    def get_review_count(self, obj):
        # Return a default review count since we don't have a review system yet
        return 0