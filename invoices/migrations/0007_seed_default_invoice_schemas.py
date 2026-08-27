from django.db import migrations


def seed_default_schemas(apps, schema_editor):
    InvoiceSchema = apps.get_model('invoices', 'InvoiceSchema')
    InvoiceSchema.objects.get_or_create(
        domain='travel_agency',
        defaults={
            'label': 'Travel Agency',
            'prefix': 'TRV',
            'pdf_template': 'invoice/travel_agency.html',
            'is_active': True,
            'extra_fields': [
                {"key": "from_location", "label": "From", "type": "text", "required": True},
                {"key": "destination", "label": "Destination", "type": "text", "required": True},
                {"key": "travel_from", "label": "Travel Date (From)", "type": "date", "required": True},
                {"key": "travel_to", "label": "Travel Date (To)", "type": "date", "required": True},
                {"key": "nights", "label": "Nights", "type": "number", "required": True},
                {"key": "days", "label": "Days", "type": "number", "required": True},
                {"key": "adults", "label": "Adults", "type": "number", "required": True},
                {"key": "children", "label": "Children", "type": "number"},
                {"key": "package_type", "label": "Package Type", "type": "text", "required": True},
                {"key": "tour_cost", "label": "Tour Cost", "type": "number", "required": True},
                {"key": "payment_mode", "label": "Payment Mode", "type": "select", "required": True,
                 "options": ["Cash", "Cheque", "UPI", "Net Banking", "Card"]},
                {"key": "advance_amount", "label": "Advance Amount", "type": "number"},
                {"key": "balance_amount", "label": "Balance Amount", "type": "number"},
            ],
        },
    )


def remove_default_schemas(apps, schema_editor):
    InvoiceSchema = apps.get_model('invoices', 'InvoiceSchema')
    InvoiceSchema.objects.filter(domain='travel_agency').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0006_alter_invoice_created_by_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_default_schemas, remove_default_schemas),
    ]
