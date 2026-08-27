from django.contrib import admin
from inventory.models import (
    ItemCategory, Unit, UnitConversion, Brand, InventoryItem,
    CustomFieldDefinition, InventoryLocationType, InventoryLocation,
    StockLedger, StockSummary,
    InventoryTransfer, InventoryTransferItem, InventoryTransferAttachment,
)


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ['category_code', 'category_name', 'parent', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['category_code', 'category_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['unit_code', 'unit_name', 'symbol', 'status']
    list_filter = ['status']
    search_fields = ['unit_code', 'unit_name', 'symbol']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    list_display = ['from_unit', 'to_unit', 'conversion_factor']
    list_filter = ['from_unit', 'to_unit']
    search_fields = ['from_unit__unit_name', 'to_unit__unit_name']


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['brand_code', 'brand_name', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['brand_code', 'brand_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = [
        'item_code', 'item_name', 'category', 'unit',
        'brand', 'status', 'created_at'
    ]
    list_filter = ['status', 'category', 'brand']
    search_fields = ['item_code', 'item_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['category', 'unit', 'brand']


@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ['field_name', 'field_label', 'field_type', 'is_required', 'is_active', 'order']
    list_filter = ['field_type', 'is_required', 'is_active']
    search_fields = ['field_name', 'field_label']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InventoryLocationType)
class InventoryLocationTypeAdmin(admin.ModelAdmin):
    list_display = ['type_code', 'type_name', 'status']
    list_filter = ['status']
    search_fields = ['type_code', 'type_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InventoryLocation)
class InventoryLocationAdmin(admin.ModelAdmin):
    list_display = [
        'location_code', 'location_name', 'location_type',
        'parent_location', 'city', 'status', 'created_at'
    ]
    list_filter = ['status', 'location_type', 'country']
    search_fields = ['location_code', 'location_name', 'city', 'state']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['location_type', 'parent_location']


@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = ['item', 'location', 'transaction_type', 'quantity', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['item__item_code', 'item__item_name', 'description']
    readonly_fields = ['created_at']
    list_select_related = ['item', 'location']


@admin.register(StockSummary)
class StockSummaryAdmin(admin.ModelAdmin):
    list_display = ['item', 'location', 'physical_quantity', 'reserved_quantity', 'available_quantity']
    list_filter = ['location']
    search_fields = ['item__item_code', 'item__item_name']
    list_select_related = ['item', 'location']


@admin.register(InventoryTransfer)
class InventoryTransferAdmin(admin.ModelAdmin):
    list_display = [
        'transfer_number', 'transfer_date', 'source_location',
        'destination_location', 'transfer_type', 'status', 'created_at'
    ]
    list_filter = ['status', 'transfer_type']
    search_fields = ['transfer_number', 'remarks']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['source_location', 'destination_location']


@admin.register(InventoryTransferItem)
class InventoryTransferItemAdmin(admin.ModelAdmin):
    list_display = ['transfer', 'item', 'quantity', 'received_quantity', 'damaged_quantity']
    list_filter = ['transfer']
    search_fields = ['item__item_code', 'item__item_name']
    list_select_related = ['transfer', 'item']


@admin.register(InventoryTransferAttachment)
class InventoryTransferAttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'transfer', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['file_name']
