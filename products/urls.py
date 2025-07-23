from django.urls import path
from .views import *

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),

    # Wishlist endpoints
    path('wishlist/', WishlistListCreateView.as_view(), name='wishlist-list-create'),
    path('wishlist/<int:pk>/', WishlistDeleteView.as_view(), name='wishlist-delete'),

    # Notification endpoints
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', NotificationMarkReadView.as_view(), name='notification-mark-read'),

    # API Endpoints
    path('featured/', FeaturedProductsAPIView.as_view(), name='featured-products'),
    path('new_arrival/', NewArrivalAPIView.as_view(), name='new-arrivals'),

    # Product reviews endpoint
    path('<slug:slug>/reviews/', ProductReviewListCreateView.as_view(), name='product-reviews'),

    # This must be last to avoid catching 'api/products/...' as a slug
    path('<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
]