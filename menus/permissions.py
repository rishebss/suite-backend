"""
Custom permission classes for Menu Management System
"""
from rest_framework import permissions


class IsSuperadmin(permissions.BasePermission):
    """
    Only Superadmin users can access the resource
    """
    message = 'Only Superadmin users can access this resource'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'Superadmin'
        )


class IsOrgOwner(permissions.BasePermission):
    """
    User is the organization owner
    """
    message = 'Only organization owners can access this resource'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Get organization ID from path
        org_id = view.kwargs.get('org_id')
        if not org_id:
            return True  # Let other checks handle

        # Check if user owns the organization
        try:
            from menus.models import Organization
            org = Organization.objects.get(id=org_id)
            return request.user == org.owner
        except Organization.DoesNotExist:
            return False


class CanEditMenu(permissions.BasePermission):
    """
    User can edit this menu based on type and organization
    """
    message = 'You do not have permission to edit this menu'

    def has_object_permission(self, request, view, obj):
        return obj.can_edit(request.user)


class CanDeleteMenu(permissions.BasePermission):
    """
    User can delete this menu
    """
    message = 'You do not have permission to delete this menu'

    def has_object_permission(self, request, view, obj):
        return obj.can_delete(request.user)


class IsOrgAdminOrSuperadmin(permissions.BasePermission):
    """
    User is either organization admin or superadmin
    """
    message = 'You do not have permission to perform this action'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.role in ['Superadmin', 'Admin']


class HasOrganization(permissions.BasePermission):
    """
    User belongs to an organization
    """
    message = 'You must belong to an organization to access this resource'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # For now, organizations are optional
        # This can be made mandatory later
        return True
