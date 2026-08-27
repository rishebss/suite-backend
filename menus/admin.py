"""
Django Admin configuration for Menu Management System
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Q
from menus.models import Menu, MenuRole, Organization, Product, OrgProductPurchase


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin for Organization model"""
    list_display = ('name', 'slug', 'owner_email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'owner__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'slug', 'owner')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = 'Owner Email'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin for Product model"""
    list_display = ('code', 'name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('code', 'name')
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('Product Information', {
            'fields': ('id', 'code', 'name', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


class OrgProductPurchaseInline(admin.TabularInline):
    """Inline admin for OrgProductPurchase"""
    model = OrgProductPurchase
    extra = 1
    readonly_fields = ('id', 'purchased_at', 'created_at')
    fields = ('product', 'purchased_at', 'expires_at', 'is_active')


@admin.register(OrgProductPurchase)
class OrgProductPurchaseAdmin(admin.ModelAdmin):
    """Admin for OrgProductPurchase model"""
    list_display = ('organization', 'product', 'is_valid_status', 'purchased_at', 'expires_at')
    list_filter = ('is_active', 'purchased_at', 'product')
    search_fields = ('organization__name', 'product__code', 'product__name')
    readonly_fields = ('id', 'purchased_at', 'created_at')
    fieldsets = (
        ('Purchase Information', {
            'fields': ('id', 'organization', 'product')
        }),
        ('Validity', {
            'fields': ('purchased_at', 'expires_at', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def is_valid_status(self, obj):
        """Show validity status with color"""
        is_valid = obj.is_valid()
        color = 'green' if is_valid else 'red'
        text = '✓ Valid' if is_valid else '✗ Invalid'
        return format_html(f'<span style="color: {color};">{text}</span>')
    is_valid_status.short_description = 'Status'


class MenuRoleInline(admin.TabularInline):
    """Inline admin for MenuRole"""
    model = MenuRole
    extra = 1
    readonly_fields = ('id', 'created_at')
    fields = ('role', 'organization', 'created_at')


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    """Admin for Menu model"""
    list_display = ('name', 'code', 'type_badge', 'section', 'icon_preview', 'is_active', 'created_at')
    list_filter = ('type', 'is_active', 'section', 'organization', 'created_at')
    search_fields = ('code', 'name', 'section')
    readonly_fields = ('id', 'created_by', 'created_at', 'updated_at')
    inlines = [MenuRoleInline]
    fieldsets = (
        ('Menu Information', {
            'fields': ('id', 'code', 'name', 'href', 'icon', 'description')
        }),
        ('Organization & Type', {
            'fields': ('type', 'organization', 'required_product')
        }),
        ('Display', {
            'fields': ('section', 'order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Auto-set created_by when creating"""
        if not change:  # Creating new menu
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def type_badge(self, obj):
        """Show type as colored badge"""
        color = 'blue' if obj.type == 'SYSTEM' else 'green'
        return format_html(f'<span style="background-color: {color}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{obj.type}</span>')
    type_badge.short_description = 'Type'

    def icon_preview(self, obj):
        """Show icon name"""
        return obj.icon
    icon_preview.short_description = 'Icon'

    def get_queryset(self, request):
        """Filter menus based on user role"""
        qs = super().get_queryset(request)
        # Superadmin sees all, others see only their organization's
        if request.user.role != 'Superadmin':
            qs = qs.filter(
                Q(type='SYSTEM') |
                Q(type='CUSTOM', organization=request.user.organization)
            )
        return qs

    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user"""
        form = super().get_form(request, obj, **kwargs)
        # Non-superadmin users can only edit CUSTOM menus
        if request.user.role != 'Superadmin':
            del form.base_fields['type']  # Hide type field
        return form


@admin.register(MenuRole)
class MenuRoleAdmin(admin.ModelAdmin):
    """Admin for MenuRole model"""
    list_display = ('menu', 'role', 'organization', 'created_at')
    list_filter = ('role', 'organization', 'created_at')
    search_fields = ('menu__code', 'menu__name', 'role')
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('Role Assignment', {
            'fields': ('id', 'menu', 'role', 'organization')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
