"""
Security & Data Privacy Service for HR Module.
Handles data masking, deduplication checks, IP restrictions, and data retention policies.
"""

import re
import ipaddress
from datetime import date, timedelta
from django.db.models import Q
from django.utils import timezone


class DataMaskingService:
    """Service for masking sensitive employee data per GDPR/DPDP compliance."""

    @staticmethod
    def mask_aadhaar(value):
        """Mask Aadhaar: show last 4 digits only. XXXX-XXXX-1234"""
        if not value:
            return None
        clean = re.sub(r'[^0-9]', '', str(value))
        if len(clean) == 12:
            return f"XXXX-XXXX-{clean[-4:]}"
        if len(clean) >= 4:
            return f"XXXX-{clean[-4:]}"
        return "XXXX"

    @staticmethod
    def mask_pan(value):
        """Mask PAN: show last 4 characters. ABCDXXXXXF"""
        if not value:
            return None
        clean = str(value).upper().strip()
        if len(clean) == 10:
            return f"{clean[:4]}XXXXX{clean[-1]}"
        if len(clean) >= 4:
            return f"XXXX{clean[-4:]}"
        return "XXXX"

    @staticmethod
    def mask_bank_account(value):
        """Mask bank account: show last 4 digits. XXXX-XXXX-1234"""
        if not value:
            return None
        clean = re.sub(r'[^0-9]', '', str(value))
        if len(clean) >= 4:
            return f"XXXX-XXXX-{clean[-4:]}"
        return "XXXX-XXXX"

    @staticmethod
    def mask_ifsc(value):
        """Mask IFSC: show first 4 and last 3. ABCD0XXX567"""
        if not value:
            return None
        clean = str(value).upper().strip()
        if len(clean) == 11:
            return f"{clean[:4]}XXX{clean[-3:]}"
        return "XXXX0XXX"

    @staticmethod
    def mask_mobile(value):
        """Mask mobile: show last 4 digits. XXXX-XX-1234"""
        if not value:
            return None
        clean = re.sub(r'[^0-9+]', '', str(value))
        if len(clean) >= 4:
            return f"XXXX-XX-{clean[-4:]}"
        return "XXXX-XX"

    @staticmethod
    def mask_email(value):
        """Mask email: show first char and domain. j***@company.com"""
        if not value:
            return None
        parts = str(value).split('@')
        if len(parts) == 2:
            name = parts[0]
            domain = parts[1]
            masked_name = f"{name[0]}***{name[-1]}" if len(name) > 2 else f"{name[0]}***"
            return f"{masked_name}@{domain}"
        return "***"

    @staticmethod
    def get_masked_employee(employee):
        """Return a dict with masked sensitive fields for non-privileged users."""
        return {
            'employee_id': employee.employee_id,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'official_email': employee.official_email,
            # Masked sensitive fields
            'personal_email': DataMaskingService.mask_email(employee.personal_email),
            'personal_mobile': DataMaskingService.mask_mobile(employee.personal_mobile),
            'aadhaar_number': DataMaskingService.mask_aadhaar(employee.aadhaar_number),
            'pan_number': DataMaskingService.mask_pan(employee.pan_number),
            'bank_account_number': DataMaskingService.mask_bank_account(employee.bank_account_number),
            'ifsc_code': DataMaskingService.mask_ifsc(employee.ifsc_code),
        }

    MASK_RULES = {
        'aadhaar_number': mask_aadhaar.__func__,
        'pan_number': mask_pan.__func__,
        'bank_account_number': mask_bank_account.__func__,
        'ifsc_code': mask_ifsc.__func__,
        'personal_mobile': mask_mobile.__func__,
        'personal_email': mask_email.__func__,
    }

    @staticmethod
    def mask_field(field_name, value):
        """Mask a single field by name."""
        masker = DataMaskingService.MASK_RULES.get(field_name)
        if masker:
            return masker(value)
        return value


class DedupService:
    """Service for detecting duplicate employee records."""

    @staticmethod
    def check_duplicates(data):
        """
        Check for duplicate employees across multiple fields.
        Returns a dict of potential duplicates found.
        """
        results = {}
        employee_model = None
        try:
            from hr.models import Employee
            employee_model = Employee
        except ImportError:
            return {'error': 'Employee model not available'}

        # Check Aadhaar
        aadhaar = data.get('aadhaar_number', '').strip()
        if aadhaar and len(aadhaar) >= 4:
            matches = employee_model.objects.filter(
                aadhaar_number__endswith=aadhaar[-4:]
            ).exclude(is_active=False)
            if matches.exists():
                results['aadhaar_number'] = [
                    {'employee_id': e.employee_id, 'name': e.get_full_name(), 
                     'value': DataMaskingService.mask_aadhaar(e.aadhaar_number)}
                    for e in matches[:5]
                ]

        # Check PAN
        pan = data.get('pan_number', '').strip().upper()
        if pan and len(pan) >= 4:
            matches = employee_model.objects.filter(
                pan_number__endswith=pan[-4:]
            ).exclude(is_active=False)
            if matches.exists():
                results['pan_number'] = [
                    {'employee_id': e.employee_id, 'name': e.get_full_name(),
                     'value': DataMaskingService.mask_pan(e.pan_number)}
                    for e in matches[:5]
                ]

        # Check Email
        email = data.get('personal_email', '').strip().lower()
        if email:
            matches = employee_model.objects.filter(
                Q(personal_email__iexact=email) | Q(official_email__iexact=email)
            ).exclude(is_active=False)
            if matches.exists():
                results['email'] = [
                    {'employee_id': e.employee_id, 'name': e.get_full_name(), 'value': e.personal_email}
                    for e in matches[:5]
                ]

        # Check Mobile
        mobile = data.get('personal_mobile', '').strip()
        if mobile and len(mobile) >= 6:
            matches = employee_model.objects.filter(
                personal_mobile__endswith=mobile[-6:]
            ).exclude(is_active=False)
            if matches.exists():
                results['mobile'] = [
                    {'employee_id': e.employee_id, 'name': e.get_full_name(), 'value': DataMaskingService.mask_mobile(e.personal_mobile)}
                    for e in matches[:5]
                ]

        return results

    @staticmethod
    def bulk_dedup_check(employee_ids=None):
        """
        Run dedup check across all active employees.
        Returns a report of potential duplicate records.
        """
        from hr.models import Employee
        
        queryset = Employee.objects.filter(is_active=True)
        if employee_ids:
            queryset = queryset.filter(id__in=employee_ids)

        duplicates = []
        employees = list(queryset)

        # Check by Aadhaar last 4 digits
        aadhaar_groups = {}
        for emp in employees:
            if emp.aadhaar_number and len(emp.aadhaar_number) >= 4:
                key = emp.aadhaar_number[-4:]
                if key not in aadhaar_groups:
                    aadhaar_groups[key] = []
                aadhaar_groups[key].append(emp)

        for key, group in aadhaar_groups.items():
            if len(group) > 1:
                duplicates.append({
                    'type': 'AADHAAR',
                    'match_value': f'XXXX-XXXX-{key}',
                    'employees': [
                        {'employee_id': e.employee_id, 'name': e.get_full_name()}
                        for e in group
                    ],
                })

        # Check by PAN last 4 chars
        pan_groups = {}
        for emp in employees:
            if emp.pan_number and len(emp.pan_number) >= 4:
                key = emp.pan_number[-4:].upper()
                if key not in pan_groups:
                    pan_groups[key] = []
                pan_groups[key].append(emp)

        for key, group in pan_groups.items():
            if len(group) > 1:
                duplicates.append({
                    'type': 'PAN',
                    'match_value': f'XXXX{key}', 
                    'employees': [
                        {'employee_id': e.employee_id, 'name': e.get_full_name()}
                        for e in group
                    ],
                })

        return {
            'total_checked': len(employees),
            'duplicate_groups_found': len(duplicates),
            'duplicates': duplicates,
        }


class IPAccessRestrictionService:
    """Service for IP-based access control."""

    @staticmethod
    def is_ip_allowed(ip_address, user=None, required_role=None):
        """
        Check if an IP address is allowed access.
        If no restrictions configured, access is granted.
        """
        from hr.models import IPAccessRestriction
        
        if not ip_address:
            return True

        # Check if there are any active restrictions
        restrictions = IPAccessRestriction.objects.filter(is_active=True)
        
        if not restrictions.exists():
            return True  # No restrictions configured

        ip_obj = ipaddress.ip_address(ip_address)

        for restriction in restrictions:
            if required_role and restriction.role_required:
                if restriction.role_required != required_role and restriction.role_required != 'ANY':
                    continue
            if user and restriction.user and restriction.user != user:
                continue

            # Check if IP is in whitelist
            if restriction.restriction_type == 'WHITELIST':
                allowed = False
                for cidr in restriction.allowed_networks:
                    try:
                        network = ipaddress.ip_network(cidr, strict=False)
                        if ip_obj in network:
                            allowed = True
                            break
                    except ValueError:
                        continue
                if not allowed:
                    return False

            # Check if IP is in blacklist
            elif restriction.restriction_type == 'BLACKLIST':
                for cidr in restriction.blocked_networks:
                    try:
                        network = ipaddress.ip_network(cidr, strict=False)
                        if ip_obj in network:
                            return False
                    except ValueError:
                        continue

        return True


class DataRetentionService:
    """Service for managing data retention and purging policies."""

    RETENTION_PERIODS = {
        'EMPLOYEE': {
            'active': None,  # Keep while active
            'post_exit_years': 7,  # Keep 7 years after exit
        },
        'PAYROLL': {
            'years': 8,  # Keep payroll records for 8 years
        },
        'ATTENDANCE': {
            'years': 3,  # Keep attendance for 3 years
        },
        'LEAVE': {
            'years': 5,  # Keep leave records for 5 years
        },
        'AUDIT_LOG': {
            'years': 10,  # Keep audit logs for 10 years
        },
        'TICKET': {
            'years': 3,  # Keep HR tickets for 3 years
        },
    }

    @staticmethod
    def get_records_to_purge(data_type, reference_date=None):
        """
        Get records that are eligible for purging based on retention policy.
        """
        if reference_date is None:
            reference_date = date.today()

        policy = DataRetentionService.RETENTION_PERIODS.get(data_type)
        if not policy:
            return {'error': f'Unknown data type: {data_type}'}

        cutoff_date = reference_date - timedelta(days=policy['years'] * 365)

        from hr.models import Employee

        if data_type == 'EMPLOYEE':
            # Employees separated more than 7 years ago
            records = Employee.objects.filter(
                status='SEPARATED',
                separation_date__lt=cutoff_date,
                is_active=False,
            )
            return {
                'data_type': data_type,
                'cutoff_date': cutoff_date.isoformat(),
                'count': records.count(),
                'sample': list(records.values('employee_id', 'first_name', 'last_name', 'separation_date')[:10]),
                'purge_eligible': True,
            }

        return {'data_type': data_type, 'count': 0, 'purge_eligible': False}

    @staticmethod
    def get_retention_summary():
        """Get a summary of all data retention policies and expiring records."""
        summary = []
        for data_type, policy in DataRetentionService.RETENTION_PERIODS.items():
            info = DataRetentionService.get_records_to_purge(data_type)
            summary.append({
                'data_type': data_type,
                'retention_years': policy.get('years') or policy.get('post_exit_years'),
                'purge_eligible_count': info.get('count', 0),
            })
        return summary
