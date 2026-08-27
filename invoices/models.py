from django.db import models
from django.conf import settings
from core.models import Main


class CompanyProfile(Main):
    """
    Single-record model holding company branding assets and details.
    Singleton: only one instance is ever allowed (enforced in save()).
    Admin-only: logo, digital_signature, company_seal are embedded in approved PDFs.
    """
    company_name = models.CharField(max_length=255, blank=True)
    company_address = models.TextField(blank=True)
    gstin = models.CharField(max_length=15, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    state = models.CharField(max_length=100, blank=True)
    state_code = models.CharField(max_length=50, blank=True)

    # Branding assets (admin-only upload; recommended: transparent PNG)
    logo = models.ImageField(upload_to='company/logo/', null=True, blank=True)
    digital_signature = models.ImageField(upload_to='company/signature/', null=True, blank=True)
    company_seal = models.ImageField(upload_to='company/seal/', null=True, blank=True)

    # Bank details
    bank_name = models.CharField(max_length=255, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    bank_ifsc = models.CharField(max_length=20, blank=True)
    bank_branch = models.CharField(max_length=255, blank=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='company_profile_updates',
    )

    class Meta:
        verbose_name = 'Company Profile'
        verbose_name_plural = 'Company Profile'

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        """Enforce singleton: only one CompanyProfile instance is allowed."""
        if not self.pk and CompanyProfile.objects.exists():
            raise ValueError(
                "Only one CompanyProfile is allowed. Update the existing record instead."
            )
        super().save(*args, **kwargs)


class InvoiceSchema(Main):
    """
    Domain-specific form configuration.
    Adding a new domain only requires a new InvoiceSchema record + an HTML template.
    No model, API, or React code changes needed.
    """
    domain = models.CharField(max_length=50, unique=True)   # e.g. 'travel_agency', 'ohrs'
    label = models.CharField(max_length=100)                 # e.g. 'Travel Agency'
    prefix = models.CharField(max_length=5)                  # invoice number prefix e.g. 'TRV'
    extra_fields = models.JSONField(default=list)            # list of field definitions
    pdf_template = models.CharField(
        max_length=100,
        default='invoice/base_invoice.html',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['domain']
        verbose_name = 'Invoice Schema'
        verbose_name_plural = 'Invoice Schemas'

    def __str__(self):
        return f"{self.label} ({self.domain})"


class Invoice(Main):
    """
    Core invoice model.
    Hybrid approach: fixed columns for financials/GST (fast queries) +
    extra_data JSONField for domain-specific fields.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        COMPLETED = 'completed', 'Completed'

    class SupplyType(models.TextChoices):
        INTRA = 'intra_state', 'Intra-State (CGST + SGST)'
        INTER = 'inter_state', 'Inter-State (IGST)'

    # Identity
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    domain = models.CharField(max_length=50)
    schema = models.ForeignKey(
        InvoiceSchema,
        on_delete=models.PROTECT,
        related_name='invoices',
    )

    # Supplier snapshot (populated from CompanyProfile at approval time)
    supplier_name = models.CharField(max_length=255, blank=True)
    supplier_gstin = models.CharField(max_length=15, blank=True)
    supplier_address = models.TextField(blank=True)

    # Client / Recipient
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='invoices',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField(blank=True)
    client_address = models.TextField(blank=True)
    client_gstin = models.CharField(max_length=15, blank=True)

    # GST
    supply_type = models.CharField(
        max_length=20,
        choices=SupplyType.choices,
        default=SupplyType.INTRA,
    )
    place_of_supply = models.CharField(max_length=100, blank=True)

    # Financials — computed and stored for fast querying / reporting
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='INR')

    # Domain-specific extra fields (injected by InvoiceSchema.extra_fields config)
    extra_data = models.JSONField(default=dict, blank=True)

    # Workflow
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)
    admin_remarks = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name='reviewed_invoices',
        on_delete=models.SET_NULL,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # PDF — generated on approval; stores snapshot with signature + seal embedded
    pdf_file = models.FileField(upload_to='invoices/pdf/', null=True, blank=True)

    # Dates
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        indexes = [
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['invoice_number']),
        ]

    def __str__(self):
        return f"{self.invoice_number} — {self.client_name}"


class InvoiceLineItem(Main):
    """
    One line item on an invoice.
    GST values (cgst_amount, sgst_amount, igst_amount) are computed at creation
    time and stored as a snapshot — they do not change if supply_type changes later.
    """

    GST_RATE_CHOICES = [
        (0, '0%'),
        (5, '5%'),
        (12, '12%'),
        (18, '18%'),
        (28, '28%'),
    ]

    invoice = models.ForeignKey(Invoice, related_name='line_items', on_delete=models.CASCADE)
    description = models.CharField(max_length=500)
    hsn_sac_code = models.CharField(max_length=20, blank=True)   # HSN (goods) / SAC (services)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)   # qty × unit_price

    # GST snapshot — computed at creation and frozen
    gst_rate = models.PositiveSmallIntegerField(choices=GST_RATE_CHOICES, default=18)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Invoice Line Item'
        verbose_name_plural = 'Invoice Line Items'

    def __str__(self):
        return f"{self.invoice.invoice_number} — {self.description}"


class InvoiceStatusLog(Main):
    """
    Immutable audit trail for every invoice status transition.
    Every DRAFT→PENDING, PENDING→APPROVED, etc. gets one record with actor + timestamp.
    """
    invoice = models.ForeignKey(Invoice, related_name='status_logs', on_delete=models.CASCADE)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice Status Log'
        verbose_name_plural = 'Invoice Status Logs'

    def __str__(self):
        return f"{self.invoice.invoice_number}: {self.from_status} → {self.to_status}"
