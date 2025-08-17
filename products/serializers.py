from rest_framework import serializers
from .models import Category, Product, ProductImage, Review, Wishlist, Notification
from django.contrib.auth import get_user_model

class ProductImageSerializer(serializers.ModelSerializer):
    thumbnail_small = serializers.SerializerMethodField()
    thumbnail_medium = serializers.SerializerMethodField()
    thumbnail_large = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'thumbnail_small', 'thumbnail_medium', 'thumbnail_large', 'is_primary']
    
    def get_thumbnail_small(self, obj):
        request = self.context.get('request')
        try:
            if obj.thumbnail_small and request:
                return request.build_absolute_uri(obj.thumbnail_small.url)
        except:
            # Fallback to original image if thumbnail fails
            if obj.image and request:
                return request.build_absolute_uri(obj.image.url)
        return None
    
    def get_thumbnail_medium(self, obj):
        request = self.context.get('request')
        try:
            if obj.thumbnail_medium and request:
                return request.build_absolute_uri(obj.thumbnail_medium.url)
        except:
            # Fallback to original image if thumbnail fails
            if obj.image and request:
                return request.build_absolute_uri(obj.image.url)
        return None
    
    def get_thumbnail_large(self, obj):
        request = self.context.get('request')
        try:
            if obj.thumbnail_large and request:
                return request.build_absolute_uri(obj.thumbnail_large.url)
        except:
            # Fallback to original image if thumbnail fails
            if obj.image and request:
                return request.build_absolute_uri(obj.image.url)
        return None

class CategorySerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'image', 'thumbnail']
    
    def get_thumbnail(self, obj):
        request = self.context.get('request')
        try:
            if obj.thumbnail and request:
                return request.build_absolute_uri(obj.thumbnail.url)
        except:
            # Fallback to original image if thumbnail fails
            if obj.image and request:
                return request.build_absolute_uri(obj.image.url)
        return None

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

# Lightweight serializer for list views (faster loading)
class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'discount_price', 
            'stock', 'rating', 'review_count', 'category', 
            'primary_image', 'is_featured', 'is_new_arrival'
        ]
    
    def get_primary_image(self, obj):
        """Get only the primary image thumbnail for list view"""
        primary_image = obj.images.filter(is_primary=True).first()
        if not primary_image:
            primary_image = obj.images.first()
        
        if primary_image:
            request = self.context.get('request')
            result = {'id': primary_image.id}
            
            # Try to get thumbnails, fallback to original image
            try:
                if primary_image.thumbnail_small and request:
                    result['thumbnail_small'] = request.build_absolute_uri(primary_image.thumbnail_small.url)
                elif primary_image.image and request:
                    result['thumbnail_small'] = request.build_absolute_uri(primary_image.image.url)
            except:
                if primary_image.image and request:
                    result['thumbnail_small'] = request.build_absolute_uri(primary_image.image.url)
            
            try:
                if primary_image.thumbnail_medium and request:
                    result['thumbnail_medium'] = request.build_absolute_uri(primary_image.thumbnail_medium.url)
                elif primary_image.image and request:
                    result['thumbnail_medium'] = request.build_absolute_uri(primary_image.image.url)
            except:
                if primary_image.image and request:
                    result['thumbnail_medium'] = request.build_absolute_uri(primary_image.image.url)
            
            return result
        return None
    
    def get_rating(self, obj):
        # Use cached rating if available
        if hasattr(obj, '_cached_rating'):
            return obj._cached_rating
        reviews = getattr(obj, 'prefetched_reviews', obj.reviews.all())
        if not reviews:
            return None
        rating = round(sum([r.rating for r in reviews]) / len(reviews), 2)
        obj._cached_rating = rating
        return rating
    
    def get_review_count(self, obj):
        # Use cached review count if available
        if hasattr(obj, '_cached_review_count'):
            return obj._cached_review_count
        reviews = getattr(obj, 'prefetched_reviews', obj.reviews.all())
        count = len(reviews)
        obj._cached_review_count = count
        return count

# Full serializer for detail views
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 
            'discount_price', 'stock', 'rating', 'review_count', 'category', 
            'images', 'primary_image', 'created_at', 'is_featured', 'is_new_arrival', 'reviews'
        ]
    
    def get_primary_image(self, obj):
        """Get the primary image or first image for quick loading"""
        primary_image = obj.images.filter(is_primary=True).first()
        if not primary_image:
            primary_image = obj.images.first()
        
        if primary_image:
            return ProductImageSerializer(primary_image, context=self.context).data
        return None
    
    def get_rating(self, obj):
        # Use prefetched reviews to avoid N+1 queries
        reviews = getattr(obj, 'prefetched_reviews', obj.reviews.all())
        if not reviews:
            return None
        return round(sum([r.rating for r in reviews]) / len(reviews), 2)
    
    def get_review_count(self, obj):
        # Use prefetched reviews to avoid N+1 queries
        reviews = getattr(obj, 'prefetched_reviews', obj.reviews.all())
        return len(reviews)

# Minimal serializer for better performance in lists
class ProductMinimalSerializer(serializers.ModelSerializer):
    primary_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'price', 'discount_price', 'primary_image_url']
    
    def get_primary_image_url(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if not primary_image:
            primary_image = obj.images.first()
        
        if primary_image:
            request = self.context.get('request')
            try:
                if request and primary_image.thumbnail_small:
                    return request.build_absolute_uri(primary_image.thumbnail_small.url)
            except:
                pass
            # Fallback to original image
            if request and primary_image.image:
                return request.build_absolute_uri(primary_image.image.url)
        return None

class WishlistSerializer(serializers.ModelSerializer):
    product = ProductMinimalSerializer(read_only=True)  # Use minimal serializer
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