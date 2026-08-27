"""
Serializers for Menu Management System
"""
from rest_framework import serializers
from menus.models import Menu, MenuRole, MenuUser, Organization, Product, OrgProductPurchase


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model"""
    class Meta:
        model = Product
        fields = ['id', 'code', 'name', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class OrgProductPurchaseSerializer(serializers.ModelSerializer):
    """Serializer for OrgProductPurchase model"""
    product = ProductSerializer(read_only=True)
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = OrgProductPurchase
        fields = ['id', 'product', 'purchased_at', 'expires_at', 'is_active', 'is_valid', 'created_at']
        read_only_fields = ['id', 'purchased_at', 'created_at']

    def get_is_valid(self, obj):
        """Check if purchase is currently valid"""
        return obj.is_valid()


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model"""
    products = OrgProductPurchaseSerializer(
        source='product_purchases',
        many=True,
        read_only=True
    )
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)

    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'owner', 'owner_name', 'is_active', 'products', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class MenuRoleSerializer(serializers.ModelSerializer):
    """Serializer for MenuRole model"""
    class Meta:
        model = MenuRole
        fields = ['id', 'menu', 'role', 'organization', 'created_at']
        read_only_fields = ['id', 'created_at']


class MenuUserSerializer(serializers.ModelSerializer):
    """Serializer for MenuUser model - individual user menu assignments"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = MenuUser
        fields = ['id', 'menu', 'user', 'user_email', 'user_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class MenuListSerializer(serializers.ModelSerializer):
    """Simplified serializer for menu lists (minimal data)"""
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = ['id', 'code', 'name', 'href', 'icon', 'section', 'order', 'roles']
        read_only_fields = ['id']

    def get_roles(self, obj):
        request = self.context.get('request')
        user = request.user if request else None

        roles = obj.roles.all()
        if user and user.role != 'Superadmin' and getattr(user, 'organization_id', None):
            roles = [r for r in roles if r.organization_id is None or r.organization_id == user.organization_id]

        return [r.role for r in roles]


class MenuDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for menu operations"""
    roles = MenuRoleSerializer(many=True, read_only=True)
    user_assignments = MenuUserSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    required_product_name = serializers.CharField(source='required_product.name', read_only=True)

    class Meta:
        model = Menu
        fields = [
            'id', 'type', 'code', 'name', 'href', 'icon', 'section', 'order',
            'description', 'is_active', 'created_by', 'created_by_name',
            'organization', 'organization_name', 'required_product', 'required_product_name',
            'roles', 'user_assignments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class MenuCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating menus"""
    class Meta:
        model = Menu
        fields = [
            'type', 'code', 'name', 'href', 'icon', 'section', 'order',
            'description', 'is_active', 'organization', 'required_product'
        ]

    def validate_code(self, value):
        """Validate code is alphanumeric with underscores"""
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError(
                "Code must contain only alphanumeric characters and underscores"
            )
        return value

    def validate_href(self, value):
        """Validate href starts with /"""
        if not value.startswith('/'):
            raise serializers.ValidationError("href must start with /")
        return value


class MenuMyMenusResponseSerializer(serializers.Serializer):
    """Response serializer for GET /api/menus/my-menus/ endpoint"""
    sections = serializers.DictField(child=serializers.ListField())
    all_menus = MenuListSerializer(many=True)


class AssignMenuToRoleSerializer(serializers.Serializer):
    """Serializer for assigning menu to role"""
    role = serializers.CharField(max_length=50)
    organization = serializers.UUIDField(required=False, allow_null=True)

    def validate_role(self, value):
        """Validate role is valid"""
        valid_roles = ['Superadmin', 'Admin', 'Manager', 'Staff', 'Vendor', 'User']
        if value not in valid_roles:
            raise serializers.ValidationError(
                f"Invalid role. Valid roles: {', '.join(valid_roles)}"
            )
        return value


class AssignMenuToUserSerializer(serializers.Serializer):
    """Serializer for assigning menu to individual user"""
    user_id = serializers.UUIDField()

    def validate_user_id(self, value):
        """Validate user exists"""
        from authentication.models import User
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value
