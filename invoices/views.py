from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from invoices.models import Invoice, InvoiceSchema, InvoiceStatusLog, CompanyProfile
from invoices.serializers import (
    InvoiceListSerializer, InvoiceDetailSerializer, InvoiceWriteSerializer,
    InvoiceSubmitSerializer, InvoiceApproveSerializer, InvoiceRejectSerializer,
    InvoiceSchemaSerializer, CompanyProfileSerializer, ImageUploadSerializer,
)
from invoices.services.pdf_generator import generate_invoice_pdf, _build_pdf_bytes
from invoices.services.notifications import (
    notify_admins_on_submit, notify_creator_on_approval, notify_creator_on_rejection,
)
from authentication.audit_logger import (
    log_invoice_create, log_invoice_update, log_invoice_delete,
    log_invoice_submit, log_invoice_approve, log_invoice_reject, log_invoice_download,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ip(request):
    return request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')


def _get_ua(request):
    return request.META.get('HTTP_USER_AGENT', '')


def _is_admin(user):
    return user.role in ('Superadmin', 'Admin') or user.is_superuser


def _log_transition(invoice, from_status, to_status, actor, note=''):
    InvoiceStatusLog.objects.create(
        invoice=invoice,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        note=note,
    )


# ---------------------------------------------------------------------------
# Invoice Schema Views
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_invoice_schemas(request):
    """
    List all active domain schemas.
    GET /api/invoice-schemas/
    """
    schemas = InvoiceSchema.objects.filter(is_active=True)
    serializer = InvoiceSchemaSerializer(schemas, many=True)
    return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_invoice_schema(request, domain):
    """
    Get field config for a specific domain.
    GET /api/invoice-schemas/{domain}/
    """
    schema = get_object_or_404(InvoiceSchema, domain=domain, is_active=True)
    serializer = InvoiceSchemaSerializer(schema)
    return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Invoice — User-facing CRUD
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def invoice_status_counts(request):
    """GET /api/invoices/status-counts/ — count per status for current user (or all for admins)."""
    if _is_admin(request.user):
        qs = Invoice.objects.all()
    else:
        qs = Invoice.objects.filter(created_by=request.user)
    counts = {s: qs.filter(status=s).count() for s, _ in Invoice.Status.choices}
    return Response({'success': True, 'data': counts})


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def invoice_list_create(request):
    """
    GET  /api/invoices/   — List the authenticated user's invoices.
    POST /api/invoices/   — Create a new DRAFT invoice.

    Query params (GET): domain, status
    """
    if request.method == 'GET':
        # Admins see all invoices; staff see only their own
        if _is_admin(request.user):
            qs = Invoice.objects.select_related('created_by', 'schema').all()
        else:
            qs = Invoice.objects.filter(created_by=request.user)

        domain = request.query_params.get('domain')
        inv_status = request.query_params.get('status')
        if domain:
            qs = qs.filter(domain=domain)
        if inv_status:
            qs = qs.filter(status=inv_status)

        serializer = InvoiceListSerializer(qs, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': qs.count(),
            'data': serializer.data,
        }, status=status.HTTP_200_OK)

    # POST — create invoice (admin: auto-approve; staff: draft)
    serializer = InvoiceWriteSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        invoice = serializer.save()

        if _is_admin(request.user):
            # Snapshot supplier info
            profile = CompanyProfile.objects.first()
            if profile:
                invoice.supplier_name = profile.company_name
                invoice.supplier_gstin = profile.gstin
                invoice.supplier_address = profile.company_address

            invoice.status = Invoice.Status.APPROVED
            invoice.reviewed_by = request.user
            invoice.reviewed_at = timezone.now()
            invoice.save()

            _log_transition(invoice, '', Invoice.Status.APPROVED, request.user, 'Created and auto-approved by admin')
            log_invoice_create(request.user, invoice, _get_ip(request), _get_ua(request))
            log_invoice_approve(request.user, invoice, _get_ip(request), _get_ua(request))

            try:
                generate_invoice_pdf(invoice)
            except Exception:
                pass

            return Response({
                'success': True,
                'message': 'Invoice created and approved.',
                'data': InvoiceDetailSerializer(invoice, context={'request': request}).data,
            }, status=status.HTTP_201_CREATED)

        _log_transition(invoice, '', Invoice.Status.DRAFT, request.user, 'Invoice created')
        log_invoice_create(request.user, invoice, _get_ip(request), _get_ua(request))
        return Response({
            'success': True,
            'message': 'Invoice created successfully.',
            'data': InvoiceDetailSerializer(invoice, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED)

    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Invoice creation failed - Errors: {serializer.errors}")
    logger.error(f"Request data: {request.data}")
    
    return Response({
        'success': False,
        'message': 'Validation failed',
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def invoice_detail(request, pk):
    """
    GET         /api/invoices/{id}/   — Detail (owner or admin).
    PUT/PATCH   /api/invoices/{id}/   — Update DRAFT or REJECTED invoice (owner only). Revising a REJECTED invoice resets it to DRAFT.
    DELETE      /api/invoices/{id}/   — Delete DRAFT or REJECTED invoice (owner only).
    """
    invoice = get_object_or_404(Invoice, pk=pk)

    # Owners see their own; admins see all
    if not _is_admin(request.user) and invoice.created_by != request.user:
        return Response({
            'success': False,
            'message': 'You do not have permission to access this invoice.',
        }, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = InvoiceDetailSerializer(invoice, context={'request': request})
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)

    if request.method == 'DELETE':
        if invoice.status not in (Invoice.Status.DRAFT, Invoice.Status.REJECTED):
            return Response({
                'success': False,
                'message': 'Only DRAFT or REJECTED invoices can be deleted.',
            }, status=status.HTTP_400_BAD_REQUEST)
        if invoice.created_by != request.user:
            return Response({'success': False, 'message': 'You can only delete your own invoices.'}, status=status.HTTP_403_FORBIDDEN)
        log_invoice_delete(request.user, invoice, _get_ip(request), _get_ua(request))
        invoice.delete()
        return Response({'success': True, 'message': 'Invoice deleted.'}, status=status.HTTP_204_NO_CONTENT)

    # PUT / PATCH
    if invoice.status not in (Invoice.Status.DRAFT, Invoice.Status.REJECTED):
        return Response({
            'success': False,
            'message': 'Only DRAFT or REJECTED invoices can be edited.',
        }, status=status.HTTP_400_BAD_REQUEST)
    if invoice.created_by != request.user:
        return Response({'success': False, 'message': 'You can only edit your own invoices.'}, status=status.HTTP_403_FORBIDDEN)

    was_rejected = invoice.status == Invoice.Status.REJECTED
    partial = request.method == 'PATCH'
    serializer = InvoiceWriteSerializer(invoice, data=request.data, partial=partial, context={'request': request})
    if serializer.is_valid():
        invoice = serializer.save()
        log_invoice_update(request.user, invoice, _get_ip(request), _get_ua(request))
        # When revising a rejected invoice, reset it to DRAFT and clear admin remarks
        if was_rejected:
            invoice.status = Invoice.Status.DRAFT
            invoice.admin_remarks = ''
            invoice.save(update_fields=['status', 'admin_remarks'])
            _log_transition(invoice, Invoice.Status.REJECTED, Invoice.Status.DRAFT, request.user, 'Invoice revised after rejection')
        return Response({
            'success': True,
            'message': 'Invoice updated.' if not was_rejected else 'Invoice revised and reset to draft.',
            'data': InvoiceDetailSerializer(invoice, context={'request': request}).data,
        }, status=status.HTTP_200_OK)

    return Response({
        'success': False,
        'message': 'Validation failed',
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_invoice(request, pk):
    """
    Submit a DRAFT invoice for admin review.
    POST /api/invoices/{id}/submit/
    Transition: DRAFT → PENDING
    """
    invoice = get_object_or_404(Invoice, pk=pk, created_by=request.user)

    if invoice.status != Invoice.Status.DRAFT:
        return Response({
            'success': False,
            'message': 'Only DRAFT invoices can be submitted.',
        }, status=status.HTTP_400_BAD_REQUEST)

    serializer = InvoiceSubmitSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    old_status = invoice.status
    invoice.status = Invoice.Status.PENDING
    note = serializer.validated_data.get('notes', '')
    if note:
        invoice.notes = note
    invoice.save()

    _log_transition(invoice, old_status, Invoice.Status.PENDING, request.user, note)
    log_invoice_submit(request.user, invoice, _get_ip(request), _get_ua(request))
    notify_admins_on_submit(invoice)

    return Response({
        'success': True,
        'message': 'Invoice submitted for review.',
        'data': InvoiceDetailSerializer(invoice, context={'request': request}).data,
    }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Invoice — Admin Actions
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_invoice_list(request):
    """
    List ALL invoices across all users (admin only).
    GET /api/invoices/admin/
    Query params: domain, status, created_by (user UUID)
    """
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    qs = Invoice.objects.select_related('created_by', 'schema').all()

    domain = request.query_params.get('domain')
    inv_status = request.query_params.get('status')
    created_by = request.query_params.get('created_by')

    if domain:
        qs = qs.filter(domain=domain)
    if inv_status:
        qs = qs.filter(status=inv_status)
    if created_by:
        qs = qs.filter(created_by=created_by)

    serializer = InvoiceListSerializer(qs, many=True, context={'request': request})
    return Response({'success': True, 'count': qs.count(), 'data': serializer.data}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_invoice(request, pk):
    """
    Approve a PENDING invoice, snapshot supplier data, generate PDF.
    POST /api/invoices/{id}/approve/
    Transition: PENDING → APPROVED
    """
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status != Invoice.Status.PENDING:
        return Response({
            'success': False,
            'message': 'Only PENDING invoices can be approved.',
        }, status=status.HTTP_400_BAD_REQUEST)

    serializer = InvoiceApproveSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    # Snapshot supplier info from CompanyProfile at approval time
    profile = CompanyProfile.objects.first()
    if profile:
        invoice.supplier_name = profile.company_name
        invoice.supplier_gstin = profile.gstin
        invoice.supplier_address = profile.company_address

    old_status = invoice.status
    invoice.status = Invoice.Status.APPROVED
    invoice.reviewed_by = request.user
    invoice.reviewed_at = timezone.now()
    invoice.save()

    _log_transition(invoice, old_status, Invoice.Status.APPROVED, request.user, serializer.validated_data.get('note', ''))
    log_invoice_approve(request.user, invoice, _get_ip(request), _get_ua(request))

    # Generate PDF (non-blocking failure — approval proceeds even if PDF fails)
    try:
        generate_invoice_pdf(invoice)
    except Exception:
        pass

    notify_creator_on_approval(invoice)

    return Response({
        'success': True,
        'message': 'Invoice approved and PDF generated.',
        'data': InvoiceDetailSerializer(invoice, context={'request': request}).data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_invoice(request, pk):
    """
    Reject a PENDING invoice with mandatory admin remarks.
    POST /api/invoices/{id}/reject/
    Transition: PENDING → REJECTED
    """
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status != Invoice.Status.PENDING:
        return Response({
            'success': False,
            'message': 'Only PENDING invoices can be rejected.',
        }, status=status.HTTP_400_BAD_REQUEST)

    serializer = InvoiceRejectSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    old_status = invoice.status
    invoice.status = Invoice.Status.REJECTED
    invoice.admin_remarks = serializer.validated_data['admin_remarks']
    invoice.reviewed_by = request.user
    invoice.reviewed_at = timezone.now()
    invoice.save()

    _log_transition(invoice, old_status, Invoice.Status.REJECTED, request.user, serializer.validated_data.get('note', ''))
    log_invoice_reject(request.user, invoice, _get_ip(request), _get_ua(request))
    notify_creator_on_rejection(invoice)

    return Response({
        'success': True,
        'message': 'Invoice rejected.',
        'data': InvoiceDetailSerializer(invoice, context={'request': request}).data,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_invoice_pdf(request, pk):
    """
    Stream invoice PDF as attachment.
    GET /api/invoices/{id}/download/
    Marks APPROVED invoice as COMPLETED after first download.
    """
    invoice = get_object_or_404(Invoice, pk=pk)

    if not _is_admin(request.user) and invoice.created_by != request.user:
        return Response({'success': False, 'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if invoice.status not in (Invoice.Status.APPROVED, Invoice.Status.COMPLETED):
        return Response({
            'success': False,
            'message': 'PDF not available. Invoice must be approved first.',
        }, status=status.HTTP_404_NOT_FOUND)

    # Generate PDF in memory so this works without persistent file storage
    try:
        content = _build_pdf_bytes(invoice)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("PDF generation failed for invoice %s", pk)
        return Response({
            'success': False,
            'message': f'PDF could not be generated: {exc}',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'

    log_invoice_download(request.user, invoice, _get_ip(request), _get_ua(request))
    if invoice.status == Invoice.Status.APPROVED:
        invoice.status = Invoice.Status.COMPLETED
        invoice.save(update_fields=['status'])
        _log_transition(invoice, Invoice.Status.APPROVED, Invoice.Status.COMPLETED, request.user, 'PDF downloaded')

    return response


# ---------------------------------------------------------------------------
# Company Profile (admin-only)
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def invoice_audit_logs(request):
    """
    GET /api/invoices/audit-logs/
    Returns invoice-related audit logs (admin: all; staff: own only).
    Query params: action, invoice_number, user_id
    """
    from authentication.models import AuditLog

    INVOICE_ACTIONS = [
        'invoice_create', 'invoice_update', 'invoice_delete',
        'invoice_submit', 'invoice_approve', 'invoice_reject', 'invoice_download',
    ]

    qs = AuditLog.objects.filter(action__in=INVOICE_ACTIONS).select_related('user')

    if not _is_admin(request.user):
        qs = qs.filter(user=request.user)

    action = request.query_params.get('action')
    invoice_number = request.query_params.get('invoice_number')
    user_id = request.query_params.get('user_id')

    if action:
        qs = qs.filter(action=action)
    if invoice_number:
        qs = qs.filter(details__invoice_number__icontains=invoice_number)
    if user_id and _is_admin(request.user):
        qs = qs.filter(user_id=user_id)

    qs = qs.order_by('-created_at')[:200]

    data = [
        {
            'id': str(log.id),
            'action': log.action,
            'performed_by': {
                'id': str(log.user.id),
                'email': log.user.email,
                'name': f"{log.user.first_name} {log.user.last_name}".strip() or log.user.email,
                'role': log.user.role,
            },
            'invoice_number': log.details.get('invoice_number'),
            'client_name': log.details.get('client_name'),
            'client_email': log.details.get('client_email'),
            'grand_total': log.details.get('grand_total'),
            'domain': log.details.get('domain'),
            'status': log.details.get('status'),
            'ip_address': log.ip_address,
            'timestamp': log.created_at,
        }
        for log in qs
    ]

    return Response({'success': True, 'count': len(data), 'data': data}, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def company_profile_view(request):
    """
    GET         /api/company-profile/   — Retrieve company profile.
    PUT/PATCH   /api/company-profile/   — Create or update company profile.
    """
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    profile = CompanyProfile.objects.first()

    if request.method == 'GET':
        if not profile:
            return Response({'success': True, 'data': None, 'message': 'No company profile configured yet.'}, status=status.HTTP_200_OK)
        serializer = CompanyProfileSerializer(profile, context={'request': request})
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)

    # PUT / PATCH
    partial = request.method == 'PATCH'
    if profile:
        serializer = CompanyProfileSerializer(profile, data=request.data, partial=partial, context={'request': request})
    else:
        serializer = CompanyProfileSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        instance = serializer.save(updated_by=request.user)
        return Response({
            'success': True,
            'message': 'Company profile updated.',
            'data': CompanyProfileSerializer(instance, context={'request': request}).data,
        }, status=status.HTTP_200_OK)

    return Response({'success': False, 'message': 'Validation failed', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_company_logo(request):
    """POST /api/company-profile/upload-logo/"""
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    profile = CompanyProfile.objects.first()
    if not profile:
        return Response({'success': False, 'message': 'Create a company profile before uploading assets.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ImageUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    profile.logo = serializer.validated_data['image']
    profile.updated_by = request.user
    profile.save()

    return Response({
        'success': True,
        'message': 'Logo uploaded.',
        'logo_url': request.build_absolute_uri(profile.logo.url),
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_company_signature(request):
    """POST /api/company-profile/upload-signature/"""
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    profile = CompanyProfile.objects.first()
    if not profile:
        return Response({'success': False, 'message': 'Create a company profile before uploading assets.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ImageUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    profile.digital_signature = serializer.validated_data['image']
    profile.updated_by = request.user
    profile.save()

    return Response({
        'success': True,
        'message': 'Digital signature uploaded.',
        'signature_url': request.build_absolute_uri(profile.digital_signature.url),
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_company_seal(request):
    """POST /api/company-profile/upload-seal/"""
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    profile = CompanyProfile.objects.first()
    if not profile:
        return Response({'success': False, 'message': 'Create a company profile before uploading assets.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ImageUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    profile.company_seal = serializer.validated_data['image']
    profile.updated_by = request.user
    profile.save()

    return Response({
        'success': True,
        'message': 'Company seal uploaded.',
        'seal_url': request.build_absolute_uri(profile.company_seal.url),
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_company_signature(request):
    """DELETE /api/company-profile/remove-signature/"""
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    profile = CompanyProfile.objects.first()
    if not profile:
        return Response({'success': False, 'message': 'No company profile found.'}, status=status.HTTP_404_NOT_FOUND)

    if profile.digital_signature:
        profile.digital_signature.delete(save=False)
        profile.digital_signature = None
        profile.save(update_fields=['digital_signature'])

    return Response({'success': True, 'message': 'Digital signature removed.'}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_company_logo(request):
    """DELETE /api/company-profile/remove-logo/"""
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    profile = CompanyProfile.objects.first()
    if not profile:
        return Response({'success': False, 'message': 'No company profile found.'}, status=status.HTTP_404_NOT_FOUND)

    if profile.logo:
        profile.logo.delete(save=False)
        profile.logo = None
        profile.save(update_fields=['logo'])

    return Response({'success': True, 'message': 'Company logo removed.'}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_company_seal(request):
    """DELETE /api/company-profile/remove-seal/"""
    if not _is_admin(request.user):
        return Response({'success': False, 'message': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    profile = CompanyProfile.objects.first()
    if not profile:
        return Response({'success': False, 'message': 'No company profile found.'}, status=status.HTTP_404_NOT_FOUND)

    if profile.company_seal:
        profile.company_seal.delete(save=False)
        profile.company_seal = None
        profile.save(update_fields=['company_seal'])

    return Response({'success': True, 'message': 'Company seal removed.'}, status=status.HTTP_200_OK)
