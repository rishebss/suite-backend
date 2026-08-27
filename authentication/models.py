import uuid
import secrets
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from core.models import Main
from authentication.managers import CustomUserManager


# Constants for User Roles and Gender
USER_ROLE = (
    ('Superadmin', "Superadmin"),
    ('Admin', "Admin"),
    ('Manager', "Manager"),
    ('Staff', "Staff"),
    ("Vendor", "Vendor"),
    ("Finance", "Finance"),
    ("Payroll Executive", "Payroll Executive"),
    ("User", "User"),
    ("Others", "Others"),
)

GENDER = (
    ('Male', "Male"),
    ('Female', "Female"),
    ('Other', "Other"),
)

# Helper functions for ID generation
def increment_one_letter(letter):
    """Increment a single letter (A-Z, then wrap around)"""
    if letter == 'Z':
        return 'A'
    return chr(ord(letter) + 1)


def increment_two_letters(letters):
    """Increment two letters (AA, AB, ..., AZ, BA, ...)"""
    first, second = letters[0], letters[1]
    
    if second == 'Z':
        second = 'A'
        if first == 'Z':
            return 'AA'
        first = chr(ord(first) + 1)
    else:
        second = chr(ord(second) + 1)
    
    return first + second


def increment_two_digits(number):
    """Increment a two-digit number (00-99, then wrap to 00)"""
    if number >= 99:
        return 0
    return number + 1


class Department(Main):
    """Department/Team model for organizing users"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    manager = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin, Main):
    """
    Custom User model with UUID primary key, email-based authentication,
    and role-based account ID generation
    Inherits id (UUID), created_at, updated_at from Main
    """
    # Override id to prevent duplicate from Main
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Authentication fields
    email = models.EmailField(
        unique=True,
        blank=False,
        max_length=200,
        error_messages={'unique': "A user with that email already exists."}
    )
    password = models.CharField(max_length=128)
    
    # Personal information
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    mobile = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        error_messages={'unique': "A user with that mobile already exists."}
    )
    gender = models.CharField(max_length=10, choices=GENDER, blank=True, null=True)
    
    # Role and organization
    role = models.CharField(
        choices=USER_ROLE,
        max_length=100,
        default='User',
        help_text='ID generation depends on the role. Once you submit it will be permanent.'
    )
    departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name='users'
    )
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    organization = models.ForeignKey(
        'menus.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text='Organization/Company this user belongs to. Superadmins can be global (NULL)'
    )

    # Account ID generation fields
    prefix = models.CharField(max_length=10, default="SA")
    first_two_letters = models.CharField(max_length=2, default="AA")
    first_two_numbers = models.IntegerField(default=0)
    last_one_letter = models.CharField(max_length=1, default="A")
    last_two_numbers = models.IntegerField(default=0)
    account_id = models.CharField(max_length=220, unique=True)
    
    # Verification and status
    is_email_verified = models.BooleanField(default=False)
    is_mobile_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Avatar/Profile
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(blank=True, null=True)

    # Required fields for CustomUserManager
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = 'User'
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['account_id']),
            models.Index(fields=['mobile']),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the user's full name"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        """Return the user's short name"""
        return self.first_name or self.email

    def generate_id_number(self):
        """
        Generate unique account ID based on role
        Format: PREFIX-ROLE-AA00A00
        Example: SA-ADM-AA00A00
        """
        try:
            # Get the last created user
            last_entry = User.objects.exclude(pk=self.pk).order_by('-created_at').first()
            
            # Determine role abbreviation
            role_map = {
                'Superadmin': 'SUP',
                'Admin': 'ADM',
                'Manager': 'MGR',
                'Staff': 'STF',
                'Vendor': 'VDR',
                'Finance': 'FIN',
                'Payroll Executive': 'PAY',
                'User': 'USR',
                'Others': 'OTH',
            }
            rle = role_map.get(self.role, 'OTH')

            if last_entry:
                # Copy previous values as starting point
                self.last_one_letter = last_entry.last_one_letter
                self.first_two_numbers = last_entry.first_two_numbers
                self.first_two_letters = last_entry.first_two_letters
                
                # Increment the last two numbers
                self.last_two_numbers = increment_two_digits(last_entry.last_two_numbers)
                
                # If last_two_numbers wrapped around (was 99, now 0), increment last_one_letter
                if last_entry.last_two_numbers == 99:
                    self.last_one_letter = increment_one_letter(last_entry.last_one_letter)
                
                # If last_one_letter wrapped around (was Z, now A), increment first_two_numbers
                if last_entry.last_one_letter == 'Z' and last_entry.last_two_numbers == 99:
                    self.first_two_numbers = increment_two_digits(last_entry.first_two_numbers)
                
                # If first_two_numbers wrapped around (was 99, now 0), increment first_two_letters
                if (last_entry.first_two_numbers == 99 and 
                    last_entry.last_one_letter == 'Z' and 
                    last_entry.last_two_numbers == 99):
                    self.first_two_letters = increment_two_letters(last_entry.first_two_letters)
            else:
                # First user ever
                self.first_two_letters = "AA"
                self.first_two_numbers = 0
                self.last_one_letter = "A"
                self.last_two_numbers = 0

            # Generate final account ID
            self.account_id = f"{self.prefix}-{rle}-{self.first_two_letters}{self.first_two_numbers:02d}{self.last_one_letter}{self.last_two_numbers:02d}"
        except Exception as e:
            # Fallback ID generation
            print(f"Error generating ID: {e}")
            self.account_id = f"{self.prefix}-{role_map.get(self.role, 'OTH')}-AA00A00"

    def save(self, *args, **kwargs):
        """Override save to generate account_id if not present"""
        if not self.account_id:
            self.generate_id_number()
        
        # Update last_login if not already set
        if self.last_login is None:
            self.last_login = timezone.now()
        
        super().save(*args, **kwargs)


import secrets
import string


class EmailVerificationToken(Main):
    """Model for email verification and password reset tokens"""
    PURPOSE_CHOICES = (
        ('email_verify', 'Email Verification'),
        ('password_reset', 'Password Reset'),
        ('mobile_verify', 'Mobile Verification'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=6, unique=True)  # 6-digit OTP
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'purpose']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.purpose}"
    
    @staticmethod
    def generate_token():
        """Generate a random 6-digit OTP"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    def is_expired(self):
        """Check if token has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()
    
    def mark_as_used(self):
        """Mark token as used"""
        self.is_used = True
        self.save()


class LoginAttempt(Main):
    """Model for tracking login attempts (for rate limiting)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='login_attempts')
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('blocked', 'Blocked'),
        ],
        default='failed'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.status} - {self.created_at}"


class AuditLog(Main):
    """Model for logging user actions (audit trail)"""
    ACTION_CHOICES = (
        # Authentication actions
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('email_change', 'Email Change'),
        ('email_verify', 'Email Verification'),
        ('mobile_verify', 'Mobile Verification'),
        ('2fa_setup', '2FA Setup'),
        ('2fa_attempt', '2FA Attempt'),
        ('profile_update', 'Profile Update'),
        # User management actions
        ('user_create', 'User Created'),
        ('user_update', 'User Updated'),
        ('user_delete', 'User Deleted'),
        ('user_activate', 'User Activated'),
        ('user_role_change', 'User Role Changed'),
        ('user_department_change', 'User Department Changed'),
        ('user_supervisor_change', 'Supervisor Assignment Changed'),
        # Invoice actions
        ('invoice_create', 'Invoice Created'),
        ('invoice_update', 'Invoice Updated'),
        ('invoice_delete', 'Invoice Deleted'),
        ('invoice_submit', 'Invoice Submitted'),
        ('invoice_approve', 'Invoice Approved'),
        ('invoice_reject', 'Invoice Rejected'),
        ('invoice_download', 'Invoice Downloaded'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    # action_target: Which user was affected by the action (for user management operations)
    action_target = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs_as_target',
        help_text='The user that was affected by this action (for user management operations)'
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('pending', 'Pending'),
        ],
        default='success'
    )
    details = models.JSONField(default=dict, blank=True)
    # target_changes: What fields changed during updates (useful for tracking what was modified)
    target_changes = models.JSONField(
        default=dict,
        blank=True,
        help_text='Stores what fields changed with old/new values for update operations'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['action_target', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.created_at}"


