"""
Invoice Notification Service
=============================
Sends transactional emails on status transitions.
All sends use fail_silently=True so a broken SMTP config never fails an API request.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model


def notify_admins_on_submit(invoice):
    """Notify Admin/Manager users when an invoice is submitted for review."""
    User = get_user_model()
    admin_emails = list(
        User.objects.filter(role__in=['Admin', 'Manager'], is_active=True)
        .values_list('email', flat=True)
    )
    if not admin_emails:
        return

    subject = f"Invoice #{invoice.invoice_number} Awaiting Review"
    message = (
        f"Invoice #{invoice.invoice_number} submitted by "
        f"{invoice.created_by.get_full_name()} ({invoice.created_by.email}) "
        f"is awaiting your review.\n\n"
        f"Client:  {invoice.client_name}\n"
        f"Domain:  {invoice.domain}\n"
        f"Amount:  {invoice.currency} {invoice.grand_total}\n"
    )

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, admin_emails, fail_silently=True)
    except Exception:
        pass


def notify_creator_on_approval(invoice):
    """Notify the invoice creator when their invoice is approved."""
    subject = f"Invoice #{invoice.invoice_number} Approved"
    message = (
        f"Your invoice #{invoice.invoice_number} has been approved.\n\n"
        f"The PDF is ready — please log in to download it.\n\n"
        f"Client:  {invoice.client_name}\n"
        f"Amount:  {invoice.currency} {invoice.grand_total}\n"
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [invoice.created_by.email],
            fail_silently=True,
        )
    except Exception:
        pass


def notify_creator_on_rejection(invoice):
    """Notify the invoice creator when their invoice is rejected."""
    subject = f"Invoice #{invoice.invoice_number} Rejected"
    message = (
        f"Your invoice #{invoice.invoice_number} has been rejected.\n\n"
        f"Admin remarks: {invoice.admin_remarks or 'No remarks provided.'}\n\n"
        f"Please revise and resubmit.\n"
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [invoice.created_by.email],
            fail_silently=True,
        )
    except Exception:
        pass
