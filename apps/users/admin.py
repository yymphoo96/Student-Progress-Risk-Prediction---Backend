from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, LoginHistory, EmailOTP

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'student_id', 'gender', 'user_type', 'email_verified', 'is_active']
    list_filter = ['user_type', 'gender', 'email_verified', 'is_active']
    search_fields = ['email', 'username', 'student_id', 'first_name', 'last_name']
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'student_id', 'gender', 'phone', 'country', 'profile_image')
        }),
        ('User Type', {'fields': ('user_type',)}),
        ('Verification', {'fields': ('email_verified',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'otp_code', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['email', 'otp_code']
    readonly_fields = ['created_at', 'expires_at']
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'login_time', 'ip_address']
    list_filter = ['login_time']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['user', 'login_time', 'ip_address', 'user_agent']