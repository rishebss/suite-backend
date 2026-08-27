from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from authentication.models import User, Department, EmailVerificationToken, LoginAttempt, AuditLog


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'manager', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'purpose', 'is_used', 'created_at', 'expires_at']
    list_filter = ['purpose', 'is_used', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = ['id', 'token', 'created_at']


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['email', 'status', 'ip_address', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['email', 'ip_address']
    readonly_fields = ['id', 'created_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'action_target', 'status', 'ip_address', 'created_at']
    list_filter = ['action', 'status', 'created_at']
    search_fields = ['user__email', 'action_target__email', 'ip_address']
    readonly_fields = ['id', 'created_at', 'details', 'target_changes']
    fieldsets = (
        ('Action Info', {
            'fields': ('user', 'action', 'action_target', 'status')
        }),
        ('Request Info', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Change Tracking', {
            'fields': ('details', 'target_changes')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User model with email-based authentication
    """
    list_display = [
        'email', 'first_name', 'last_name', 'account_id', 'role',
        'is_email_verified', 'is_active', 'created_at'
    ]
    list_filter = [
        'role', 'is_active', 'is_email_verified', 'is_mobile_verified',
        'is_staff', 'is_superuser', 'created_at'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'account_id', 'mobile']
    readonly_fields = [
        'id', 'account_id', 'first_two_letters', 'first_two_numbers',
        'last_one_letter', 'last_two_numbers', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'mobile', 'gender', 'avatar')
        }),
        ('Organization', {
            'fields': ('role', 'departments', 'supervisor')
        }),
        ('Account ID Generation', {
            'fields': (
                'account_id', 'prefix', 'first_two_letters',
                'first_two_numbers', 'last_one_letter', 'last_two_numbers'
            ),
            'classes': ('collapse',)
        }),
        ('Verification Status', {
            'fields': ('is_email_verified', 'is_mobile_verified')
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Authentication', {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'mobile', 'gender')
        }),
        ('Organization', {
            'fields': ('role', 'departments', 'supervisor')
        }),
        ('Status', {
            'fields': ('is_active', 'is_staff')
        }),
    )
    
    ordering = ('-created_at',)
    filter_horizontal = ['groups', 'user_permissions', 'departments']

