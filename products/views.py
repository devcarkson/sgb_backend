from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import permissions
from .models import Product, Category, Review, Wishlist, Notification
from .serializers import ProductSerializer, CategorySerializer, ReviewSerializer, WishlistSerializer, NotificationSerializer
# from .filters import ProductFilter  # Temporarily commented out

class StandardPagination(PageNumberPagination):
    page_size = 2  # Better for infinite scroll - shows more products per load
    page_size_query_param = 'page_size'
    max_page_size = 10000

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at', 'rating']
    ordering = ['-created_at']  # Default ordering
    
    def get_queryset(self):
        queryset = Product.objects.all()
        
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
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = StandardPagination
    
class FeaturedProductsAPIView(APIView):
    def get(self, request):
        featured_products = Product.objects.filter(is_featured=True)
        paginator = StandardPagination()
        result_page = paginator.paginate_queryset(featured_products, request)
        serializer = ProductSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
class NewArrivalAPIView(APIView):
    def get(self, request, *args, **kwargs):
        new_products = Product.objects.filter(is_new_arrival=True)
        paginator = StandardPagination()
        result_page = paginator.paginate_queryset(new_products, request)
        serializer = ProductSerializer(result_page, many=True)
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

class WishlistListCreateView(generics.ListCreateAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class WishlistDeleteView(generics.DestroyAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

class NotificationMarkReadView(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)