import uuid
from django.db import models
from core.models import Main


class ItemCategory(Main):
    """Hierarchical item categories — e.g. Electronics → Laptops"""

    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ARCHIVED', 'Archived'),
    )

    # Tenant isolation
    tenant_id = models.UUIDField(db_index=True, default=uuid.uuid4)

    category_code = models.CharField(max_length=100, db_index=True, default='')
    category_name = models.CharField(max_length=255, default='')
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children'
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='ACTIVE'
    )

    # Tracking & audit
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_categories'
    )
    updated_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_categories'
    )

    class Meta:
        ordering = ['category_name']
        verbose_name = 'Item Category'
        verbose_name_plural = 'Item Categories'
        unique_together = ('tenant_id', 'category_code')
        indexes = [
            models.Index(fields=['tenant_id', 'category_code']),
            models.Index(fields=['tenant_id', 'category_name']),
            models.Index(fields=['tenant_id', 'parent']),
            models.Index(fields=['tenant_id', 'status']),
        ]

    def __str__(self):
        return f"{self.category_code} — {self.category_name}"


class Unit(Main):
    """Units of measurement — e.g. Piece, Kg, Meter, Liter, Box"""

    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ARCHIVED', 'Archived'),
    )

    # Tenant isolation
    tenant_id = models.UUIDField(db_index=True, default=uuid.uuid4)

    unit_code = models.CharField(max_length=100, db_index=True, default='')
    unit_name = models.CharField(max_length=255, default='')
    symbol = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='ACTIVE'
    )

    class Meta:
        ordering = ['unit_name']
        verbose_name = 'Unit'
        verbose_name_plural = 'Units'
        unique_together = ('tenant_id', 'unit_code')
        indexes = [
            models.Index(fields=['tenant_id', 'unit_code']),
            models.Index(fields=['tenant_id', 'unit_name']),
            models.Index(fields=['tenant_id', 'status']),
        ]

    def __str__(self):
        return f"{self.unit_code} — {self.unit_name}"


class UnitConversion(Main):
    """Conversion relationships between units — e.g. 1 Box = 12 Pieces"""

    # Tenant isolation
    tenant_id = models.UUIDField(db_index=True)

    from_unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='conversions_from'
    )
    to_unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='conversions_to'
    )
    conversion_factor = models.DecimalField(max_digits=20, decimal_places=6)

    class Meta:
        ordering = ['from_unit', 'to_unit']
        verbose_name = 'Unit Conversion'
        verbose_name_plural = 'Unit Conversions'
        unique_together = ('tenant_id', 'from_unit', 'to_unit')
        indexes = [
            models.Index(fields=['tenant_id', 'from_unit']),
            models.Index(fields=['tenant_id', 'to_unit']),
        ]

    def __str__(self):
        return f"1 {self.from_unit.unit_name} = {self.conversion_factor} {self.to_unit.unit_name}"


class Brand(Main):
    """Brand or manufacturer of items — e.g. Apple, Samsung, Dell"""

    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ARCHIVED', 'Archived'),
    )

    # Tenant isolation
    tenant_id = models.UUIDField(db_index=True, default=uuid.uuid4)

    brand_code = models.CharField(max_length=100, db_index=True, default='')
    brand_name = models.CharField(max_length=255, default='')
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True, max_length=2000)
    website = models.URLField(blank=True, max_length=2000)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='ACTIVE'
    )

    # Tracking & audit
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_brands'
    )
    updated_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_brands'
    )

    class Meta:
        ordering = ['brand_name']
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        unique_together = ('tenant_id', 'brand_code')
        indexes = [
            models.Index(fields=['tenant_id', 'brand_code']),
            models.Index(fields=['tenant_id', 'brand_name']),
            models.Index(fields=['tenant_id', 'status']),
        ]

    def __str__(self):
        return f"{self.brand_code} — {self.brand_name}"


class InventoryItem(Main):
    """Central item master — every stockable/service item lives here."""

    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ARCHIVED', 'Archived'),
    )

    # Tenant isolation
    tenant_id = models.UUIDField(db_index=True)

    item_code = models.CharField(max_length=100, db_index=True)
    item_name = models.CharField(max_length=500)
    category = models.ForeignKey(
        ItemCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='items'
    )
    sub_category = models.CharField(max_length=255, blank=True)
    unit = models.ForeignKey(
        Unit, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='items'
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='items'
    )
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True, max_length=2000)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='ACTIVE'
    )
    custom_fields = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)

    # Tracking & audit
    imported_from = models.CharField(max_length=255, blank=True,
                                       help_text="Source of import (e.g. Excel file name)")
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_inventory_items'
    )
    updated_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_inventory_items'
    )

    # Cloned-from reference
    cloned_from = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='clones'
    )

    # Stock management fields
    min_stock_level = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True,
        help_text='Minimum stock before low-stock alert'
    )
    reorder_level = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True,
        help_text='Stock level at which to reorder'
    )
    max_stock_level = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True,
        help_text='Maximum desired stock level'
    )
    cost_price = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True,
        help_text='Unit cost price for valuation'
    )
    selling_price = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True,
        help_text='Unit selling price'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
        unique_together = ('tenant_id', 'item_code')
        indexes = [
            models.Index(fields=['tenant_id', 'item_code']),
            models.Index(fields=['tenant_id', 'item_name']),
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'category']),
            models.Index(fields=['tenant_id', 'brand']),
        ]

    def __str__(self):
        return f"{self.item_code} — {self.item_name}"


class CustomFieldDefinition(Main):
    """Dynamic custom field schema per organization/tenant.

    Travel Client may need Destination, Hotel Name, Tour Duration.
    Retail Client may need Color, Size, Warranty.
    No code changes required — admins configure these via the UI.
    """
    FIELD_TYPE_CHOICES = (
        ('TEXT', 'Text'),
        ('NUMBER', 'Number'),
        ('DATE', 'Date'),
        ('BOOLEAN', 'Boolean'),
        ('SELECT', 'Select'),
        ('MULTI_SELECT', 'Multi Select'),
    )

    field_name = models.CharField(max_length=255)
    field_label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='TEXT')
    options = models.JSONField(default=list, blank=True,
                                help_text="For SELECT/MULTI_SELECT types")
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'field_name']
        verbose_name = 'Custom Field Definition'
        verbose_name_plural = 'Custom Field Definitions'

    def __str__(self):
        return f"{self.field_label} ({self.get_field_type_display()})"


class InventoryLocationType(Main):
    """Configurable location types — Warehouse, Branch, Store, Office, Depot, etc.
    Clients can create custom types without code changes.
    """

    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    )

    tenant_id = models.UUIDField(db_index=True)
    type_code = models.CharField(max_length=50, db_index=True)
    type_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='ACTIVE'
    )

    class Meta:
        ordering = ['type_name']
        verbose_name = 'Location Type'
        verbose_name_plural = 'Location Types'
        unique_together = ('tenant_id', 'type_code')
        indexes = [
            models.Index(fields=['tenant_id', 'type_code']),
            models.Index(fields=['tenant_id', 'type_name']),
            models.Index(fields=['tenant_id', 'status']),
        ]

    def __str__(self):
        return f"{self.type_code} — {self.type_name}"


class InventoryLocation(Main):
    """Locations define where inventory exists — warehouse, branch, store, office, etc.
    Supports hierarchy: India HQ → Bangalore Branch → Section A.
    Stock quantities are NOT stored here — use Stock Ledger (Section 4).
    """

    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ARCHIVED', 'Archived'),
    )

    # Tenant isolation
    tenant_id = models.UUIDField(db_index=True)

    # Core identification
    location_code = models.CharField(max_length=100, db_index=True)
    location_name = models.CharField(max_length=500)
    location_type = models.ForeignKey(
        InventoryLocationType, on_delete=models.PROTECT,
        related_name='locations'
    )
    parent_location = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='child_locations'
    )

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Contact
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    mobile = models.CharField(max_length=50, blank=True)

    # Manager assignment
    manager = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_locations'
    )

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='ACTIVE'
    )

    # Capacity (optional)
    max_capacity = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True,
        help_text='Maximum storage capacity'
    )
    capacity_unit = models.CharField(
        max_length=50, blank=True,
        help_text='e.g. PCS, KG, Seats'
    )

    # Location settings (configurable toggles)
    allow_reservations = models.BooleanField(default=True)
    allow_transfers = models.BooleanField(default=True)
    allow_sales = models.BooleanField(default=True)
    allow_purchases = models.BooleanField(default=True)
    allow_audits = models.BooleanField(default=True)

    # Tracking & audit
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_locations'
    )
    updated_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='updated_locations'
    )

    class Meta:
        ordering = ['location_name']
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        unique_together = ('tenant_id', 'location_code')
        indexes = [
            models.Index(fields=['tenant_id', 'location_code']),
            models.Index(fields=['tenant_id', 'location_name']),
            models.Index(fields=['tenant_id', 'location_type']),
            models.Index(fields=['tenant_id', 'parent_location']),
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'city']),
        ]

    def __str__(self):
        return f"{self.location_code} — {self.location_name}"


class InventoryTransfer(Main):
    """Stock transfer between locations with full workflow."""

    TRANSFER_TYPES = (
        ('STANDARD', 'Standard Transfer'),
        ('EMERGENCY', 'Emergency Transfer'),
        ('RETURN', 'Return Transfer'),
        ('DAMAGED', 'Damaged Stock Transfer'),
    )

    TRANSFER_STATUSES = (
        ('DRAFT', 'Draft'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('IN_TRANSIT', 'In Transit'),
        ('RECEIVED', 'Received'),
        ('PARTIALLY_RECEIVED', 'Partially Received'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    tenant_id = models.UUIDField(db_index=True)
    transfer_number = models.CharField(max_length=100, db_index=True)
    transfer_date = models.DateField()

    source_location = models.ForeignKey(
        InventoryLocation, on_delete=models.PROTECT,
        related_name='transfers_from'
    )
    destination_location = models.ForeignKey(
        InventoryLocation, on_delete=models.PROTECT,
        related_name='transfers_to'
    )

    transfer_type = models.CharField(
        max_length=30, choices=TRANSFER_TYPES, default='STANDARD'
    )
    status = models.CharField(
        max_length=30, choices=TRANSFER_STATUSES, default='DRAFT'
    )

    # Approval
    approved_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_transfers'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)

    # Dispatch / Receipt
    dispatched_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='received_transfers'
    )

    remarks = models.TextField(blank=True)

    # Tracking
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_transfers'
    )
    updated_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='updated_transfers'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Transfer'
        verbose_name_plural = 'Stock Transfers'
        unique_together = ('tenant_id', 'transfer_number')
        indexes = [
            models.Index(fields=['tenant_id', 'transfer_number']),
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'source_location']),
            models.Index(fields=['tenant_id', 'destination_location']),
            models.Index(fields=['tenant_id', 'transfer_date']),
        ]

    def __str__(self):
        return f"{self.transfer_number} ({self.get_status_display()})"


class InventoryTransferItem(Main):
    """Line items for a stock transfer."""

    transfer = models.ForeignKey(
        InventoryTransfer, on_delete=models.CASCADE,
        related_name='items'
    )
    item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE,
        related_name='transfer_items'
    )
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    received_quantity = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True
    )
    damaged_quantity = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True
    )
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Transfer Line Item'
        verbose_name_plural = 'Transfer Line Items'

    def __str__(self):
        return f"{self.item.item_code} x {self.quantity}"


class InventoryTransferAttachment(Main):
    """Files attached to a transfer (delivery notes, receipts, etc.)."""

    transfer = models.ForeignKey(
        InventoryTransfer, on_delete=models.CASCADE,
        related_name='attachments'
    )
    file_url = models.URLField(max_length=2000, blank=True)
    file_name = models.CharField(max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Transfer Attachment'
        verbose_name_plural = 'Transfer Attachments'

    def __str__(self):
        return self.file_name


class StockLedger(Main):
    """Stock Ledger — the single source of truth for all inventory quantities.

    NEVER store quantities directly. Every stock movement creates a ledger entry.
    Current stock is calculated by summing all ledger entries for an item+location.
    """

    TRANSACTION_TYPES = (
        ('OPENING', 'Opening Balance'),
        ('PURCHASE', 'Purchase'),
        ('SALE', 'Sale'),
        ('TRANSFER_IN', 'Transfer In'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('RETURN', 'Return'),
        ('DAMAGE', 'Damage'),
        ('LOST', 'Lost'),
        ('EXPIRED', 'Expired'),
        ('CONSUMPTION', 'Consumption'),
        ('ADJUSTMENT', 'Adjustment'),
        ('RESERVATION', 'Reservation'),
        ('RESERVATION_RELEASE', 'Reservation Release'),
    )

    tenant_id = models.UUIDField(db_index=True)

    item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE,
        related_name='stock_ledger_entries'
    )
    location = models.ForeignKey(
        InventoryLocation, on_delete=models.CASCADE,
        related_name='stock_ledger_entries',
        null=True, blank=True
    )

    transaction_type = models.CharField(
        max_length=30, choices=TRANSACTION_TYPES
    )
    quantity = models.DecimalField(
        max_digits=20, decimal_places=4,
        help_text='Positive = in, Negative = out'
    )

    # Unit cost/total cost for valuation
    unit_cost = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True
    )
    total_cost = models.DecimalField(
        max_digits=20, decimal_places=4,
        null=True, blank=True
    )

    # Polymorphic reference to source document
    reference_type = models.CharField(
        max_length=50, blank=True,
        help_text='e.g. PURCHASE_ORDER, SALES_ORDER, TRANSFER'
    )
    reference_id = models.CharField(
        max_length=100, blank=True,
        help_text='ID of the source document'
    )

    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_ledger_entries'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Ledger Entry'
        verbose_name_plural = 'Stock Ledger Entries'
        indexes = [
            models.Index(fields=['tenant_id', 'item', 'location']),
            models.Index(fields=['tenant_id', 'item']),
            models.Index(fields=['tenant_id', 'location']),
            models.Index(fields=['tenant_id', 'transaction_type']),
            models.Index(fields=['tenant_id', 'created_at']),
        ]

    def __str__(self):
        return f"{self.item.item_code} @ {self.location} = {self.quantity} ({self.transaction_type})"


class StockSummary(Main):
    """Cached stock summary for fast lookups.
    Updated automatically when ledger entries are created.
    Never update this directly — always use the ledger.
    """

    tenant_id = models.UUIDField(db_index=True)

    item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE,
        related_name='stock_summaries'
    )
    location = models.ForeignKey(
        InventoryLocation, on_delete=models.CASCADE,
        related_name='stock_summaries',
        null=True, blank=True
    )

    physical_quantity = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )
    reserved_quantity = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )
    in_transit_quantity = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )
    damaged_quantity = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )

    class Meta:
        verbose_name = 'Stock Summary'
        verbose_name_plural = 'Stock Summaries'
        unique_together = ('tenant_id', 'item', 'location')
        indexes = [
            models.Index(fields=['tenant_id', 'item']),
            models.Index(fields=['tenant_id', 'location']),
            models.Index(fields=['tenant_id', 'physical_quantity']),
        ]

    def __str__(self):
        return f"{self.item.item_code} @ {self.location}: {self.physical_quantity}"

    @property
    def available_quantity(self):
        """Available = Physical - Reserved"""
        return self.physical_quantity - self.reserved_quantity
