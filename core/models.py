from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Nuevo campo para el rol
    ROLE_CHOICES = (
        ('user', 'Usuario'),
        ('vendor', 'Vendedor'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    
    def __str__(self) -> str:
        return str(self.username)