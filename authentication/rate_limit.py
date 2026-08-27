"""
Rate limiting utility for login attempts
"""
from django.utils import timezone
from datetime import timedelta
from authentication.models import LoginAttempt, User


def get_failed_attempts(identifier, time_window_minutes=15):
    """
    Get number of failed login attempts within time window
    
    Args:
        identifier: email or IP address
        time_window_minutes: lookback period
    
    Returns:
        count of failed attempts
    """
    cutoff_time = timezone.now() - timedelta(minutes=time_window_minutes)
    
    attempts = LoginAttempt.objects.filter(
        email=identifier,
        status='failed',
        created_at__gte=cutoff_time
    ).count()
    
    return attempts


def is_rate_limited(identifier, max_attempts=5, time_window_minutes=15):
    """
    Check if identifier is rate limited
    
    Args:
        identifier: email or IP address
        max_attempts: max failed attempts before blocking
        time_window_minutes: lookback period
    
    Returns:
        True if rate limited, False otherwise
    """
    failed_count = get_failed_attempts(identifier, time_window_minutes)
    return failed_count >= max_attempts


def log_login_attempt(email, ip_address, user_agent=None, success=False):
    """
    Log a login attempt
    
    Args:
        email: User email
        ip_address: Client IP address
        user_agent: Browser user agent
        success: True if login was successful
    """
    status = 'success' if success else 'failed'
    
    try:
        # Try to get user by email
        user = User.objects.get(email=email)
        user_id = user.id
    except User.DoesNotExist:
        user_id = None
    
    LoginAttempt.objects.create(
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent or '',
        status=status
    )


def get_client_ip(request):
    """
    Extract client IP address from request
    Handles proxy headers (X-Forwarded-For, etc.)
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can have multiple IPs, get the first one
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extract user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')
