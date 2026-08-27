from django.contrib import admin, messages
from django.utils import timezone
from invoices.models import Invoice, InvoiceLineItem, InvoiceSchema, InvoiceStatusLog, CompanyProfile


def _log_transition(invoice, from_status, to_status, actor, note=''):
    InvoiceStatusLog.objects.create(
        invoice=invoice,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        note=note,
    )


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    readonly_fields = ['amount', 'cgst_amount', 'sgst_amount', 'igst_amount', 'line_total']


class InvoiceStatusLogInline(admin.TabularInline):
    model = InvoiceStatusLog
    extra = 0
    readonly_fields = ['from_status', 'to_status', 'actor', 'note', 'created_at']
    can_delete = False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'domain', 'client_name', 'status',
        'grand_total', 'currency', 'created_by', 'created_at',
    ]
    list_filter = ['status', 'domain', 'supply_type', 'currency']
    search_fields = ['invoice_number', 'client_name', 'client_email', 'client_gstin']
    ordering = ['-created_at']
    readonly_fields = [
        'invoice_number', 'status', 'subtotal', 'cgst_total', 'sgst_total',
        'igst_total', 'total_tax', 'grand_total',
        'reviewed_by', 'reviewed_at', 'created_at', 'updated_at',
    ]
    inlines = [InvoiceLineItemInline, InvoiceStatusLogInline]
    actions = ['action_approve_invoices', 'action_reject_invoices']

    @admin.action(description='Approve selected invoices (PENDING → APPROVED)')
    def action_approve_invoices(self, request, queryset):
        from invoices.services.pdf_generator import generate_invoice_pdf
        from invoices.services.notifications import notify_creator_on_approval

        pending = queryset.filter(status=Invoice.Status.PENDING)
        skipped = queryset.exclude(status=Invoice.Status.PENDING).count()
        profile = CompanyProfile.objects.first()
        approved_count = 0

        for invoice in pending:
            if profile:
                invoice.supplier_name = profile.company_name
                invoice.supplier_gstin = profile.gstin
                invoice.supplier_address = profile.company_address

            old_status = invoice.status
            invoice.status = Invoice.Status.APPROVED
            invoice.reviewed_by = request.user
            invoice.reviewed_at = timezone.now()
            invoice.save()

            _log_transition(invoice, old_status, Invoice.Status.APPROVED, request.user, 'Approved via admin')

            try:
                generate_invoice_pdf(invoice)
            except Exception:
                pass

            notify_creator_on_approval(invoice)
            approved_count += 1

        if approved_count:
            self.message_user(request, f'{approved_count} invoice(s) approved and PDF generated.', messages.SUCCESS)
        if skipped:
            self.message_user(request, f'{skipped} invoice(s) skipped — only PENDING invoices can be approved.', messages.WARNING)

    @admin.action(description='Reject selected invoices (PENDING → REJECTED)')
    def action_reject_invoices(self, request, queryset):
        from invoices.services.notifications import notify_creator_on_rejection

        pending = queryset.filter(status=Invoice.Status.PENDING)
        skipped = queryset.exclude(status=Invoice.Status.PENDING).count()
        rejected_count = 0

        for invoice in pending:
            old_status = invoice.status
            invoice.status = Invoice.Status.REJECTED
            invoice.reviewed_by = request.user
            invoice.reviewed_at = timezone.now()
            invoice.save()

            _log_transition(invoice, old_status, Invoice.Status.REJECTED, request.user, 'Rejected via admin')
            notify_creator_on_rejection(invoice)
            rejected_count += 1

        if rejected_count:
            self.message_user(request, f'{rejected_count} invoice(s) rejected.', messages.SUCCESS)
        if skipped:
            self.message_user(request, f'{skipped} invoice(s) skipped — only PENDING invoices can be rejected.', messages.WARNING)

    fieldsets = (
        ('Identity', {
            'fields': ('invoice_number', 'domain', 'schema', 'status'),
        }),
        ('Supplier Snapshot', {
            'fields': ('supplier_name', 'supplier_gstin', 'supplier_address'),
            'classes': ('collapse',),
        }),
        ('Client', {
            'fields': ('created_by', 'client_name', 'client_email', 'client_address', 'client_gstin'),
        }),
        ('GST', {
            'fields': ('supply_type', 'place_of_supply'),
        }),
        ('Financials', {
            'fields': (
                'subtotal', 'discount_amount',
                'cgst_total', 'sgst_total', 'igst_total', 'total_tax', 'grand_total',
                'currency',
            ),
        }),
        ('Domain Extra Data', {
            'fields': ('extra_data',),
            'classes': ('collapse',),
        }),
        ('Workflow', {
            'fields': ('notes', 'admin_remarks', 'reviewed_by', 'reviewed_at', 'pdf_file', 'due_date'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(InvoiceSchema)
class InvoiceSchemaAdmin(admin.ModelAdmin):
    list_display = ['domain', 'label', 'prefix', 'pdf_template', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['domain', 'label', 'prefix']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InvoiceStatusLog)
class InvoiceStatusLogAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'from_status', 'to_status', 'actor', 'created_at']
    list_filter = ['from_status', 'to_status']
    readonly_fields = ['invoice', 'from_status', 'to_status', 'actor', 'note', 'created_at']
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'gstin', 'state', 'updated_at']
    readonly_fields = ['updated_at', 'updated_by', 'created_at']

    fieldsets = (
        ('Company Info', {
            'fields': (
                'company_name', 'company_address', 'gstin', 'pan_number',
                'phone', 'email', 'website', 'state', 'state_code',
            ),
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'bank_account', 'bank_ifsc', 'bank_branch'),
            'classes': ('collapse',),
        }),
        ('Branding Assets', {
            'fields': ('logo', 'digital_signature', 'company_seal'),
            'description': (
                '⚠ Signature and seal are embedded in ALL approved invoices. '
                'Use transparent PNG (recommended 150×60 px for signature, 100×100 px for seal).'
            ),
        }),
        ('Metadata', {
            'fields': ('updated_at', 'updated_by', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        """Allow creating only if no profile exists yet."""
        return not CompanyProfile.objects.exists()
