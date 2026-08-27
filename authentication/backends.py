from django.contrib.auth.backends import ModelBackend
from authentication.models import User


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that uses email instead of username
    """
    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        """
        Authenticate user using email and password
        """
        # Support both 'email' parameter and 'username' parameter for compatibility
        email_to_use = email or username
        
        if not email_to_use or not password:
            return None
        
        try:
            user = User.objects.get(email=email_to_use)
        except User.DoesNotExist:
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
