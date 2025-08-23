from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import permissions
from django.views.decorators.cache import cache_page, never_cache
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from .models import Product, Category, Review, Wishlist, Notification
from .serializers import ProductSerializer, ProductListSerializer, CategorySerializer, ReviewSerializer, WishlistSerializer, NotificationSerializer
# from .filters import ProductFilter  # Temporarily commented out

class StandardPagination(PageNumberPagination):
    page_size = 12  # Optimized for grid layouts (3x4 or 4x3)
    page_size_query_param = 'page_size'
    max_page_size = 100  # Prevent excessive data loading
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.page_size,
            'results': data
        })

class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer  # Use lightweight serializer for list view
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at', 'rating']
    ordering = ['-created_at']  # Default ordering
    
    def get_queryset(self):
        # Optimize queries with select_related and prefetch_related
        queryset = Product.objects.select_related('category').prefetch_related(
            'images',
            'reviews'
        )
        
        # Manual filtering
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__id=category)
            
        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
            
        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
            
        in_stock = self.request.query_params.get('in_stock')
        if in_stock and in_stock.lower() == 'true':
            queryset = queryset.filter(stock__gt=0)
            
        is_featured = self.request.query_params.get('is_featured')
        if is_featured and is_featured.lower() == 'true':
            queryset = queryset.filter(is_featured=True)
            
        is_new_arrival = self.request.query_params.get('is_new_arrival')
        if is_new_arrival and is_new_arrival.lower() == 'true':
            queryset = queryset.filter(is_new_arrival=True)
            
        return queryset

class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        # Optimize queries for detail view
        return Product.objects.select_related('category').prefetch_related(
            'images',
            'reviews__user'
        )

@method_decorator(cache_page(60 * 15), name='dispatch')  # Cache for 15 minutes
class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = StandardPagination
    
class FeaturedProductsAPIView(APIView):
    def get(self, request):
        featured_products = Product.objects.filter(is_featured=True).select_related('category').prefetch_related(
            'images',
            'reviews'
        )
        paginator = StandardPagination()
        result_page = paginator.paginate_queryset(featured_products, request)
        serializer = ProductListSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
class NewArrivalAPIView(APIView):
    def get(self, request, *args, **kwargs):
        new_products = Product.objects.filter(is_new_arrival=True).select_related('category').prefetch_related(
            'images',
            'reviews'
        )
        paginator = StandardPagination()
        result_page = paginator.paginate_queryset(new_products, request)
        serializer = ProductListSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

# ... (keep your other views the same - Review, Wishlist, Notification views)

class ProductReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        product_slug = self.kwargs['slug']
        return Review.objects.filter(product__slug=product_slug)

    def perform_create(self, serializer):
        product = Product.objects.get(slug=self.kwargs['slug'])
        serializer.save(user=self.request.user, product=product)

@method_decorator(never_cache, name='dispatch')
class WishlistListCreateView(generics.ListCreateAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product')

    def perform_create(self, serializer):
        wishlist = serializer.save(user=self.request.user)
        # Broadcast wishlist update
        try:
            from payments.realtime import broadcast_realtime_update
            from .serializers import WishlistSerializer
            broadcast_realtime_update(
                user_id=str(self.request.user.id),
                data={
                    "type": "wishlist_update",
                    "wishlist": WishlistSerializer(Wishlist.objects.filter(user=self.request.user), many=True).data
                }
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Realtime wishlist_update error: {e}")

@method_decorator(never_cache, name='dispatch')
class WishlistDeleteView(generics.DestroyAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        user_id = instance.user.id
        instance.delete()
        # Broadcast wishlist update after removal
        try:
            from payments.realtime import broadcast_realtime_update
            from .serializers import WishlistSerializer
            broadcast_realtime_update(
                user_id=str(user_id),
                data={
                    "type": "wishlist_update",
                    "wishlist": WishlistSerializer(Wishlist.objects.filter(user__id=user_id), many=True).data
                }
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Realtime wishlist_update remove error: {e}")

@method_decorator(never_cache, name='dispatch')
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

@method_decorator(never_cache, name='dispatch')
class NotificationMarkReadView(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)