from django.urls import path
from . import views

urlpatterns = [
    path("products/", views.products, name="products"),
    path("product_detail/<slug:slug>", views.product_detail, name="product_detail"),
    path("add_item/", views.add_item, name="add_item"),
    path("product_in_cart/", views.product_in_cart, name="product_in_cart"),
    path("get_cart_stat/", views.get_card_stat, name="get_cart_stat"),
    path("get_cart/", views.get_cart, name="get_cart"),
    path("update_quantity/", views.update_quantity, name="update_quantity"),
    path("delete_cartitem", views.delete_cartitem, name="delete_cartitem"),
    path("get_username", views.get_username, name="get_username"),
    path("user_info", views.user_info, name="user_info"),
    path("initiate_payment/", views.initiate_payment, name="initiate_payment"),
    path("payment_callback/", views.payment_callback, name="payment_callback"),
    path("initiate_paypal_payment/", views.initiate_paypal_payment, name="initiate_paypal_payment"),
    path("paypal_payment_callback/", views.paypal_payment_callback, name="paypal_payment_callback"),
    path('register/', views.register_user, name='register_user'),
    # Añadir esta línea a las urlpatterns existentes
    path("search/", views.search_products, name="search_products"),
    path('product-requests/', views.submit_product_request, name='submit_product_request'),
    path('vendor-requests/', views.get_vendor_product_requests, name='get_vendor_product_requests'),
    path('vendor-sales/', views.get_vendor_sales, name='get_vendor_sales'),
    
    # Endpoints para administradores
    path('admin/requests/', views.get_all_product_requests, name='get_all_product_requests'),
    path('admin/requests/approve/<int:request_id>/', views.approve_product_request, name='approve_product_request'),
    path('admin/requests/reject/<int:request_id>/', views.reject_product_request, name='reject_product_request'),
    path('admin/statistics/', views.get_admin_statistics, name='get_admin_statistics'),
]


#fetching all_products: http://127.0.0.1:8001/products/
#search products: http://127.0.0.1:8001/search/?q=your_query
#fetching all_products: http://127.0.0.1:8001/products/