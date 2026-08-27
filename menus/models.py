"""
Menu Management System Models
Handles dynamic menus, role assignments, products, and organizations
All models inherit from Main (UUIDField + timestamps)
"""
import uuid
from django.db import models
from django.utils.timezone import now
from django.conf import settings
from core.models import Main


class Organization(Main):
    """Multi-tenant organization for menu customization and product purchases"""
    name = models.CharField(max_length=256, unique=True)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_organizations')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'

    def __str__(self):
        return f"{self.name} ({self.owner.email})"


class Product(Main):
    """Represents a purchasable module (CRM, HR, Inventory, Accounts, etc)"""
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code: 'crm', 'hr', 'inventory', etc"
    )
    name = models.CharField(max_length=256, help_text="Display name: 'Customer Relations', 'Human Resources'")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.name} ({self.code})"


class OrgProductPurchase(Main):
    """Track which products each organization has purchased"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='product_purchases')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='organization_purchases')
    purchased_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # null = lifetime license
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'product')
        ordering = ['-purchased_at']
        verbose_name = 'Organization Product Purchase'
        verbose_name_plural = 'Organization Product Purchases'

    def is_valid(self):
        """Check if purchase is still active"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < now():
            return False
        return True

    def __str__(self):
        return f"{self.organization.name} → {self.product.code}"


class Menu(Main):
    """System and custom menus that can be assigned to roles"""
    MENU_TYPE_CHOICES = [
        ('SYSTEM', 'System Menu'),
        ('CUSTOM', 'Custom Menu'),
    ]

    type = models.CharField(
        max_length=10,
        choices=MENU_TYPE_CHOICES,
        default='SYSTEM',
        help_text="SYSTEM: Global menus managed by Superadmin. CUSTOM: Organization-specific menus"
    )
    code = models.CharField(
        max_length=100,
        help_text="Unique identifier: 'dashboard', 'crm', 'custom_reports'"
    )
    name = models.CharField(max_length=256, help_text="Display name: 'Dashboard', 'Customer Relations'")
    href = models.CharField(max_length=256, help_text="URL path: '/dashboard', '/crm'")
    icon = models.CharField(
        max_length=100,
        help_text="Lucide icon name: 'LayoutDashboard', 'Users', 'Settings', etc"
    )
    section = models.CharField(
        max_length=50,
        help_text="Menu section grouping: 'Operations', 'Settings', etc"
    )
    order = models.IntegerField(default=0, help_text="Sort order within section (0=first)")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Relationships
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_menus'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_menus',
        help_text="Organization for custom menus. NULL for system-wide menus"
    )
    required_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gated_menus',
        help_text="Menu only visible if organization has purchased this product"
    )

    class Meta:
        unique_together = ('organization', 'code')
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['type', 'is_active']),
            models.Index(fields=['section', 'order']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['code'],
                condition=models.Q(organization__isnull=True),
                name='unique_system_menu_code'
            )
        ]
        ordering = ['section', 'order', 'name']
        verbose_name = 'Menu'
        verbose_name_plural = 'Menus'

    def __str__(self):
        org = f" [{self.organization.slug}]" if self.organization else " [SYSTEM]"
        return f"{self.name}{org}"

    def can_edit(self, user):
        """Check if user can edit this menu"""
        if self.type == 'SYSTEM':
            return user.role == 'Superadmin'
        else:
            # CUSTOM menu: only superadmin or org admin can edit
            return (
                user.organization == self.organization and
                user.role in ['Superadmin', 'Admin']
            )

    def can_assign_user(self, user):
        """Check if user can assign this menu to an individual user"""
        if self.type == 'SYSTEM':
            return user.role in ['Superadmin', 'Admin']
        return self.can_edit(user)

    def can_delete(self, user):
        """Check if user can delete this menu"""
        if self.type == 'SYSTEM':
            return user.role == 'Superadmin'
        else:
            # CUSTOM menu: creator or org superadmin can delete
            return (
                user == self.created_by or (
                    user.organization == self.organization and
                    user.role == 'Superadmin'
                )
            )


class MenuRole(Main):
    """Maps menus to user roles for access control"""
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(
        max_length=50,
        help_text="User role: 'Superadmin', 'Admin', 'Manager', 'Staff', 'Vendor', 'User'"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Organization context. NULL for system-wide role assignments"
    )

    class Meta:
        unique_together = ('menu', 'role', 'organization')
        indexes = [
            models.Index(fields=['menu', 'role']),
            models.Index(fields=['organization', 'role']),
        ]
        verbose_name = 'Menu Role'
        verbose_name_plural = 'Menu Roles'

    def __str__(self):
        org = f" [{self.organization.slug}]" if self.organization else ""
        return f"{self.menu.code} → {self.role}{org}"


class MenuUser(Main):
    """Maps menus to individual users for custom access control"""
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='user_assignments')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_menus'
    )

    class Meta:
        unique_together = ('menu', 'user')
        indexes = [
            models.Index(fields=['menu', 'user']),
            models.Index(fields=['user', 'menu']),
        ]
        verbose_name = 'Menu User'
        verbose_name_plural = 'Menu Users'

    def __str__(self):
        return f"{self.menu.code} → {self.user.email}"
