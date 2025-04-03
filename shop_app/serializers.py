from rest_framework import serializers
from .models import Product, Cart, CartItem, ProductRequest, SalesSummary
from django.contrib.auth import get_user_model

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "slug", "image", "description", "price", "category"]

class DetailedProductSerializer(serializers.ModelSerializer):
    similar_products = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ["id", "name", "slug", "image", "description", "price", "similar_products"]
        
    def get_similar_products(self, products):
        products = Product.objects.filter(category=products.category).exclude(id=products.id)
        serializer = ProductSerializer(products, many=True)
        return serializer.data
    
    
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total = serializers.SerializerMethodField()
    class Meta:
        model = CartItem
        fields = ["id", "quantity", "product", "total"]
    def get_total(self, cart_item):
        price = cart_item.product.price * cart_item.quantity
        return price
        
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(read_only=True ,many=True)
    sum_total = serializers.SerializerMethodField()
    num_of_items = serializers.SerializerMethodField()
    class Meta:
        model = Cart
        fields = ["id", "cart_code", "items", "sum_total", "num_of_items", "created_at", "modified_at"]
        
    def get_sum_total(self, cart):
        items = cart.items.all()
        total = sum([item.product.price * item.quantity for item in items])
        return total

    def get_num_of_items(self, cart):
        items = cart.items.all()
        total = sum([item.quantity for item in items])
        return total

class SimpleCartSerializer(serializers.ModelSerializer):
    num_of_items = serializers.SerializerMethodField()
    class Meta:
        model = Cart
        fields = ["id", "cart_code", "num_of_items"]
    
    def get_num_of_items(self, cart):
        num_of_items = sum([item.quantity for item in cart.items.all()])
        return num_of_items
        

class NewCartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    order_id = serializers.SerializerMethodField()
    order_date = serializers.SerializerMethodField()
    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "order_id", "order_date"]
        
    def get_order_id(self, cartitem):
        order_id = cartitem.cart.cart_code
        return order_id

    def get_order_date(self, cartitem):
        order_date = cartitem.cart.modified_at
        return order_date

class UserSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    class Meta:
        model = get_user_model()
        fields = ["id", "username", "first_name", "last_name", "email", "city", "state", "address", "phone", "items"]
        
    def get_items(self, user):
        cartitems = CartItem.objects.filter(cart__user=user, cart__paid=True)[:10]
        serializer = NewCartItemSerializer(cartitems, many=True)
        return serializer.data
    
    
# En shop_app/serializers.py

class ProductRequestSerializer(serializers.ModelSerializer):
    platform_benefit = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductRequest
        fields = [
            'id', 'name', 'image', 'description', 'price', 'category',
            'status', 'admin_notes', 'commission_rate', 'created_at',
            'modified_at', 'platform_benefit'
        ]
        read_only_fields = ['status', 'admin_notes', 'platform_benefit']
    
    def get_platform_benefit(self, obj):
        return obj.calculate_platform_benefit()

class ProductRequestDetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.SerializerMethodField()
    platform_benefit = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductRequest
        fields = [
            'id', 'vendor', 'vendor_name', 'name', 'image', 'description', 
            'price', 'category', 'status', 'admin_notes', 'commission_rate', 
            'created_at', 'modified_at', 'platform_benefit'
        ]
    
    def get_vendor_name(self, obj):
        return obj.vendor.username
    
    def get_platform_benefit(self, obj):
        return obj.calculate_platform_benefit()

class SalesSummarySerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SalesSummary
        fields = [
            'id', 'product', 'product_name', 'total_quantity', 
            'total_sales', 'total_commission', 'last_updated'
        ]
    
    def get_product_name(self, obj):
        return obj.product.name