# apps/users/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer

class AuthViewSet(viewsets.ViewSet):
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """
        Student Registration
        POST /api/auth/register/
        {
            "email": "student@example.com",
            "username": "johnsmith",
            "password": "password123",
            "password_confirm": "password123",
            "first_name": "John",
            "last_name": "Smith",
            "student_id": "123456",
            "phone": "+95912345678",
            "country": "Myanmar"
        }
        """
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """
        Login
        POST /api/auth/login/
        {
            "email": "student@example.com",
            "password": "password123"
        }
        """
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserProfileSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Logout
        POST /api/auth/logout/
        Header: Authorization: Token <token>
        """
        request.user.auth_token.delete()
        return Response({'message': 'Logged out successfully'})
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """
        Get Profile
        GET /api/auth/profile/
        Header: Authorization: Token <token>
        """
        return Response(UserProfileSerializer(request.user).data)
    
    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """
        Update Profile
        PUT /api/auth/update_profile/
        Header: Authorization: Token <token>
        """
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)