# apps/users/views.py - UPDATE AuthViewSet

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import User, EmailOTP
from .serializers import (
    RegisterRequestSerializer, 
    VerifyOTPSerializer,
    LoginSerializer, 
    UserProfileSerializer
)
from .email_service import send_otp_email

class AuthViewSet(viewsets.ViewSet):
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register_request(self, request):
        """Step 1: Validate data and send OTP"""
        serializer = RegisterRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            # Create OTP and save temp data
            temp_data = {
                'email': email,
                'username': serializer.validated_data['username'],
                'password': serializer.validated_data['password'],
                'first_name': serializer.validated_data['first_name'],
                'last_name': serializer.validated_data['last_name'],
                'student_id': serializer.validated_data['student_id'],
            }
            
            otp = EmailOTP.create_otp(email, temp_data)
            
            # Send OTP email
            email_sent = send_otp_email(email, otp.otp_code)
            
            if email_sent:
                return Response({
                    'message': 'OTP sent to your email',
                    'email': email,
                    'expires_in': '10 minutes'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to send OTP email. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def verify_otp(self, request):
        """Step 2: Verify OTP and create user"""
        serializer = VerifyOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            otp = serializer.validated_data['otp_instance']
            
            # Get temp data
            temp_data = otp.temp_data
            
            if not temp_data:
                return Response({
                    'error': 'Registration data not found. Please start registration again.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create user
            try:
                user = User.objects.create_user(
                    email=temp_data['email'],
                    username=temp_data['username'],
                    password=temp_data['password'],
                    first_name=temp_data['first_name'],
                    last_name=temp_data['last_name'],
                    student_id=temp_data['student_id'],
                    user_type='student',
                    email_verified=True
                )
                
                # Mark OTP as used
                otp.is_used = True
                otp.save()
                
                # Create token
                token, _ = Token.objects.get_or_create(user=user)
                
                return Response({
                    'message': 'Registration successful',
                    'token': token.key,
                    'user': {
                        'user_id': user.user_id,
                        'email': user.email,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'student_id': user.student_id,
                    }
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Failed to create user: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def resend_otp(self, request):
        """Resend OTP"""
        email = request.data.get('email')
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find latest OTP temp data
        latest_otp = EmailOTP.objects.filter(email=email).order_by('-created_at').first()
        
        if not latest_otp or not latest_otp.temp_data:
            return Response({
                'error': 'No pending registration found. Please start registration again.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create new OTP
        new_otp = EmailOTP.create_otp(email, latest_otp.temp_data)
        
        # Send email
        email_sent = send_otp_email(email, new_otp.otp_code)
        
        if email_sent:
            return Response({
                'message': 'OTP resent successfully',
                'expires_in': '10 minutes'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to send OTP email'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """Login user"""
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            user = authenticate(username=email, password=password)
            
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                
                return Response({
                    'token': token.key,
                    'user': {
                        'user_id': user.user_id,
                        'email': user.email,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    }
                })
            else:
                return Response({
                    'error': 'Invalid email or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Logout user"""
        request.user.auth_token.delete()
        return Response({'message': 'Logged out successfully'})
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """Get user profile"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update user profile"""
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)