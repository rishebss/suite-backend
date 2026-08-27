from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from authentication.models import User
from authentication.serializers import (
    UserSerializer, UserRegistrationSerializer, CustomTokenObtainPairSerializer,
    LoginSerializer, PasswordChangeSerializer, ProfileUpdateSerializer
)


# JWT Token Views
class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token obtain view using email instead of username"""
    serializer_class = CustomTokenObtainPairSerializer
    

class CustomTokenRefreshView(TokenRefreshView):
    """JWT token refresh view"""
    pass


# Registration and Authentication API Views
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def register_user(request):
    """
    Register a new user
    POST /api/auth/register/
    Request body: {
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "mobile": "1234567890",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
        "role": "User",
        "gender": "Male"
    }
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "success": True,
            "message": "User registered successfully. Please verify your email.",
            "data": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        "success": False,
        "message": "Registration failed",
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def login_user(request):
    """
    Login user with email and password
    POST /api/auth/login/
    Request body: {
        "email": "user@example.com",
        "password": "SecurePass123!"
    }
    """
    from authentication.rate_limit import is_rate_limited, log_login_attempt, get_client_ip, get_user_agent
    from authentication.audit_logger import log_login
    
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "success": False,
            "message": "Invalid input",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Check rate limiting
    if is_rate_limited(email):
        return Response({
            "success": False,
            "message": "Too many failed login attempts. Please try again after 15 minutes."
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    # Use email to authenticate
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Log failed attempt (non-blocking — don't let logging errors break login)
        try:
            log_login_attempt(email, ip_address, user_agent, success=False)
        except Exception:
            pass
        return Response({
            "success": False,
            "message": "Invalid email or password"
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.check_password(password):
        # Log failed attempt (non-blocking)
        try:
            log_login_attempt(email, ip_address, user_agent, success=False)
            log_login(user, ip_address, user_agent, success=False)
        except Exception:
            pass
        return Response({
            "success": False,
            "message": "Invalid email or password"
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    if not user.is_active:
        return Response({
            "success": False,
            "message": "User account is inactive"
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
    # Also login to session for session-based auth compatibility
    # Set the backend attribute for session login (required with multiple backends)
    user.backend = 'authentication.backends.EmailBackend'
    login(request, user, backend='authentication.backends.EmailBackend')
    
    # Log successful login
    log_login_attempt(email, ip_address, user_agent, success=True)
    log_login(user, ip_address, user_agent, success=True)
    
    return Response({
        "success": True,
        "message": "Login successful",
        "data": {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }
    }, status=status.HTTP_200_OK)
    
    # Log successful login after building response (non-blocking)
    try:
        log_login_attempt(email, ip_address, user_agent, success=True)
        log_login(user, ip_address, user_agent, success=True)
    except Exception:
        pass
    
    return response_data


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request):
    """
    Logout user
    POST /api/auth/logout/
    """
    from authentication.audit_logger import log_logout
    from authentication.rate_limit import get_client_ip, get_user_agent
    
    user = request.user
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Log logout
    log_logout(user, ip_address, user_agent)
    
    logout(request)
    return Response({
        "success": True,
        "message": "Logout successful"
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_profile(request):
    """
    Get current user profile
    GET /api/auth/profile/
    """
    serializer = UserSerializer(request.user)
    return Response({
        "success": True,
        "data": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_user_profile(request):
    """
    Update current user profile
    PUT/PATCH /api/auth/profile/update/
    Request body: {
        "first_name": "John",
        "last_name": "Doe",
        "mobile": "1234567890",
        "gender": "Male"
    }
    """
    serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "success": True,
            "message": "Profile updated successfully",
            "data": UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)
    
    return Response({
        "success": False,
        "message": "Update failed",
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_password(request):
    """
    Verify current password without changing it
    POST /api/auth/verify-password/
    Request body: {
        "password": "CurrentPass123!"
    }
    """
    password = request.data.get('password')
    if not password:
        return Response({
            "success": False,
            "message": "Password is required"
        }, status=status.HTTP_400_BAD_REQUEST)

    if request.user.check_password(password):
        return Response({
            "success": True,
            "message": "Password verified"
        }, status=status.HTTP_200_OK)

    return Response({
        "success": False,
        "message": "Current password is incorrect"
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """
    Change user password
    POST /api/auth/change-password/
    Request body: {
        "current_password": "CurrentPass123!",
        "new_password": "NewPass123!"
    }
    """
    serializer = PasswordChangeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "success": False,
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    # Check current password
    if not user.check_password(serializer.validated_data['current_password']):
        return Response({
            "success": False,
            "message": "Current password is incorrect"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Set new password
    user.set_password(serializer.validated_data['new_password'])
    user.save()
    
    # Log password change
    from authentication.audit_logger import log_password_change
    from authentication.rate_limit import get_client_ip, get_user_agent
    log_password_change(
        user,
        get_client_ip(request),
        get_user_agent(request),
        success=True
    )
    
    return Response({
        "success": True,
        "message": "Password changed successfully"
    }, status=status.HTTP_200_OK)


# Email Verification Views
from authentication.email_service import (
    send_verification_email, verify_email_token,
    send_password_reset_email, reset_password
)
from authentication.serializers import (
    SendVerificationEmailSerializer, VerifyEmailSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer
)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def send_verification_email_view(request):
    """
    Send verification email
    POST /api/auth/send-verification-email/
    Request body: {
        "email": "user@example.com",
        "purpose": "email_verify"  # or "password_reset"
    }
    """
    serializer = SendVerificationEmailSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    purpose = serializer.validated_data.get('purpose', 'email_verify')
    
    try:
        user = User.objects.get(email=email)
        result = send_verification_email(user, purpose)
        
        status_code = status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST
        return Response({
            "success": result['success'],
            "message": result['message']
        }, status=status_code)
    except User.DoesNotExist:
        # For security, don't reveal if user exists
        return Response({
            "success": True,
            "message": "If the email exists in our system, a verification code has been sent"
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def verify_email_view(request):
    """
    Verify email with token
    POST /api/auth/verify-email/
    Request body: {
        "email": "user@example.com",
        "token": "123456",
        "purpose": "email_verify"
    }
    """
    serializer = VerifyEmailSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    token = serializer.validated_data['token']
    purpose = serializer.validated_data.get('purpose', 'email_verify')
    
    try:
        user = User.objects.get(email=email)
        result = verify_email_token(user, token, purpose)
        
        status_code = status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST
        return Response({
            "success": result['success'],
            "message": result['message']
        }, status=status_code)
    except User.DoesNotExist:
        return Response({
            "success": False,
            "message": "User not found"
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def forgot_password_view(request):
    """
    Request password reset
    POST /api/auth/forgot-password/
    Request body: {
        "email": "user@example.com"
    }
    """
    serializer = ForgotPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    result = send_password_reset_email(email)
    
    return Response({
        "success": result['success'],
        "message": result['message']
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def reset_password_view(request):
    """
    Reset password with token
    POST /api/auth/reset-password/
    Request body: {
        "email": "user@example.com",
        "token": "123456",
        "new_password": "NewSecurePass123!",
        "new_password_confirm": "NewSecurePass123!"
    }
    """
    serializer = ResetPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']
    
    result = reset_password(email, token, new_password)
    
    status_code = status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST
    return Response({
        "success": result['success'],
        "message": result['message']
    }, status=status_code)


