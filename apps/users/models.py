# models.py

from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

# ===================== USER MANAGEMENT =====================

class User(AbstractUser):
    """Custom User Model with encrypted password"""
    USER_TYPES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    )
    GENDER_CHOICES = (
        (0, 'Female'),
        (1, 'Male'),
    ) 
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    student_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPES)
    gender = models.IntegerField(choices=GENDER_CHOICES, default=1, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Override username field to use email
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
    
    def save(self, *args, **kwargs):
        # Automatically encrypt password if it's not already encrypted
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.student_id or self.email})"

class LoginHistory(models.Model):
    """Track user login history"""
    login_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)
    device_info = models.TextField(null=True)
    
    class Meta:
        db_table = 'login_history'












