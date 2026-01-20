from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, LoginHistory

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'student_id', 'gender', 'user_type', 'is_active']
    list_filter = ['user_type', 'gender', 'is_active']
    search_fields = ['email', 'username', 'student_id', 'first_name', 'last_name']
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'student_id', 'gender', 'phone', 'country', 'profile_image')
        }),
        ('User Type', {'fields': ('user_type',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'user_type', 'student_id', 'gender'),
        }),
    )

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'login_time', 'ip_address']
    list_filter = ['login_time']
    search_fields = ['user__email', 'user__username', 'ip_address']
    readonly_fields = ['user', 'login_time', 'ip_address', 'device_info']

