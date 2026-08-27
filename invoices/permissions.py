from rest_framework import permissions


class IsInvoiceOwner(permissions.BasePermission):
    """Allow access only to the invoice's creator"""

    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class IsAdminReviewer(permissions.BasePermission):
    """Allow access only to Admin / Manager / is_staff users"""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (request.user.role in ['Admin', 'Manager'] or request.user.is_staff)
        )
