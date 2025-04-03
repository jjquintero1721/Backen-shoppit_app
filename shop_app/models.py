from django.db import models
from django.utils.text import slugify
from django.conf import settings
# Create your models here.
class Product(models.Model):
    
    CATEGORY =  (("Electronicos", "ELECTRONICOS"),
                 ("Juegos", "JUEGOS")
                 )
    objects = models.Manager()
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, null=True)
    image = models.ImageField(upload_to="img")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=15, choices=CATEGORY, blank=True, null=True)
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    
    def __str__(self):
        return str(self.name)
    
    def save(self, *args, **kwargs):
        
        if not self.slug:
            self.slug = slugify(self.name)
            unique_slug = self.slug
            counter = 1
            if Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{self.slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)
        

class Cart(models.Model):
    cart_code = models.CharField(max_length=11, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null= True)
    modified_at = models.DateTimeField(auto_now=True, blank=True , null=True)
    
    def __str__(self):
        return str(self.cart_code)
    

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in cart {self.cart.id}"
    

class Transaction(models.Model):
    ref = models.CharField(max_length=255, unique=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")
    status = models.CharField(max_length=20, default='pending')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transaction {self.ref} - {self.status}"
    
from decimal import Decimal

class ProductRequest(models.Model):
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_requests')
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="img")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=15, choices=Product.CATEGORY, blank=True, null=True)
    
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True)
    
    # Cálculo de comisión (porcentaje que va a la plataforma)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)  # Default 10%
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()}) by {self.vendor.username}"
    
    def approve(self):
        """Aprobar la solicitud y crear un producto"""
        if self.status == 'pending':
            product = Product.objects.create(
                name=self.name,
                image=self.image,
                description=self.description,
                price=self.price,
                category=self.category,
                vendor=self.vendor,
                commission_rate=self.commission_rate
            )
            self.status = 'approved'
            self.save()
            return product
        return None
    
    def reject(self, notes=None):
        """Rechazar la solicitud"""
        if self.status == 'pending':
            self.status = 'rejected'
            if notes:
                self.admin_notes = notes
            self.save()
            return True
        return False
    
    def calculate_platform_benefit(self):
        """Calcular el beneficio esperado para la plataforma"""
        return (self.price * Decimal(self.commission_rate) / Decimal(100)).quantize(Decimal('0.01'))

class SalesSummary(models.Model):
    """Modelo para almacenar estadísticas de ventas precalculadas"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales_summary')
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sales_summary')
    
    total_quantity = models.PositiveIntegerField(default=0)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('product', 'vendor')
    
    @classmethod
    def update_sales_for_cart(cls, cart):
        """Actualizar estadísticas cuando un carrito es pagado"""
        if cart.paid:
            for item in cart.items.all():
                product = item.product
                if product.vendor:
                    vendor = product.vendor
                    quantity = item.quantity
                    price = product.price
                    total = price * Decimal(quantity)
                    commission = (total * Decimal(product.commission_rate) / Decimal(100)).quantize(Decimal('0.01'))
                    
                    summary, created = cls.objects.get_or_create(
                        product=product,
                        vendor=vendor,
                        defaults={
                            'total_quantity': quantity,
                            'total_sales': total,
                            'total_commission': commission
                        }
                    )
                    
                    if not created:
                        summary.total_quantity += quantity
                        summary.total_sales += total
                        summary.total_commission += commission
                        summary.save()