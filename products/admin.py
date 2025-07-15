from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url) if obj.image else ''
    image_preview.short_description = 'Preview'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    
    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    readonly_fields = ['created_at', 'updated_at']
    actions = ['activate_products', 'deactivate_products']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'description', 'is_featured', 'is_new_arrival')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price')
        }),
        ('Inventory', {
            'fields': ('stock', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products activated.')
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products deactivated.')
    deactivate_products.short_description = "Deactivate selected products"