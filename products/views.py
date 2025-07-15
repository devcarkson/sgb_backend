from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'price']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'rating']

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
class FeaturedProductsAPIView(APIView):
    def get(self, request):
        featured_products = Product.objects.filter(is_featured=True)[:10]  # Or whatever logic
        serializer = ProductSerializer(featured_products, many=True)
        return Response(serializer.data)
    
    
class NewArrivalAPIView(APIView):
    def get(self, request, *args, **kwargs):
        new_products = Product.objects.filter(is_new_arrival=True)
        serializer = ProductSerializer(new_products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)