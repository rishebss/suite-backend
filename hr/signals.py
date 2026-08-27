from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import F
from datetime import datetime
from hr.models import Employee, EmployeeDocument, LeaveApplication, Payroll, EmployeeLeaveBalance
from media.utils import sync_file_to_media_library, COLLECTION_HR_DOCUMENTS, COLLECTION_HR_PHOTOS


@receiver(post_save, sender=EmployeeDocument)
def sync_employee_document_to_media(sender, instance, created, **kwargs):
    """
    When a new employee document is created, sync it to the media library
    so it appears in the user's Media page.
    """
    # Only sync on creation to avoid re-reading file on metadata updates
    if not created or not instance.document_file:
        return

    # Determine the uploader — use the employee's linked user or system
    uploaded_by = None
    if instance.employee and instance.employee.user:
        uploaded_by = instance.employee.user
    elif instance.verified_by:
        uploaded_by = instance.verified_by

    if not uploaded_by:
        return

    # Read file bytes for copying into media storage
    try:
        file_content = instance.document_file.read()
        instance.document_file.seek(0)
    except Exception:
        return

    sync_file_to_media_library(
        file_content=file_content,
        file_name=instance.document_file.name,
        collection_name=COLLECTION_HR_DOCUMENTS,
        uploaded_by=uploaded_by,
        description=f"{instance.get_document_type_display()} — {instance.employee.get_full_name()}",
        source_object=instance.employee,
        source_display=f"Employee: {instance.employee.get_full_name()} ({instance.employee.employee_id})",
    )


@receiver(pre_save, sender=Employee)
def track_photo_change(sender, instance, **kwargs):
    """Store the old photo path before save so post_save can detect changes."""
    if instance.pk:
        try:
            old = Employee.objects.get(pk=instance.pk)
            instance._old_photo = old.photo.name if old.photo else None
        except Employee.DoesNotExist:
            instance._old_photo = None
    else:
        instance._old_photo = None


@receiver(post_save, sender=Employee)
def sync_employee_photo_to_media(sender, instance, **kwargs):
    """
    When an employee's photo is updated, sync it to the media library.
    Only fires when the photo field actually changes.
    """
    # Check if photo actually changed
    old_photo = getattr(instance, '_old_photo', None)
    new_photo = instance.photo.name if instance.photo else None
    if old_photo == new_photo or not new_photo:
        return

    if not instance.user:
        return

    try:
        file_content = instance.photo.read()
        instance.photo.seek(0)
    except Exception:
        return

    sync_file_to_media_library(
        file_content=file_content,
        file_name=f"{instance.employee_id}_{instance.photo.name.split('/')[-1]}",
        collection_name=COLLECTION_HR_PHOTOS,
        uploaded_by=instance.user,
        description=f"Photo — {instance.get_full_name()}",
        source_object=instance,
        source_display=f"Employee: {instance.get_full_name()} ({instance.employee_id})",
    )


@receiver(post_save, sender=Employee)
def create_leave_balances(sender, instance, created, **kwargs):
    """
    When an employee is created or status changes to ACTIVE, create leave balances
    """
    if created and (instance.status == 'ACTIVE' or instance.status == 'ONBOARDING'):
        from hr.models import LeaveType
        today = datetime.now()
        if today.month >= 4:
            financial_year = f"{today.year}-{today.year + 1}"
        else:
            financial_year = f"{today.year - 1}-{today.year}"
        
        leave_types = LeaveType.objects.filter(is_active=True)
        
        for leave_type in leave_types:
            balance, created = EmployeeLeaveBalance.objects.get_or_create(
                employee=instance,
                leave_type=leave_type,
                financial_year=financial_year,
                defaults={
                    'opening_balance': leave_type.default_annual_allocation,
                    'accrued_days': 0,
                }
            )
            if created:
                balance.current_balance = balance.calculate_balance()
                balance.save(update_fields=['current_balance'])


@receiver(post_save, sender=LeaveApplication)
def update_leave_balance_on_approval(sender, instance, created, **kwargs):
    """
    When a leave application is approved, update the leave balance
    """
    if instance.approval_status == 'APPROVED':
        try:
            applied_date = instance.applied_date
            if applied_date.month >= 4:
                financial_year = f"{applied_date.year}-{applied_date.year + 1}"
            else:
                financial_year = f"{applied_date.year - 1}-{applied_date.year}"
            leave_balance = EmployeeLeaveBalance.objects.get(
                employee=instance.employee,
                leave_type=instance.leave_type,
                financial_year=financial_year
            )
            leave_balance.used_days += instance.number_of_days
            leave_balance.calculate_balance()
            leave_balance.save()
        except EmployeeLeaveBalance.DoesNotExist:
            pass


@receiver(pre_save, sender=Payroll)
def calculate_payroll_totals(sender, instance, **kwargs):
    """
    Auto-calculate payroll totals (this is a simplified version)
    In production, this would have complex logic for tax calculations
    """
    if not instance.net_salary or instance.net_salary == 0:
        # This will be calculated properly during payroll processing
        pass
