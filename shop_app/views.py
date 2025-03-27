from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Product, Cart, CartItem
from .serializers import ProductSerializer, DetailedProductSerializer,UserSerializer , CartItemSerializer, SimpleCartSerializer, \
    CartSerializer
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from decimal import Decimal
import uuid
import requests
import paypalrestsdk
from django.conf import settings
from core.models import CustomUser

from .serializers import DetailedProductSerializer

# Create your views here.
@api_view(['GET'])
def products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def product_detail(request, slug):
    product = Product.objects.get(slug=slug)
    serializer = DetailedProductSerializer(product)
    return Response(serializer.data)

@api_view(['POST'])
def add_item(request):
    try:
        cart_code = request.data.get("cart_code")
        product_id = request.data.get("product_id")
        
        cart, created = Cart.objects.get_or_create(cart_code=cart_code)
        product = Product.objects.get(id=product_id)
        
        cartitem, created = CartItem.objects.get_or_create(cart=cart, product=product)
        cartitem.quantity = 1
        cartitem.save()
        
        serializer = CartItemSerializer(cartitem)
        return Response({"datat": serializer.data, "message": "CartItem created successfully"}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['GET'])
def product_in_cart(request):
    cart_code = request.query_params.get("cart_code")
    product_id = request.query_params.get("product_id")
    
    cart = Cart.objects.get(cart_code=cart_code)
    product = Product.objects.get(id=product_id)
    
    product_exists_in_cart = CartItem.objects.filter(cart=cart, product=product).exists()
    
    return Response({"product_in_cart": product_exists_in_cart})
    
    
@api_view(['GET'])
def get_card_stat(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code=cart_code, paid=False)    
    serializer = SimpleCartSerializer(cart)
    return Response(serializer.data)

@api_view(['GET'])
def get_cart(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['PATCH'])
def update_quantity(request):
    try:
        cartitem_id = request.data.get("item_id")
        quantity = request.data.get("quantity")
        quantity = int(quantity)
        cartitem = CartItem.objects.get(id=cartitem_id)
        cartitem.quantity = quantity
        cartitem.save()
        serializer = CartItemSerializer(cartitem)
        return Response({"data": serializer.data, "message": "Caritem updated successfully!"})
    
    except Exception as e:
        return Response({"error": str(e)}, status=400)
    

@api_view(['POST'])
def delete_cartitem(request):
    cartitem_id =request.data.get("item_id")
    cartitem = CartItem.objects.get(id=cartitem_id)
    cartitem.delete()
    return Response({"message": "Item Deleted successfully"},status=status.HTTP_204_NO_CONTENT)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_username(request):
    user = request.user
    return Response({"username": user.username})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)