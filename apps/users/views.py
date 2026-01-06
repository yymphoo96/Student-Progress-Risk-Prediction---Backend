# apps/users/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from .models import User, LoginHistory
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer
)

class AuthViewSet(viewsets.ViewSet):
    """Authentication endpoints"""
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """
        Student Registration (Sign Up)
        
        POST /api/auth/register/
        Body:
        {
            "email": "student@example.com",
            "username": "johnsmith",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "first_name": "John",
            "last_name": "Smith",
            "student_id": "123456",
            "user_type": "student",
            "phone": "+1234567890",
            "country": "Myanmar",
            "date_of_birth": "2000-01-01"
        }
        """
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Create authentication token
            token, created = Token.objects.get_or_create(user=user)
            
            # Log the registration
            LoginHistory.objects.create(
                user=user,
                ip_address=self._get_client_ip(request),
                device_info=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': 'Registration successful',
                'user': UserProfileSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """
        User Login
        
        POST /api/auth/login/
        Body:
        {
            "email": "student@example.com",
            "password": "SecurePass123!"
        }
        """
        serializer = UserLoginSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Create or get authentication token
            token, created = Token.objects.get_or_create(user=user)
            
            # Log the login
            LoginHistory.objects.create(
                user=user,
                ip_address=self._get_client_ip(request),
                device_info=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Django session login (optional)
            login(request, user)
            
            return Response({
                'message': 'Login successful',
                'user': UserProfileSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        User Logout
        
        POST /api/auth/logout/
        Headers: Authorization: Token <token>
        """
        try:
            # Delete the token
            request.user.auth_token.delete()
        except:
            pass
        
        # Django session logout
        logout(request)
        
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """
        Get current user profile
        
        GET /api/auth/profile/
        Headers: Authorization: Token <token>
        """
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """
        Update user profile
        
        PUT/PATCH /api/auth/update_profile/
        Headers: Authorization: Token <token>
        Body:
        {
            "first_name": "John",
            "last_name": "Smith",
            "phone": "+1234567890",
            "country": "Myanmar"
        }
        """
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change user password
        
        POST /api/auth/change_password/
        Headers: Authorization: Token <token>
        Body:
        {
            "old_password": "OldPass123!",
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!"
        }
        """
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Set new password
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            
            # Update token
            Token.objects.filter(user=request.user).delete()
            token = Token.objects.create(user=request.user)
            
            return Response({
                'message': 'Password changed successfully',
                'token': token.key
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip