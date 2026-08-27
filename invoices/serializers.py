from decimal import Decimal
from rest_framework import serializers
from invoices.models import Invoice, InvoiceLineItem, InvoiceSchema, InvoiceStatusLog, CompanyProfile
from invoices.services.gst_calculator import calculate_line_item_gst, calculate_invoice_totals
from authentication.serializers import UserSerializer


# ---------------------------------------------------------------------------
# InvoiceSchema
# ---------------------------------------------------------------------------

class InvoiceSchemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceSchema
        fields = [
            'id', 'domain', 'label', 'prefix',
            'extra_fields', 'pdf_template', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ---------------------------------------------------------------------------
# InvoiceLineItem
# ---------------------------------------------------------------------------

class InvoiceLineItemReadSerializer(serializers.ModelSerializer):
    gst_rate_display = serializers.CharField(source='get_gst_rate_display', read_only=True)

    class Meta:
        model = InvoiceLineItem
        fields = [
            'id', 'description', 'hsn_sac_code', 'quantity', 'unit_price', 'amount',
            'gst_rate', 'gst_rate_display',
            'cgst_amount', 'sgst_amount', 'igst_amount', 'line_total',
            'order',
        ]


class InvoiceLineItemWriteSerializer(serializers.Serializer):
    """Flat write serializer — GST fields are computed, not accepted from client."""
    description = serializers.CharField(max_length=500)
    hsn_sac_code = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    gst_rate = serializers.ChoiceField(choices=[0, 5, 12, 18, 28], default=18)
    order = serializers.IntegerField(required=False, default=0)


# ---------------------------------------------------------------------------
# InvoiceStatusLog
# ---------------------------------------------------------------------------

class InvoiceStatusLogSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = InvoiceStatusLog
        fields = ['id', 'from_status', 'to_status', 'actor', 'note', 'created_at']
        read_only_fields = ['id', 'created_at']


# ---------------------------------------------------------------------------
# Invoice — List (lightweight)
# ---------------------------------------------------------------------------

class InvoiceListSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    supply_type_display = serializers.CharField(source='get_supply_type_display', read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'domain',
            'client_name', 'client_email',
            'status', 'status_display',
            'supply_type', 'supply_type_display',
            'grand_total', 'currency',
            'due_date', 'created_by',
            'pdf_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'invoice_number', 'created_at', 'updated_at']

    def get_pdf_url(self, obj):
        if not obj.pdf_file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return obj.pdf_file.url


# ---------------------------------------------------------------------------
# Invoice — Detail (full with line items, GST, logs)
# ---------------------------------------------------------------------------

class InvoiceDetailSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)
    schema = InvoiceSchemaSerializer(read_only=True)
    line_items = InvoiceLineItemReadSerializer(many=True, read_only=True)
    status_logs = InvoiceStatusLogSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    supply_type_display = serializers.CharField(source='get_supply_type_display', read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'domain', 'schema',
            'supplier_name', 'supplier_gstin', 'supplier_address',
            'created_by',
            'client_name', 'client_email', 'client_address', 'client_gstin',
            'supply_type', 'supply_type_display', 'place_of_supply',
            'subtotal', 'discount_amount',
            'cgst_total', 'sgst_total', 'igst_total', 'total_tax', 'grand_total',
            'currency', 'extra_data',
            'status', 'status_display', 'notes', 'admin_remarks',
            'reviewed_by', 'reviewed_at',
            'pdf_url', 'due_date',
            'line_items', 'status_logs',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'invoice_number',
            'supplier_name', 'supplier_gstin', 'supplier_address',
            'subtotal', 'cgst_total', 'sgst_total', 'igst_total', 'total_tax', 'grand_total',
            'status', 'reviewed_by', 'reviewed_at',
            'created_at', 'updated_at',
        ]

    def get_pdf_url(self, obj):
        if not obj.pdf_file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return obj.pdf_file.url


# ---------------------------------------------------------------------------
# Invoice — Write (create / update with nested line items)
# ---------------------------------------------------------------------------

class InvoiceWriteSerializer(serializers.ModelSerializer):
    line_items = InvoiceLineItemWriteSerializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            'domain', 'schema',
            'client_name', 'client_email', 'client_address', 'client_gstin',
            'supply_type', 'place_of_supply',
            'discount_amount', 'currency',
            'extra_data', 'notes', 'due_date',
            'line_items',
        ]
        extra_kwargs = {
            'client_email':     {'required': False},
            'client_address':   {'required': False},
            'client_gstin':     {'required': False},
            'place_of_supply':  {'required': False},
            'discount_amount':  {'required': False},
            'extra_data':       {'required': False},
            'notes':            {'required': False},
            'due_date':         {'required': False},
        }

    def validate(self, data):
        # Resolve schema from domain
        domain = data.get('domain', '').strip()
        if not domain:
            raise serializers.ValidationError({'domain': 'Domain is required and cannot be blank.'})
        
        try:
            schema = InvoiceSchema.objects.get(domain=domain, is_active=True)
            data['schema'] = schema
        except InvoiceSchema.DoesNotExist:
            raise serializers.ValidationError({'domain': f'Invalid domain: {domain}. Schema not found or inactive.'})
        
        if not data.get('line_items'):
            raise serializers.ValidationError({'line_items': 'At least one line item is required.'})
        
        return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_line_items(self, invoice, line_items_data):
        """Compute GST for each line item and bulk-insert."""
        supply_type = invoice.supply_type
        to_create = []

        for idx, item in enumerate(line_items_data):
            quantity = Decimal(str(item['quantity']))
            unit_price = Decimal(str(item['unit_price']))
            amount = (quantity * unit_price).quantize(Decimal('0.01'))
            gst_rate = int(item['gst_rate'])

            gst = calculate_line_item_gst(amount, gst_rate, supply_type)

            to_create.append(InvoiceLineItem(
                invoice=invoice,
                description=item['description'],
                hsn_sac_code=item.get('hsn_sac_code', ''),
                quantity=quantity,
                unit_price=unit_price,
                amount=amount,
                gst_rate=gst_rate,
                cgst_amount=gst['cgst_amount'],
                sgst_amount=gst['sgst_amount'],
                igst_amount=gst['igst_amount'],
                line_total=gst['line_total'],
                order=item.get('order', idx),
            ))

        InvoiceLineItem.objects.bulk_create(to_create)

    def _refresh_totals(self, invoice):
        """Recalculate and save invoice-level totals from persisted line items."""
        items = list(invoice.line_items.values('amount', 'gst_rate'))
        totals = calculate_invoice_totals(items, invoice.supply_type, invoice.discount_amount)
        for field, value in totals.items():
            setattr(invoice, field, value)
        invoice.save(update_fields=list(totals.keys()))

    # ------------------------------------------------------------------
    # DRF hooks
    # ------------------------------------------------------------------

    def create(self, validated_data):
        from invoices.services.invoice_number import generate_invoice_number

        line_items_data = validated_data.pop('line_items')
        schema = validated_data['schema']

        # Generate invoice number atomically before inserting the row
        invoice_number = generate_invoice_number(schema)

        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            created_by=self.context['request'].user,
            **validated_data,
        )

        self._build_line_items(invoice, line_items_data)
        self._refresh_totals(invoice)

        return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if line_items_data is not None:
            instance.line_items.all().delete()
            self._build_line_items(instance, line_items_data)
            self._refresh_totals(instance)

        return instance


# ---------------------------------------------------------------------------
# Action serializers (submit / approve / reject)
# ---------------------------------------------------------------------------

class InvoiceSubmitSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class InvoiceApproveSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')


class InvoiceRejectSerializer(serializers.Serializer):
    admin_remarks = serializers.CharField(required=True, min_length=5)
    note = serializers.CharField(required=False, allow_blank=True, default='')


# ---------------------------------------------------------------------------
# CompanyProfile
# ---------------------------------------------------------------------------

class CompanyProfileSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    signature_url = serializers.SerializerMethodField()
    seal_url = serializers.SerializerMethodField()

    class Meta:
        model = CompanyProfile
        fields = [
            'id',
            'company_name', 'company_address', 'gstin', 'pan_number',
            'phone', 'email', 'website', 'state', 'state_code',
            'logo', 'logo_url',
            'digital_signature', 'signature_url',
            'company_seal', 'seal_url',
            'bank_name', 'bank_account', 'bank_ifsc', 'bank_branch',
            'updated_at', 'updated_by',
        ]
        read_only_fields = ['id', 'updated_at', 'updated_by']
        extra_kwargs = {
            'company_name':    {'required': False, 'allow_blank': True},
            'company_address': {'required': False, 'allow_blank': True},
            'gstin':           {'required': False, 'allow_blank': True},
            'state':           {'required': False, 'allow_blank': True},
            'state_code':      {'required': False, 'allow_blank': True},
            'logo':              {'required': False, 'write_only': True},
            'digital_signature': {'required': False, 'write_only': True},
            'company_seal':      {'required': False, 'write_only': True},
        }

    def _abs_url(self, field_file):
        if not field_file:
            return None
        try:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(field_file.url)
            return field_file.url
        except Exception:
            return None

    def get_logo_url(self, obj):
        return self._abs_url(obj.logo)

    def get_signature_url(self, obj):
        return self._abs_url(obj.digital_signature)

    def get_seal_url(self, obj):
        return self._abs_url(obj.company_seal)


class ImageUploadSerializer(serializers.Serializer):
    """Validates branding image uploads (PNG/JPG, ≤ 2 MB)."""
    image = serializers.ImageField(required=True)

    def validate_image(self, value):
        max_bytes = 2 * 1024 * 1024
        if value.size > max_bytes:
            raise serializers.ValidationError('Image must be 2 MB or smaller.')
        if value.content_type not in ('image/png', 'image/jpeg'):
            raise serializers.ValidationError('Only PNG and JPG images are allowed.')
        return value
