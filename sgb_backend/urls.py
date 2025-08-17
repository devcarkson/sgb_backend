
from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.response import Response
from rest_framework.decorators import api_view

schema_view = get_schema_view(
   openapi.Info(
      title="SGB E-commerce API",
      default_version='v1',
      description="API documentation for SGB E-commerce Platform",
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

# Root API view
@api_view(['GET'])
def root_api_view(request):
    base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash

    return Response({
        "auth": request.build_absolute_uri('/api/auth/'),
        "products": request.build_absolute_uri('/api/products/'),
        "orders": request.build_absolute_uri('/api/orders/'),
        "payments": request.build_absolute_uri('/api/payments/'),
        "swagger": request.build_absolute_uri('/swagger/'),
        "redoc": request.build_absolute_uri('/redoc/'),
    })


# URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', root_api_view, name='root-api'), 
    path('api/auth/', include('accounts.urls')),
    path('api/products/', include('products.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),

    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    from django.views.static import serve
    from django.views.decorators.cache import cache_control
    
    # Add cache headers to media files
    @cache_control(max_age=60*60*24*7)  # Cache for 1 week
    def cached_serve(request, path, document_root=None, show_indexes=False):
        return serve(request, path, document_root, show_indexes)
    
    urlpatterns += [
        path('media/<path:path>', cached_serve, {'document_root': settings.MEDIA_ROOT}),
    ]