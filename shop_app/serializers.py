from rest_framework import serializers
from .models import Product, Cart, CartItem

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
    
class CartSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["id", "Cart_code", "created_at", "modified_at"]
        model = Cart
        
        
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    cart = CartSerializer(read_only=True)
    class Meta:
        model = CartItem
        fields = ["id", "cart", "product", "quantity"]