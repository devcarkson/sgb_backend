from rest_framework import serializers
from .models import Category, Product, ProductImage, Review, Wishlist, Notification
from django.contrib.auth import get_user_model

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
class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

class ProductSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 
            'discount_price', 'stock', 'rating', 'review_count', 'category', 
            'images', 'created_at', 'is_featured', 'is_new_arrival', 'reviews'
        ]
    
    def get_images(self, obj):
        return [image.image.url for image in obj.images.all()]
    
    def get_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return None
        return round(sum([r.rating for r in reviews]) / reviews.count(), 2)
    
    def get_review_count(self, obj):
        return obj.reviews.count()

class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), source='product', write_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id', 'created_at']
        read_only_fields = ['id', 'created_at', 'product']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'read', 'created_at']
        read_only_fields = ['id', 'created_at']