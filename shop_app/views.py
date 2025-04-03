from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Product, Cart, CartItem, Transaction
from .serializers import ProductSerializer, DetailedProductSerializer, UserSerializer, CartItemSerializer, SimpleCartSerializer, \
    CartSerializer, ProductSubmissionSerializer
from .models import ProductSubmission  # Import the ProductSubmission model
from rest_framework import status
from django.db import models  # Añadido para consultas Q
from django.conf import settings
from decimal import Decimal
import uuid
import requests
import paypalrestsdk
from core.models import CustomUser


BASE_URL = settings.REACT_BASE_URL

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    if request.user:
        try:
            tx_ref = str(uuid.uuid4())
            cart_code = request.data.get("cart_code")
            cart = Cart.objects.get(cart_code=cart_code)
            user= request.user
            
            amount =sum([item.quantity * item.product.price for item in cart.items.all()])
            tax = Decimal("4.00")
            total_amount = amount + tax
            currency = "NGN"
            redirect_url = f"{BASE_URL}/payment-status/"
            
            transaction = Transaction.objects.create(
                ref=tx_ref,
                cart=cart,
                amount=total_amount,
                currency=currency,
                user=user,
                status='pending'
            )
            
            flutterwave_payload = {
                "tx_ref": tx_ref,
                "amount": str(total_amount),
                "currency": currency,
                "redirect_url": redirect_url,
                "customer" : {
                    "email": user.email,
                    "username": user.username,
                    "phonenumber": user.phone
                },
                "customizations": {
                    "title": "A.I.A.G Payment"
                }
            }
            
            
            headers = {
                "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
                "Content-Type": "application/json"
            }
            
            
            response = requests.post(
                'https://api.flutterwave.com/v3/payments',
                json=flutterwave_payload,
                headers=headers
            )
            
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response(response.json(), status=response.status_code)

        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
@api_view(["POST"])
def payment_callback(request):
    status = request.GET.get("status")
    tx_ref = request.GET.get("tx_ref")
    transaction_id = request.GET.get("transaction_id")

    user = request.user

    if status == "successful":
        # Verify the transaction using Flutterwave's API
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"
        }

        response = requests.get(f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify", headers=headers)
        response_data = response.json()

        if response_data["status"] == "success":
            transaction = Transaction.objects.get(ref=tx_ref)

            # Confirm the transaction details
            if(response_data['data']['status'] == "successful"
                    and float(response_data['data']['amount']) == float(transaction.amount)
                    and response_data['data']['currency'] == transaction.currency):
                # Update transaction and cart status to paid
                transaction.status = "completed"
                transaction.save()

                cart = transaction.cart
                cart.paid = True
                cart.user = user
                cart.save()

                return Response({'message': 'Payment succesful!', 'subMessage': 'You have succesfully made payment for items you purchased!'})
            else:
                # Payment verification failed
                return Response({'message': 'Payment verification failed.', 'subMessage': 'Your payment verification failed.'})
        else:
            return Response({'message': 'Failed to verify transaction with Flutterwave.', 'subMessage': 'We could not verify transaction with Flutterwave.'})
    else:
        # Payment was not successful
        return Response({'message': 'Payment was not succesful.'}, status=400)

@api_view(["POST"])
def initiate_paypal_payment(request):
    if request.method == "POST" and request.user.is_authenticated:
        tx_ref = str(uuid.uuid4())
        user = request.user
        cart_code = request.data.get('cart_code')
        cart = Cart.objects.get(cart_code=cart_code)
        amount = sum(item.product.price * item.quantity for item in cart.items.all())
        tax = Decimal("4.00")
        total_amount = amount + tax

        # Create a PayPal payment object
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": f"{BASE_URL}/payment-status?paymentStatus=success&ref={tx_ref}",
                "cancel_url": f"{BASE_URL}/payment-status?paymentStatus=cancel"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "Cart Items",
                        "sku": "cart",
                        "price": str(total_amount),
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(total_amount),
                    "currency": "USD"
                },
                "description": "Payment for cart items."
            }]
        })

        print("pay_id", payment)

        transaction, created = Transaction.objects.get_or_create(
            ref=tx_ref,
            cart=cart,
            amount=total_amount,
            user=user,
            status="pending"
        )

        if payment.create():
            for link in payment.links: 
                if link in payment.links:
                    if link.rel == 'approval_url':
                        approval_url = str(link.href)
                        return Response({"approval_url": approval_url})
        else:
            return Response({'error': payment.error}, status=400)

@api_view(['POST'])
def paypal_payment_callback(request):
    payment_id = request.query_params.get('paymentId')
    payer_id = request.query_params.get('PayerID')
    ref = request.query_params.get('ref')
    
    user = request.user
    
    print("refff", ref)
    
    transaction = Transaction.objects.get(ref=ref)
    
    if payment_id and payer_id:
        
        payment = paypalrestsdk.Payment.find(payment_id)
        
        transaction.status= 'completed'
        transaction.save()
        cart = transaction.cart
        cart.paid = True
        cart.user = user
        cart.save()
        
        return Response({'message': 'Payment succesful', 'subMessage': 'You have successfully made payment for the items you purchased'})
    
    else:
        return Response({"error": "invalid payment details."}, status=400)

# shop_app/views.py (replace existing register_user function)

@api_view(["POST"])
def register_user(request):
    try:
        # Extract user data from request
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        role = request.data.get('role', 'user')  # Default to 'user' if not specified
        
        # Validate role
        if role not in ['user', 'seller']:
            return Response(
                {"error": "Invalid role. Must be 'user' or 'seller'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already exists
        if CustomUser.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists. Please choose a different one."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already in use. Please use a different email or login."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create new user
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role  # Set the user role
        )

        # Add additional data if provided
        if request.data.get('phone'):
            user.phone = request.data.get('phone')
        if request.data.get('address'):
            user.address = request.data.get('address')
        if request.data.get('city'):
            user.city = request.data.get('city')
        if request.data.get('state'):
            user.state = request.data.get('state')

        user.save()

        # Return success response
        return Response(
            {"success": "User registered successfully! Please login with your credentials."},
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )        
# Añadir este import en la parte superior del archivo
from django.db.models import Q
import re

@api_view(['GET'])
def search_products(request):
    """
    Búsqueda inteligente de productos con sugerencias relacionadas
    """
    query = request.query_params.get('q', '').strip()
    
    if not query:
        return Response({'results': [], 'related': []})
    
    # Dividir la consulta en términos individuales y filtrar palabras cortas
    search_terms = [term.lower() for term in re.findall(r'\w+', query) if len(term) > 2]
    
    # Construir consulta para búsqueda
    query_filter = Q()
    for term in search_terms:
        # Búsqueda en nombre (mayor peso)
        name_filter = Q(name__icontains=term)
        # Búsqueda en descripción (peso medio)
        desc_filter = Q(description__icontains=term)
        # Búsqueda en categoría (peso medio-alto)
        category_filter = Q(category__icontains=term)
        
        # Combinar filtros con OR
        query_filter |= name_filter | desc_filter | category_filter
    
    # Obtener resultados directos
    direct_results = Product.objects.filter(query_filter).distinct()
    
    # Si no hay resultados directos o hay pocos, buscar productos relacionados
    related_products = []
    
    if direct_results.count() <= 5:
        # Construir lista de categorías de los resultados principales
        result_categories = set(direct_results.values_list('category', flat=True))
        
        # Buscar productos en las mismas categorías que no son resultados directos
        if result_categories:
            category_filter = Q()
            for category in result_categories:
                if category:  # Asegurarse de que la categoría no sea None
                    category_filter |= Q(category=category)
                    
            related_products = Product.objects.filter(category_filter).exclude(id__in=direct_results.values_list('id', flat=True))[:8]
        
        # Si no hay categorías o productos relacionados, mostrar algunos productos aleatorios
        if not related_products:
            related_products = Product.objects.all().order_by('?')[:8]
    
    # Serializar resultados
    direct_results_serialized = ProductSerializer(direct_results, many=True).data
    related_products_serialized = ProductSerializer(related_products, many=True).data
    
    return Response({
        'results': direct_results_serialized,
        'related': related_products_serialized
    })
    
    
# shop_app/views.py (add to existing file)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_product(request):
    """API endpoint for sellers to submit a product for approval"""
    if request.user.role != 'seller':
        return Response({"error": "Only sellers can submit products"}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = ProductSubmissionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(seller=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seller_submissions(request):
    """API endpoint for sellers to view their product submissions"""
    if request.user.role != 'seller':
        return Response({"error": "Only sellers can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)
    
    submissions = ProductSubmission.objects.filter(seller=request.user)
    serializer = ProductSubmissionSerializer(submissions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_view_submissions(request):
    """API endpoint for admins to view all product submissions"""
    if not request.user.is_staff:
        return Response({"error": "Only administrators can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)
    
    status_filter = request.query_params.get('status', None)
    
    if status_filter:
        submissions = ProductSubmission.objects.filter(status=status_filter)
    else:
        submissions = ProductSubmission.objects.all()
    
    serializer = ProductSubmissionSerializer(submissions, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_review_submission(request, submission_id):
    """API endpoint for admins to approve or reject a product submission"""
    if not request.user.is_staff:
        return Response({"error": "Only administrators can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        submission = ProductSubmission.objects.get(id=submission_id)
    except ProductSubmission.DoesNotExist:
        return Response({"error": "Submission not found"}, status=status.HTTP_404_NOT_FOUND)
    
    action = request.data.get("action", "")
    admin_notes = request.data.get("admin_notes", "")
    
    if action not in ["approve", "reject"]:
        return Response({"error": "Invalid action. Must be 'approve' or 'reject'"}, status=status.HTTP_400_BAD_REQUEST)
    
    if action == "approve":
        # Create a new product based on the submission
        product = Product(
            name=submission.name,
            slug=submission.slug,
            image=submission.image,
            description=submission.description,
            price=submission.price,
            category=submission.category,
            seller=submission.seller
        )
        product.save()
        
        # Update the submission
        submission.status = "approved"
        submission.admin_notes = admin_notes
        submission.product = product
        submission.save()
        
        return Response({
            "message": "Submission approved and product created",
            "submission": ProductSubmissionSerializer(submission).data,
            "product": ProductSerializer(product).data
        })
    else:  # action == "reject"
        submission.status = "rejected"
        submission.admin_notes = admin_notes
        submission.save()
        
        return Response({
            "message": "Submission rejected",
            "submission": ProductSubmissionSerializer(submission).data
        })
        
# shop_app/views.py (add to existing file)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seller_statistics(request):
    """API endpoint for sellers to view their sales statistics"""
    if request.user.role != 'seller':
        return Response({"error": "Only sellers can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)
    
    # Get all products by this seller
    products = Product.objects.filter(seller=request.user)
    
    # Get all CartItems for these products where the cart is paid
    cart_items = CartItem.objects.filter(product__in=products, cart__paid=True)
    
    # Calculate statistics
    total_sales = sum(item.quantity * item.product.price for item in cart_items)
    total_items_sold = sum(item.quantity for item in cart_items)
    product_counts = {}
    
    for item in cart_items:
        product_name = item.product.name
        if product_name in product_counts:
            product_counts[product_name] += item.quantity
        else:
            product_counts[product_name] = item.quantity
    
    # Sort by highest selling products
    top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Get sales by date
    sales_by_date = {}
    for item in cart_items:
        date_str = item.cart.modified_at.strftime('%Y-%m-%d')
        if date_str in sales_by_date:
            sales_by_date[date_str] += item.quantity * item.product.price
        else:
            sales_by_date[date_str] = item.quantity * item.product.price
    
    return Response({
        "total_sales": total_sales,
        "total_items_sold": total_items_sold,
        "top_products": top_products[:10],  # Top 10 products
        "sales_by_date": sales_by_date
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_statistics(request):
    """API endpoint for admins to view overall platform statistics"""
    if not request.user.is_staff:
        return Response({"error": "Only administrators can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)
    
    # Get all paid carts
    paid_carts = Cart.objects.filter(paid=True)
    
    # Get all sellers
    sellers = CustomUser.objects.filter(role='seller')
    
    # Calculate total platform sales
    total_platform_sales = sum(
        item.product.price * item.quantity 
        for cart in paid_carts 
        for item in cart.items.all()
    )
    
    # Calculate sales per seller
    seller_sales = {}
    for seller in sellers:
        seller_products = Product.objects.filter(seller=seller)
        seller_cart_items = CartItem.objects.filter(product__in=seller_products, cart__paid=True)
        seller_total_sales = sum(item.quantity * item.product.price for item in seller_cart_items)
        seller_sales[seller.username] = seller_total_sales
    
    # Sort by highest selling sellers
    top_sellers = sorted(seller_sales.items(), key=lambda x: x[1], reverse=True)
    
    # Pending submissions count
    pending_submissions_count = ProductSubmission.objects.filter(status='pending').count()
    
    return Response({
        "total_platform_sales": total_platform_sales,
        "top_sellers": top_sellers,
        "total_sellers": sellers.count(),
        "pending_submissions_count": pending_submissions_count
    })