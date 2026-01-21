# apps/users/models.py - ADD OTP model

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import random

class User(AbstractUser):
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
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='student')
    gender = models.IntegerField(choices=GENDER_CHOICES, default=1, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    
    # ✅ NEW: Email verification
    email_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"


# ✅ NEW: OTP Model
class EmailOTP(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    # Store registration data temporarily
    temp_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'email_otps'
        ordering = ['-created_at']
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"{self.email} - {self.otp_code}"
    
    @staticmethod
    def generate_otp():
        """Generate 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    @classmethod
    def create_otp(cls, email, temp_data=None):
        """Create new OTP for email"""
        # Invalidate old OTPs for this email
        cls.objects.filter(email=email, is_used=False).update(is_used=True)
        
        # Generate new OTP
        otp_code = cls.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=10)  # Valid for 10 minutes
        
        otp = cls.objects.create(
            email=email,
            otp_code=otp_code,
            expires_at=expires_at,
            temp_data=temp_data
        )
        
        return otp


class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'login_history'
        ordering = ['-login_time']