from rest_framework import permissions


# ============================================================================
# ITEM PERMISSIONS
# ============================================================================

class CanViewItems(permissions.BasePermission):
    """inventory.items.view"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class CanCreateItems(permissions.BasePermission):
    """inventory.items.create"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanEditItems(permissions.BasePermission):
    """inventory.items.edit"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanDeleteItems(permissions.BasePermission):
    """inventory.items.delete"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )


class CanImportItems(permissions.BasePermission):
    """inventory.items.import"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanExportItems(permissions.BasePermission):
    """inventory.items.export"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


# ============================================================================
# CATEGORY PERMISSIONS
# ============================================================================

class CanViewCategories(permissions.BasePermission):
    """inventory.categories.view"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class CanCreateCategories(permissions.BasePermission):
    """inventory.categories.create"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanEditCategories(permissions.BasePermission):
    """inventory.categories.edit"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanDeleteCategories(permissions.BasePermission):
    """inventory.categories.delete"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )


# ============================================================================
# UNIT PERMISSIONS
# ============================================================================

class CanViewUnits(permissions.BasePermission):
    """inventory.units.view"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class CanCreateUnits(permissions.BasePermission):
    """inventory.units.create"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanEditUnits(permissions.BasePermission):
    """inventory.units.edit"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanDeleteUnits(permissions.BasePermission):
    """inventory.units.delete"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )


# ============================================================================
# BRAND PERMISSIONS
# ============================================================================

class CanViewBrands(permissions.BasePermission):
    """inventory.brands.view"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class CanCreateBrands(permissions.BasePermission):
    """inventory.brands.create"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanEditBrands(permissions.BasePermission):
    """inventory.brands.edit"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanDeleteBrands(permissions.BasePermission):
    """inventory.brands.delete"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )


# ============================================================================
# LOCATION TYPE PERMISSIONS
# ============================================================================

class CanViewLocationTypes(permissions.BasePermission):
    """inventory.location_types.view"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class CanCreateLocationTypes(permissions.BasePermission):
    """inventory.location_types.create"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanEditLocationTypes(permissions.BasePermission):
    """inventory.location_types.edit"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanDeleteLocationTypes(permissions.BasePermission):
    """inventory.location_types.delete"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )


# ============================================================================
# LOCATION PERMISSIONS
# ============================================================================

class CanViewLocations(permissions.BasePermission):
    """inventory.locations.view"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class CanCreateLocations(permissions.BasePermission):
    """inventory.locations.create"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanEditLocations(permissions.BasePermission):
    """inventory.locations.edit"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanDeleteLocations(permissions.BasePermission):
    """inventory.locations.delete"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )


# ============================================================================
# STOCK PERMISSIONS
# ============================================================================

class CanViewStock(permissions.BasePermission):
    """inventory.stock.view"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class CanExportStock(permissions.BasePermission):
    """inventory.stock.export"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class CanViewStockSnapshot(permissions.BasePermission):
    """inventory.stock.snapshot"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanViewStockValuation(permissions.BasePermission):
    """inventory.stock.valuation"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


# ============================================================================
# TRANSFER PERMISSIONS
# ============================================================================

class CanViewTransfers(permissions.BasePermission):
    """inventory.transfers.view"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )


class CanCreateTransfers(permissions.BasePermission):
    """inventory.transfers.create"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanEditTransfers(permissions.BasePermission):
    """inventory.transfers.edit"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanDeleteTransfers(permissions.BasePermission):
    """inventory.transfers.delete"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )


class CanSubmitTransfer(permissions.BasePermission):
    """inventory.transfers.submit"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanApproveTransfer(permissions.BasePermission):
    """inventory.transfers.approve"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )


class CanReceiveTransfer(permissions.BasePermission):
    """inventory.transfers.receive"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanExportTransfers(permissions.BasePermission):
    """inventory.transfers.export"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated
        )
