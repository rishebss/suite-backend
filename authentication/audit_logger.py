"""
Audit logging utility for tracking user actions
"""
from authentication.models import AuditLog


def log_audit(user, action, action_target=None, ip_address=None, user_agent=None, status='success', details=None, target_changes=None):
    """
    Log an audit entry for user action
    
    Args:
        user: User object (who performed the action)
        action: Action type (login, logout, password_change, user_create, etc.)
        action_target: User object being affected by the action
        ip_address: IP address of the request
        user_agent: User agent string
        status: success, failed, or pending
        details: Additional JSON details
        target_changes: Dictionary showing what changed in target_changes field
    """
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            action_target=action_target,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            details=details or {},
            target_changes=target_changes or {}
        )
    except Exception as e:
        print(f"Error logging audit: {e}")


def log_login(user, ip_address=None, user_agent=None, success=True):
    """Log user login attempt"""
    status = 'success' if success else 'failed'
    log_audit(
        user=user,
        action='login',
        ip_address=ip_address,
        user_agent=user_agent,
        status=status
    )


def log_logout(user, ip_address=None, user_agent=None):
    """Log user logout"""
    log_audit(
        user=user,
        action='logout',
        ip_address=ip_address,
        user_agent=user_agent
    )


def log_password_change(user, ip_address=None, user_agent=None, success=True):
    """Log password change"""
    status = 'success' if success else 'failed'
    log_audit(
        user=user,
        action='password_change',
        ip_address=ip_address,
        user_agent=user_agent,
        status=status
    )


def log_email_verification(user, ip_address=None, user_agent=None, success=True):
    """Log email verification"""
    status = 'success' if success else 'failed'
    log_audit(
        user=user,
        action='email_verify',
        ip_address=ip_address,
        user_agent=user_agent,
        status=status
    )


def log_profile_update(user, ip_address=None, user_agent=None, success=True):
    """Log profile update"""
    status = 'success' if success else 'failed'
    log_audit(
        user=user,
        action='profile_update',
        ip_address=ip_address,
        user_agent=user_agent,
        status=status
    )


# User Management Logging Functions

def log_user_create(admin_user, new_user, ip_address=None, user_agent=None):
    """Log user creation by admin"""
    log_audit(
        user=admin_user,
        action='user_create',
        action_target=new_user,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            'email': new_user.email,
            'role': new_user.role,
            'first_name': new_user.first_name,
            'last_name': new_user.last_name
        }
    )


def log_user_update(admin_user, updated_user, changes=None, ip_address=None, user_agent=None):
    """Log user update with change tracking"""
    log_audit(
        user=admin_user,
        action='user_update',
        action_target=updated_user,
        ip_address=ip_address,
        user_agent=user_agent,
        target_changes=changes or {}
    )


def log_user_delete(admin_user, deleted_user_email, ip_address=None, user_agent=None):
    """Log user delete"""
    log_audit(
        user=admin_user,
        action='user_delete',
        action_target=None,
        ip_address=ip_address,
        user_agent=user_agent,
        details={'email': deleted_user_email}
    )


def log_user_activate(admin_user, activated_user, ip_address=None, user_agent=None):
    """Log user activation"""
    log_audit(
        user=admin_user,
        action='user_activate',
        action_target=activated_user,
        ip_address=ip_address,
        user_agent=user_agent,
        details={'email': activated_user.email}
    )


def log_user_role_change(admin_user, target_user, old_role, new_role, ip_address=None, user_agent=None):
    """Log user role change"""
    log_audit(
        user=admin_user,
        action='user_role_change',
        action_target=target_user,
        ip_address=ip_address,
        user_agent=user_agent,
        target_changes={
            'role': {'old': old_role, 'new': new_role}
        }
    )


def log_user_department_change(admin_user, target_user, old_dept, new_dept, ip_address=None, user_agent=None):
    """Log user department change"""
    old_dept_name = old_dept.name if old_dept else None
    new_dept_name = new_dept.name if new_dept else None
    log_audit(
        user=admin_user,
        action='user_department_change',
        action_target=target_user,
        ip_address=ip_address,
        user_agent=user_agent,
        target_changes={
            'department': {'old': old_dept_name, 'new': new_dept_name}
        }
    )


def _invoice_details(invoice):
    return {
        'invoice_number': invoice.invoice_number,
        'domain': invoice.domain,
        'client_name': invoice.client_name,
        'client_email': invoice.client_email,
        'grand_total': str(invoice.grand_total),
        'status': invoice.status,
    }


def log_invoice_create(user, invoice, ip_address=None, user_agent=None):
    log_audit(user=user, action='invoice_create', ip_address=ip_address,
              user_agent=user_agent, details=_invoice_details(invoice))


def log_invoice_update(user, invoice, ip_address=None, user_agent=None):
    log_audit(user=user, action='invoice_update', ip_address=ip_address,
              user_agent=user_agent, details=_invoice_details(invoice))


def log_invoice_delete(user, invoice, ip_address=None, user_agent=None):
    log_audit(user=user, action='invoice_delete', ip_address=ip_address,
              user_agent=user_agent, details=_invoice_details(invoice))


def log_invoice_submit(user, invoice, ip_address=None, user_agent=None):
    log_audit(user=user, action='invoice_submit', ip_address=ip_address,
              user_agent=user_agent, details=_invoice_details(invoice))


def log_invoice_approve(user, invoice, ip_address=None, user_agent=None):
    log_audit(user=user, action='invoice_approve', ip_address=ip_address,
              user_agent=user_agent, details=_invoice_details(invoice))


def log_invoice_reject(user, invoice, ip_address=None, user_agent=None):
    log_audit(user=user, action='invoice_reject', ip_address=ip_address,
              user_agent=user_agent, details=_invoice_details(invoice))


def log_invoice_download(user, invoice, ip_address=None, user_agent=None):
    log_audit(user=user, action='invoice_download', ip_address=ip_address,
              user_agent=user_agent, details=_invoice_details(invoice))


def log_user_supervisor_change(admin_user, target_user, old_supervisor, new_supervisor, ip_address=None, user_agent=None):
    """Log supervisor assignment change"""
    old_sup_name = f"{old_supervisor.first_name} {old_supervisor.last_name}" if old_supervisor else None
    new_sup_name = f"{new_supervisor.first_name} {new_supervisor.last_name}" if new_supervisor else None
    log_audit(
        user=admin_user,
        action='user_supervisor_change',
        action_target=target_user,
        ip_address=ip_address,
        user_agent=user_agent,
        target_changes={
            'supervisor': {'old': old_sup_name, 'new': new_sup_name}
        }
    )

