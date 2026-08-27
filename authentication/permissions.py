"""
Permission classes for authentication and user management
"""
from rest_framework import permissions


class IsUserAdmin(permissions.BasePermission):
    """
    Allow only Superadmin or Admin users to manage users.
    Admins are scoped to their organization.
    """
    message = "You don't have permission to manage users."
    
    def has_permission(self, request, view):
        """Check if user has basic permission"""
        # Only superadmin and admin can manage users
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['Superadmin', 'Admin']
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permission"""
        # Superadmin can do anything
        if request.user.role == 'Superadmin':
            return True
        
        # Admin can only manage users in their organization
        if request.user.role == 'Admin':
            # For User objects, check organization
            if hasattr(obj, 'organization'):
                return obj.organization_id == request.user.organization_id
            return True
        
        return False


class IsSuperAdmin(permissions.BasePermission):
    """Allow only superadmin users"""
    message = "Only superadmins can perform this action."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'Superadmin'


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow admins to edit, but allow read access to anyone authenticated.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in ['Superadmin', 'Admin']


class CanViewOwnAuditLog(permissions.BasePermission):
    """
    Allow users to view their own audit log, admins can view all.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        obj here is the User whose audit log we're viewing
        """
        # Users can view their own audit log
        if request.user.id == obj.id:
            return True
        
        # Superadmin can view all
        if request.user.role == 'Superadmin':
            return True
        
        # Admin can view users in their organization
        if request.user.role == 'Admin':
            return obj.organization_id == request.user.organization_id
        
        # Supervisors can view subordinates' logs
        if obj.supervisor_id == request.user.id:
            return True
        
        return False


class CanManageDepartments(permissions.BasePermission):
    """
    Allow admin and above to manage departments
    """
    message = "You don't have permission to manage departments."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['Superadmin', 'Admin']
    
    def has_object_permission(self, request, view, obj):
        # Superadmin can do anything
        if request.user.role == 'Superadmin':
            return True
        
        # Admin scope: for now, allow all in their org (department doesn't have org field)
        if request.user.role == 'Admin':
            return True
        
        return False
