"""
PDF Generation Service
======================
Renders an approved invoice to PDF using xhtml2pdf.
Images (logo, signature, seal) are embedded as base64 data URLs so this works
with both local-filesystem storage and remote object storage (S3/Leapcell).

Uses xhtml2pdf for better compatibility on Linux/Leapcell environments without
requiring system-level GTK/Cairo/Pango binary dependencies.
"""
import base64
import logging
from io import BytesIO
from django.template.loader import render_to_string
from django.core.files.base import ContentFile

def _to_data_url(field_file):
    """Read an ImageField from any storage backend and return a base64 data URL."""
    if not field_file:
        return None
    try:
        with field_file.open('rb') as fh:
            data = fh.read()
        mime = 'image/jpeg' if data[:2] == b'\xff\xd8' else 'image/png'
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    except Exception:
        return None

def _build_pdf_bytes(invoice) -> bytes:
    """Render invoice to PDF bytes without touching any file storage."""
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise ImportError(
            "xhtml2pdf is required for PDF generation. "
            "Install it with: pip install xhtml2pdf"
        )

    try:
        from num2words import num2words
        amount_in_words = (
            num2words(float(invoice.grand_total), lang='en_IN', to='currency').title()
            + " Only"
        )
    except Exception:
        amount_in_words = f"INR {invoice.grand_total}"

    profile = None
    try:
        from invoices.models import CompanyProfile
        profile = CompanyProfile.objects.first()
    except Exception:
        pass

    template_name = invoice.schema.pdf_template

    context = {
        'invoice': invoice,
        'profile': profile,
        'line_items': invoice.line_items.all().order_by('order'),
        'logo_path': _to_data_url(profile.logo) if profile else None,
        'sig_path': _to_data_url(profile.digital_signature) if profile else None,
        'seal_path': _to_data_url(profile.company_seal) if profile else None,
        'amount_in_words': amount_in_words,
    }

    html_string = render_to_string(template_name, context)

    result = BytesIO()
    pisa_status = pisa.CreatePDF(
        BytesIO(html_string.encode("UTF-8")),
        dest=result,
        encoding='utf-8'
    )

    if pisa_status.err:
        raise Exception(f"xhtml2pdf error: {pisa_status.err}")

    return result.getvalue()


def generate_invoice_pdf(invoice) -> str:
    """
    Generate a PDF for the given invoice and save it to invoice.pdf_file.
    Also copies the PDF to the user's "Invoice" media collection.

    Requires:
      - xhtml2pdf (pip install xhtml2pdf)
      - num2words  (pip install num2words)
    """
    pdf_bytes = _build_pdf_bytes(invoice)
    file_name = f"{invoice.invoice_number}.pdf"
    invoice.pdf_file.save(file_name, ContentFile(pdf_bytes), save=True)

    # Copy the PDF to the "Invoice" media collection for the invoice creator
    _save_to_media_collection(invoice, pdf_bytes, file_name)

    return invoice.pdf_file.name


def _save_to_media_collection(invoice, pdf_bytes, file_name):
    """
    Save a copy of the generated PDF into the user's pinned "Invoice" media collection
    so it appears in their Media library automatically.
    """
    try:
        from django.db import models as db_models
        from media.models import MediaCollection, MediaAsset

        # Find or create the "Invoice" collection (always pinned)
        collection, created = MediaCollection.objects.get_or_create(
            name="Invoice",
            created_by=invoice.created_by,
            defaults={
                'is_pinned': True,
                'description': 'Auto-generated invoice PDFs',
            },
        )

        # Ensure it stays pinned even if someone unpinned it
        if not created and not collection.is_pinned:
            MediaCollection.objects.filter(id=collection.id).update(is_pinned=True)

        # Skip if an asset with this filename already exists (avoids duplicates
        # when an invoice is re-approved)
        if MediaAsset.objects.filter(
            collection=collection, file_name=file_name
        ).exists():
            return

        # Create the media asset
        MediaAsset.objects.create(
            collection=collection,
            file=ContentFile(pdf_bytes, name=file_name),
            uploaded_by=invoice.created_by,
        )

        # Increment denormalised asset count
        MediaCollection.objects.filter(id=collection.id).update(
            asset_count=db_models.F('asset_count') + 1
        )

    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception(
            "Failed to save PDF '%s' to media collection for user %s",
            file_name,
            invoice.created_by_id,
        )
