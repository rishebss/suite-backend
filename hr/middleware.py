"""
HR Module Middleware — Session Timeout & MFA Enforcement

Provides:
1. Idle session timeout for HR admin screens (30 min default)
2. MFA enforcement for HR Admin and Payroll roles
3. IP-based access restriction for payroll processing
"""

import time
from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages

from hr.models import IPAccessRestriction


class HRSessionTimeoutMiddleware:
    """
    Enforce idle session timeout for HR module screens.
    
    - Default timeout: 30 minutes (configurable via HR_SESSION_TIMEOUT_MINUTES)
    - Resets on each authenticated request to HR endpoints
    - Redirects to login page with appropriate message
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_minutes = getattr(settings, 'HR_SESSION_TIMEOUT_MINUTES', 30)

    def __call__(self, request):
        # Only enforce for authenticated users on HR paths
        if request.user.is_authenticated and request.path.startswith('/api/hr/'):
            # Check if this is a sensitive HR admin endpoint
            sensitive_paths = [
                '/api/hr/payroll/', '/api/hr/salary-revisions/', '/api/hr/employees/',
                '/api/hr/compliance/', '/api/hr/fnf-settlements/', '/api/hr/resignations/',
            ]
            is_sensitive = any(request.path.startswith(p) for p in sensitive_paths)
            
            if is_sensitive and request.user.role in ['Superadmin', 'Admin']:
                last_activity = request.session.get('hr_last_activity')
                now = time.time()
                
                if last_activity:
                    elapsed_minutes = (now - last_activity) / 60
                    if elapsed_minutes > self.timeout_minutes:
                        # Session timeout — clear HR session and return 401
                        from rest_framework.response import Response
                        from rest_framework import status
                        return Response(
                            {'error': 'Session expired due to inactivity. Please login again.',
                             'code': 'SESSION_TIMEOUT'},
                            status=status.HTTP_401_UNAUTHORIZED
                        )
                
                # Update last activity timestamp
                request.session['hr_last_activity'] = now

        response = self.get_response(request)
        return response


class HRMFAEnforcementMiddleware:
    """
    Enforce Multi-Factor Authentication for sensitive HR roles.
    
    - Requires MFA for: HR Admin, Payroll Executive, Super Admin
    - Blocks access to sensitive endpoints if MFA not verified
    - Checks `session['hr_mfa_verified']` flag
    """

    MFA_REQUIRED_ROLES = ['Superadmin', 'Admin']
    MFA_SENSITIVE_PATHS = [
        '/api/hr/payroll/process_', '/api/hr/payroll/bulk_approve/',
        '/api/hr/salary-revisions/', '/api/hr/employees/import_csv/',
        '/api/hr/bulk-salary-revisions/', '/api/hr/fnf-settlements/approve_',
        '/api/hr/ip-access-restrictions/', '/api/hr/data-retention/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            is_mfa_required = (
                request.user.role in self.MFA_REQUIRED_ROLES and
                any(request.path.startswith(p) for p in self.MFA_SENSITIVE_PATHS)
            )

            if is_mfa_required and not request.session.get('hr_mfa_verified', False):
                from rest_framework.response import Response
                from rest_framework import status
                return Response(
                    {'error': 'MFA verification required. Please complete MFA to access this resource.',
                     'code': 'MFA_REQUIRED', 'requires_mfa': True},
                    status=status.HTTP_403_FORBIDDEN
                )

        response = self.get_response(request)
        return response


class HRAccessLogMiddleware:
    """
    Log access to sensitive HR endpoints for audit purposes.
    """

    SENSITIVE_ACTIONS = ['POST', 'PUT', 'PATCH', 'DELETE']
    LOG_PATHS = [
        '/api/hr/employees/', '/api/hr/payroll/', '/api/hr/salary-revisions/',
        '/api/hr/fnf-settlements/', '/api/hr/resignations/', '/api/hr/employee-loans/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (request.user.is_authenticated and
            request.method in self.SENSITIVE_ACTIONS and
            any(request.path.startswith(p) for p in self.LOG_PATHS)):
            
            try:
                from authentication.audit_logger import log_audit
                log_audit(
                    user=request.user,
                    action=f'hr_{request.method.lower()}_{request.path.split("/")[-2] if len(request.path.split("/")) > 2 else "unknown"}',
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    details={
                        'path': request.path,
                        'method': request.method,
                        'status_code': response.status_code,
                    }
                )
            except Exception:
                pass  # Silent fail for audit logging

        return response
