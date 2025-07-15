from django.urls import path
from .views import *

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),

    # API Endpoints
    path('featured/', FeaturedProductsAPIView.as_view(), name='featured-products'),
    path('new_arrival/', NewArrivalAPIView.as_view(), name='new-arrivals'),

    # This must be last to avoid catching 'api/products/...' as a slug
    path('<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
]