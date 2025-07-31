import django_filters
from .models import Product, Category

class ProductFilter(django_filters.FilterSet):
    # Price range filters
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    
    # Category filter
    category = django_filters.NumberFilter(field_name="category__id")
    
    # Stock filter
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    
    # Featured and new arrival filters
    is_featured = django_filters.BooleanFilter(field_name='is_featured')
    is_new_arrival = django_filters.BooleanFilter(field_name='is_new_arrival')
    
    class Meta:
        model = Product
        fields = ['category', 'min_price', 'max_price', 'in_stock', 'is_featured', 'is_new_arrival']
    
    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__gt=0)
        return queryset