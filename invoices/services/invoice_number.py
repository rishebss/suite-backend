"""
Invoice Number Generator
========================
Format:  {PREFIX}-{YEAR}-{SEQUENCE}
Example: TRV-2026-0001

Sequence is per-domain, per-calendar-year.
Wrapped in a transaction so concurrent requests get unique numbers.
"""
from django.db import transaction
from django.utils import timezone


def generate_invoice_number(schema) -> str:
    """
    Generate the next invoice number for the given InvoiceSchema.

    Must be called BEFORE the new Invoice row is inserted so the count
    reflects only previously committed invoices.
    """
    from invoices.models import Invoice

    current_year = timezone.now().year
    prefix = schema.prefix.upper()
    domain = schema.domain

    with transaction.atomic():
        # select_for_update prevents concurrent reads from grabbing the same count
        last_invoice = (
            Invoice.objects
            .select_for_update()
            .filter(domain=domain, created_at__year=current_year)
            .order_by('-created_at')
            .first()
        )

        if last_invoice and last_invoice.invoice_number:
            try:
                last_seq = int(last_invoice.invoice_number.rsplit('-', 1)[-1])
            except (ValueError, IndexError):
                last_seq = 0
            sequence = last_seq + 1
        else:
            sequence = 1

        return f"{prefix}-{current_year}-{sequence:04d}"
