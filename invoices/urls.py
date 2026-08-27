from django.urls import path
from . import views

# All paths are relative; included in core/urls.py under the 'api/' prefix.
# This keeps invoice, invoice-schema, and company-profile under one app.

app_name = 'invoices'

urlpatterns = [

    # ------------------------------------------------------------------
    # Invoice CRUD + workflow actions
    # Mounted at: /api/invoices/
    # ------------------------------------------------------------------
    path('invoices/status-counts/', views.invoice_status_counts, name='invoice-status-counts'),
    path('invoices/', views.invoice_list_create, name='invoice-list-create'),
    path('invoices/admin/', views.admin_invoice_list, name='admin-invoice-list'),
    path('invoices/audit-logs/', views.invoice_audit_logs, name='invoice-audit-logs'),
    path('invoices/<uuid:pk>/', views.invoice_detail, name='invoice-detail'),
    path('invoices/<uuid:pk>/submit/', views.submit_invoice, name='invoice-submit'),
    path('invoices/<uuid:pk>/approve/', views.approve_invoice, name='invoice-approve'),
    path('invoices/<uuid:pk>/reject/', views.reject_invoice, name='invoice-reject'),
    path('invoices/<uuid:pk>/download/', views.download_invoice_pdf, name='invoice-download'),

    # ------------------------------------------------------------------
    # Invoice Schemas (domain field configs)
    # Mounted at: /api/invoice-schemas/
    # ------------------------------------------------------------------
    path('invoice-schemas/', views.list_invoice_schemas, name='schema-list'),
    path('invoice-schemas/<str:domain>/', views.get_invoice_schema, name='schema-detail'),

    # ------------------------------------------------------------------
    # Company Profile (branding, admin-only)
    # Mounted at: /api/company-profile/
    # ------------------------------------------------------------------
    path('company-profile/', views.company_profile_view, name='company-profile'),
    path('company-profile/upload-logo/', views.upload_company_logo, name='upload-logo'),
    path('company-profile/upload-signature/', views.upload_company_signature, name='upload-signature'),
    path('company-profile/upload-seal/', views.upload_company_seal, name='upload-seal'),
    path('company-profile/remove-logo/', views.remove_company_logo, name='remove-logo'),
    path('company-profile/remove-signature/', views.remove_company_signature, name='remove-signature'),
    path('company-profile/remove-seal/', views.remove_company_seal, name='remove-seal'),
]
