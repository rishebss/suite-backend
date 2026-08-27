from rest_framework import serializers
from inventory.models import (
    ItemCategory, Unit, UnitConversion, Brand, InventoryItem,
    CustomFieldDefinition, InventoryLocationType, InventoryLocation,
    StockLedger, StockSummary, InventoryTransfer, InventoryTransferItem,
    InventoryTransferAttachment
)


# ============================================================================
# CATEGORY SERIALIZERS
# ============================================================================

class CategoryTreeSerializer(serializers.ModelSerializer):
    """Nested serializer for tree view with item counts."""
    children = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.category_name', read_only=True, default='')

    class Meta:
        model = ItemCategory
        fields = [
            'id', 'category_code', 'category_name', 'parent', 'parent_name',
            'description', 'status', 'item_count', 'children',
            'created_at', 'updated_at',
        ]

    def get_children(self, obj):
        qs = obj.children.all()
        if 'status' in self.context.get('filters', {}):
            qs = qs.filter(status=self.context['filters']['status'])
        return CategoryTreeSerializer(qs, many=True, context=self.context).data

    def get_item_count(self, obj):
        return obj.items.count()


class ItemCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.category_name', read_only=True, default='')

    class Meta:
        model = ItemCategory
        fields = [
            'id', 'category_code', 'category_name', 'parent', 'parent_name',
            'description', 'status', 'item_count', 'children',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_children(self, obj):
        return ItemCategorySerializer(obj.children.all(), many=True).data

    def get_item_count(self, obj):
        return obj.items.count()

    def validate(self, data):
        tenant_id = self.context['request'].user.organization_id
        category_code = data.get('category_code')
        instance = self.instance

        if category_code:
            qs = ItemCategory.objects.filter(
                tenant_id=tenant_id,
                category_code=category_code
            )
            if instance:
                qs = qs.exclude(id=instance.id)
            if qs.exists():
                raise serializers.ValidationError({
                    'category_code': f"Category code '{category_code}' already exists."
                })
        return data


class ItemCategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdown/reference data."""
    parent_name = serializers.CharField(source='parent.category_name', read_only=True, default='')

    class Meta:
        model = ItemCategory
        fields = ['id', 'category_code', 'category_name', 'parent_name', 'status']


# ============================================================================
# UNIT SERIALIZERS
# ============================================================================

class UnitConversionSerializer(serializers.ModelSerializer):
    from_unit_name = serializers.CharField(source='from_unit.unit_name', read_only=True)
    to_unit_name = serializers.CharField(source='to_unit.unit_name', read_only=True)

    class Meta:
        model = UnitConversion
        fields = [
            'id', 'from_unit', 'from_unit_name', 'to_unit', 'to_unit_name',
            'conversion_factor', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        tenant_id = self.context['request'].user.organization_id
        from_unit = data.get('from_unit')
        to_unit = data.get('to_unit')

        if from_unit and to_unit and from_unit == to_unit:
            raise serializers.ValidationError(
                "Cannot create a conversion between the same unit."
            )

        if from_unit and to_unit:
            qs = UnitConversion.objects.filter(
                tenant_id=tenant_id,
                from_unit=from_unit,
                to_unit=to_unit,
            )
            instance = self.instance
            if instance:
                qs = qs.exclude(id=instance.id)
            if qs.exists():
                raise serializers.ValidationError(
                    "This conversion already exists."
                )

        if 'conversion_factor' in data and data.get('conversion_factor', 0) <= 0:
            raise serializers.ValidationError({
                'conversion_factor': 'Conversion factor must be greater than 0.'
            })

        return data


class UnitSerializer(serializers.ModelSerializer):
    conversions = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = [
            'id', 'unit_code', 'unit_name', 'symbol', 'description',
            'status', 'conversions', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_conversions(self, obj):
        conversions_from = UnitConversion.objects.filter(from_unit=obj)
        conversions_to = UnitConversion.objects.filter(to_unit=obj)
        qs = list(conversions_from) + list(conversions_to)
        return UnitConversionSerializer(qs, many=True).data

    def validate(self, data):
        tenant_id = self.context['request'].user.organization_id
        unit_code = data.get('unit_code')
        instance = self.instance

        if unit_code:
            qs = Unit.objects.filter(
                tenant_id=tenant_id,
                unit_code=unit_code
            )
            if instance:
                qs = qs.exclude(id=instance.id)
            if qs.exists():
                raise serializers.ValidationError({
                    'unit_code': f"Unit code '{unit_code}' already exists."
                })
        return data


class UnitListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdown/reference data."""
    class Meta:
        model = Unit
        fields = ['id', 'unit_code', 'unit_name', 'symbol', 'status']


# ============================================================================
# BRAND SERIALIZERS
# ============================================================================

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = [
            'id', 'brand_code', 'brand_name', 'description',
            'logo_url', 'website', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        tenant_id = self.context['request'].user.organization_id
        brand_code = data.get('brand_code')
        instance = self.instance

        if brand_code:
            qs = Brand.objects.filter(
                tenant_id=tenant_id,
                brand_code=brand_code
            )
            if instance:
                qs = qs.exclude(id=instance.id)
            if qs.exists():
                raise serializers.ValidationError({
                    'brand_code': f"Brand code '{brand_code}' already exists."
                })
        return data


class BrandListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdown/reference data."""
    class Meta:
        model = Brand
        fields = ['id', 'brand_code', 'brand_name', 'status']


# ============================================================================
# INVENTORY ITEM SERIALIZERS
# ============================================================================

class InventoryItemListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.category_name', read_only=True, default='')
    unit_name = serializers.CharField(source='unit.unit_name', read_only=True, default='')
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True, default='')

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'item_code', 'item_name', 'category', 'category_name',
            'sub_category', 'unit', 'unit_name', 'brand', 'brand_name',
            'description', 'image_url', 'status', 'tags',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InventoryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.category_name', read_only=True, default='')
    unit_name = serializers.CharField(source='unit.unit_name', read_only=True, default='')
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True, default='')

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'item_code', 'item_name', 'category', 'category_name',
            'sub_category', 'unit', 'unit_name', 'brand', 'brand_name',
            'description', 'image_url', 'status', 'custom_fields', 'tags',
            'imported_from', 'cloned_from',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'cloned_from']

    def validate(self, data):
        """Ensure item_code is unique per tenant."""
        tenant_id = self.context['request'].user.organization_id
        item_code = data.get('item_code')
        instance = self.instance

        if item_code:
            qs = InventoryItem.objects.filter(
                tenant_id=tenant_id,
                item_code=item_code
            )
            if instance:
                qs = qs.exclude(id=instance.id)
            if qs.exists():
                raise serializers.ValidationError({
                    'item_code': f"Item code '{item_code}' already exists."
                })

        return data


class CustomFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomFieldDefinition
        fields = [
            'id', 'field_name', 'field_label', 'field_type',
            'options', 'is_required', 'order', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# STOCK SERIALIZERS
# ============================================================================

class StockLedgerSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source='item.item_code', read_only=True)
    item_name = serializers.CharField(source='item.item_name', read_only=True)
    location_name = serializers.CharField(
        source='location.location_name', read_only=True, default=''
    )

    class Meta:
        model = StockLedger
        fields = [
            'id', 'item', 'item_code', 'item_name',
            'location', 'location_name',
            'transaction_type', 'quantity',
            'unit_cost', 'total_cost',
            'reference_type', 'reference_id',
            'description', 'created_by', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CreateLedgerEntrySerializer(serializers.Serializer):
    item_id = serializers.UUIDField()
    location_id = serializers.UUIDField(required=False, allow_null=True)
    transaction_type = serializers.ChoiceField(choices=StockLedger.TRANSACTION_TYPES)
    quantity = serializers.DecimalField(max_digits=20, decimal_places=4)
    unit_cost = serializers.DecimalField(
        max_digits=20, decimal_places=4, required=False, allow_null=True
    )
    reference_type = serializers.CharField(required=False, allow_blank=True)
    reference_id = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)


class StockAvailabilitySerializer(serializers.Serializer):
    """Read-only serializer for stock availability data."""
    item_id = serializers.UUIDField()
    item_code = serializers.CharField()
    item_name = serializers.CharField()
    category_name = serializers.CharField(default='')
    brand_name = serializers.CharField(default='')
    unit_name = serializers.CharField(default='')
    physical = serializers.DecimalField(max_digits=20, decimal_places=4)
    reserved = serializers.DecimalField(max_digits=20, decimal_places=4)
    available = serializers.DecimalField(max_digits=20, decimal_places=4)
    in_transit = serializers.DecimalField(max_digits=20, decimal_places=4)
    damaged = serializers.DecimalField(max_digits=20, decimal_places=4)
    cost_price = serializers.DecimalField(
        max_digits=20, decimal_places=4, allow_null=True
    )
    selling_price = serializers.DecimalField(
        max_digits=20, decimal_places=4, allow_null=True
    )
    cost_value = serializers.DecimalField(max_digits=20, decimal_places=4)
    selling_value = serializers.DecimalField(max_digits=20, decimal_places=4)
    min_stock_level = serializers.DecimalField(
        max_digits=20, decimal_places=4, allow_null=True
    )
    reorder_level = serializers.DecimalField(
        max_digits=20, decimal_places=4, allow_null=True
    )
    max_stock_level = serializers.DecimalField(
        max_digits=20, decimal_places=4, allow_null=True
    )


class LowStockSerializer(serializers.Serializer):
    item_id = serializers.UUIDField()
    item_code = serializers.CharField()
    item_name = serializers.CharField()
    current_stock = serializers.DecimalField(max_digits=20, decimal_places=4)
    min_stock_level = serializers.DecimalField(max_digits=20, decimal_places=4)
    reorder_level = serializers.DecimalField(
        max_digits=20, decimal_places=4, allow_null=True
    )
    suggested_purchase = serializers.DecimalField(max_digits=20, decimal_places=4)


class InventoryValuationSerializer(serializers.Serializer):
    items = serializers.ListField()
    summary = serializers.DictField()


# ============================================================================
# TRANSFER SERIALIZERS
# ============================================================================

class TransferItemSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source='item.item_code', read_only=True)
    item_name = serializers.CharField(source='item.item_name', read_only=True)

    class Meta:
        model = InventoryTransferItem
        fields = [
            'id', 'item', 'item_code', 'item_name',
            'quantity', 'received_quantity', 'damaged_quantity', 'remarks',
        ]
        read_only_fields = ['id']


class TransferAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryTransferAttachment
        fields = ['id', 'file_url', 'file_name', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class TransferListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    source_name = serializers.CharField(
        source='source_location.location_name', read_only=True
    )
    destination_name = serializers.CharField(
        source='destination_location.location_name', read_only=True
    )
    item_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryTransfer
        fields = [
            'id', 'transfer_number', 'transfer_date',
            'source_location', 'source_name',
            'destination_location', 'destination_name',
            'transfer_type', 'status',
            'item_count', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_item_count(self, obj):
        return obj.items.count()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return ''


class TransferDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested items."""
    items = TransferItemSerializer(many=True, read_only=True)
    attachments = TransferAttachmentSerializer(many=True, read_only=True)
    source_name = serializers.CharField(
        source='source_location.location_name', read_only=True
    )
    destination_name = serializers.CharField(
        source='destination_location.location_name', read_only=True
    )
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    received_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryTransfer
        fields = [
            'id', 'tenant_id', 'transfer_number', 'transfer_date',
            'source_location', 'source_name',
            'destination_location', 'destination_name',
            'transfer_type', 'status',
            'approved_by', 'approved_by_name', 'approved_at', 'approval_notes',
            'dispatched_at', 'received_at', 'received_by', 'received_by_name',
            'remarks',
            'items', 'attachments',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'tenant_id', 'transfer_number', 'status',
            'approved_at', 'dispatched_at', 'received_at',
            'created_at', 'updated_at',
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return ''

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.email
        return ''

    def get_received_by_name(self, obj):
        if obj.received_by:
            return obj.received_by.get_full_name() or obj.received_by.email
        return ''


class CreateTransferSerializer(serializers.Serializer):
    """Serializer for creating a transfer."""
    transfer_date = serializers.DateField(required=False)
    source_location = serializers.UUIDField()
    destination_location = serializers.UUIDField()
    transfer_type = serializers.ChoiceField(
        choices=InventoryTransfer.TRANSFER_TYPES, default='STANDARD'
    )
    remarks = serializers.CharField(required=False, allow_blank=True)
    items = serializers.ListField(min_length=1)

    def validate_items(self, items):
        for item in items:
            if 'item_id' not in item:
                raise serializers.ValidationError("Each item must have 'item_id'.")
            if 'quantity' not in item:
                raise serializers.ValidationError("Each item must have 'quantity'.")
            if float(item['quantity']) <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0.")
        return items

    def validate(self, data):
        if data['source_location'] == data['destination_location']:
            raise serializers.ValidationError(
                "Source and destination must be different."
            )
        return data


class ReceiveTransferSerializer(serializers.Serializer):
    """Serializer for receiving a transfer with optional partial receipt."""
    items = serializers.ListField(required=False)

    def validate_items(self, items):
        if not items:
            return items
        for item in items:
            if 'item_id' not in item:
                raise serializers.ValidationError("Each item must have 'item_id'.")
            received = item.get('received_quantity', 0)
            damaged = item.get('damaged_quantity', 0)
            if float(received) < 0 or float(damaged) < 0:
                raise serializers.ValidationError("Quantities cannot be negative.")
        return items


# ============================================================================
# BULK IMPORT SERIALIZER
# ============================================================================

class BulkImportSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )

    def validate_items(self, items):
        errors = []
        validated = []

        for idx, item in enumerate(items):
            item_errors = {}

            item_code = item.get('item_code', '').strip()
            item_name = item.get('item_name', '').strip()

            if not item_code:
                item_errors['item_code'] = 'Item code is required.'
            if not item_name:
                item_errors['item_name'] = 'Item name is required.'

            if item_errors:
                errors.append({'index': idx, 'errors': item_errors})
            else:
                validated.append(item)

        if errors:
            raise serializers.ValidationError({
                'validation_errors': errors,
                'valid_count': len(validated),
                'error_count': len(errors),
            })

        return validated


# ============================================================================
# LOCATION TYPE SERIALIZERS
# ============================================================================

class LocationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryLocationType
        fields = [
            'id', 'type_code', 'type_name', 'description', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        tenant_id = self.context['request'].user.organization_id
        type_code = data.get('type_code')
        instance = self.instance

        if type_code:
            qs = InventoryLocationType.objects.filter(
                tenant_id=tenant_id,
                type_code=type_code
            )
            if instance:
                qs = qs.exclude(id=instance.id)
            if qs.exists():
                raise serializers.ValidationError({
                    'type_code': f"Type code '{type_code}' already exists."
                })
        return data


class LocationTypeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdown/reference data."""
    class Meta:
        model = InventoryLocationType
        fields = ['id', 'type_code', 'type_name', 'status']


# ============================================================================
# LOCATION SERIALIZERS
# ============================================================================

class LocationTreeSerializer(serializers.ModelSerializer):
    """Nested serializer for tree view."""
    children = serializers.SerializerMethodField()
    location_type_name = serializers.CharField(
        source='location_type.type_name', read_only=True, default=''
    )
    parent_name = serializers.CharField(
        source='parent_location.location_name', read_only=True, default=''
    )
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryLocation
        fields = [
            'id', 'location_code', 'location_name', 'location_type',
            'location_type_name', 'parent_location', 'parent_name',
            'city', 'state', 'country', 'status',
            'manager', 'manager_name',
            'children', 'created_at', 'updated_at',
        ]

    def get_children(self, obj):
        qs = obj.child_locations.all()
        filters = self.context.get('filters', {})
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])
        return LocationTreeSerializer(qs, many=True, context=self.context).data

    def get_manager_name(self, obj):
        if obj.manager:
            return obj.manager.get_full_name() or obj.manager.email
        return ''


class LocationSerializer(serializers.ModelSerializer):
    location_type_name = serializers.CharField(
        source='location_type.type_name', read_only=True, default=''
    )
    parent_name = serializers.CharField(
        source='parent_location.location_name', read_only=True, default=''
    )
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryLocation
        fields = [
            'id', 'location_code', 'location_name',
            'location_type', 'location_type_name',
            'parent_location', 'parent_name',
            'address', 'city', 'state', 'country', 'postal_code',
            'phone', 'email', 'contact_person', 'mobile',
            'manager', 'manager_name',
            'status',
            'max_capacity', 'capacity_unit',
            'allow_reservations', 'allow_transfers',
            'allow_sales', 'allow_purchases', 'allow_audits',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_manager_name(self, obj):
        if obj.manager:
            return obj.manager.get_full_name() or obj.manager.email
        return ''

    def validate(self, data):
        tenant_id = self.context['request'].user.organization_id
        location_code = data.get('location_code')
        instance = self.instance

        if location_code:
            qs = InventoryLocation.objects.filter(
                tenant_id=tenant_id,
                location_code=location_code
            )
            if instance:
                qs = qs.exclude(id=instance.id)
            if qs.exists():
                raise serializers.ValidationError({
                    'location_code': f"Location code '{location_code}' already exists."
                })
        return data


class LocationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/dropdown."""
    location_type_name = serializers.CharField(
        source='location_type.type_name', read_only=True, default=''
    )
    parent_name = serializers.CharField(
        source='parent_location.location_name', read_only=True, default=''
    )

    class Meta:
        model = InventoryLocation
        fields = [
            'id', 'location_code', 'location_name',
            'location_type', 'location_type_name',
            'parent_location', 'parent_name',
            'city', 'state', 'country', 'status',
        ]
