from django.db import migrations


def set_travel_agency_template(apps, schema_editor):
    InvoiceSchema = apps.get_model('invoices', 'InvoiceSchema')
    InvoiceSchema.objects.filter(domain='travel_agency').update(
        pdf_template='invoice/travel_agency.html'
    )


def revert_travel_agency_template(apps, schema_editor):
    InvoiceSchema = apps.get_model('invoices', 'InvoiceSchema')
    InvoiceSchema.objects.filter(domain='travel_agency').update(
        pdf_template='invoice/base_invoice.html'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(set_travel_agency_template, revert_travel_agency_template),
    ]
