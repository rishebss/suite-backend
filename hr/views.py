from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta, date
from decimal import Decimal
import os
import mimetypes
import requests
import cloudinary.utils

from authentication.models import Department
from hr.models import (
    Employee, EmployeeDocument, Designation, WorkLocation, CostCenter,
    LeaveType, EmployeeLeaveBalance, LeaveApplication, Attendance,
    Shift, CompensatoryOff, SalaryComponent, SalaryStructure,
    SalaryStructureDetail, EmployeeSalary, Payroll, PayrollComponentDetail,
    Holiday,
    SalaryRevision, EmployeeLoan, LoanRepayment, EmployeeReimbursement,
    PFConfiguration, PFContribution, ESIConfiguration, ESIContribution,
    ProfessionalTaxSlab, PTContribution, TDSConfiguration,
    InvestmentDeclaration, TDSCalculation, GratuityConfiguration,
    GratuityCalculation, BonusConfiguration, BonusCalculation,
    ComplianceCalendarEntry,
    VPFContribution, PFStatement, ESICard, LowerDeductionCertificate,
    PTEnrollment, InternationalWorker, Form12BA, Form24QReturn,
    IPAccessRestriction
)
from hr.serializers import (
    DepartmentSerializer, DesignationSerializer, WorkLocationSerializer,
    CostCenterSerializer, ShiftSerializer, EmployeeListSerializer,
    EmployeeDetailSerializer, EmployeeDocumentSerializer, LeaveTypeSerializer,
    EmployeeLeaveBalanceSerializer, LeaveApplicationSerializer, AttendanceSerializer,
    CompensatoryOffSerializer, SalaryComponentSerializer, SalaryStructureSerializer,
    EmployeeSalarySerializer, PayrollSerializer, HolidaySerializer,
    SalaryRevisionSerializer, SalaryRevisionListSerializer,
    EmployeeLoanSerializer, EmployeeLoanListSerializer, LoanRepaymentSerializer,
    EmployeeReimbursementSerializer, EmployeeReimbursementListSerializer,
    PayrollProcessSerializer, PayrollApproveSerializer, BankFileSerializer,
    PayrollReportSerializer,
    PFConfigurationSerializer, PFContributionSerializer, ESIConfigurationSerializer,
    ESIContributionSerializer, ProfessionalTaxSlabSerializer, PTContributionSerializer,
    TDSConfigurationSerializer, InvestmentDeclarationSerializer, TDSCalculationSerializer,
    GratuityConfigurationSerializer, GratuityCalculationSerializer,
    BonusConfigurationSerializer, BonusCalculationSerializer,
    ComplianceCalendarEntrySerializer,
    VPFContributionSerializer, PFStatementSerializer, ESICardSerializer,
    LowerDeductionCertificateSerializer, PTEnrollmentSerializer,
    InternationalWorkerSerializer, Form12BASerializer, Form24QReturnSerializer,
    IPAccessRestrictionSerializer, DedupSerializer, BulkDedupSerializer
)
from hr.permissions import (
    IsHRAdmin, IsHRStaff, IsManagerOrHR, IsEmployeeOrHR,
    CanApproveLeave, CanProcessPayroll, CanViewAttendance, CanEditEmployeeData
)


# Import Payroll Engine
from hr.services.payroll_engine import (
    PayrollEngine, BatchPayrollProcessor,
    BankFileGenerator, PayrollReportGenerator
)
from hr.services.pdf_generation import PaySlipGenerator, Form16Generator, SalaryCertificateGenerator
from hr.services.notification_service import NotificationDispatcher
from hr.services.security_service import DataMaskingService, DedupService, IPAccessRestrictionService, DataRetentionService
from authentication.audit_logger import log_audit


# ============================================================================
# PAYROLL ENHANCEMENTS: SALARY REVISIONS, LOANS, REIMBURSEMENTS
# ============================================================================

class SalaryRevisionViewSet(viewsets.ModelViewSet):
    """ViewSet for Salary Revision management."""
    permission_classes = [IsAuthenticated, IsManagerOrHR]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'status', 'revision_type', 'effective_month', 'effective_year', 'is_processed']
    search_fields = ['employee__employee_id', 'employee__first_name', 'employee__last_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return SalaryRevisionListSerializer
        return SalaryRevisionSerializer

    def get_queryset(self):
        user = self.request.user
        base_qs = SalaryRevision.objects.select_related(
            'employee', 'recommended_by', 'approved_by_manager', 'approved_by_hr'
        )
        if user.role in ['Superadmin', 'Admin', 'Payroll Executive']:
            return base_qs.all()
        if user.role == 'Manager':
            try:
                employee = user.employee
                return base_qs.filter(employee__reporting_manager=employee)
            except:
                return base_qs.none()
        if user.role == 'Finance':
            return base_qs.all()
        return base_qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in ['Superadmin', 'Admin']:
            raise PermissionDenied('Only HR Admin can create salary revisions')
        revision = serializer.save(status='PENDING_MANAGER')
        if revision.previous_ctc and revision.revised_ctc:
            revision.percentage_increase = (
                (revision.revised_ctc - revision.previous_ctc) / revision.previous_ctc * Decimal('100')
            ).quantize(Decimal('0.01'))
            revision.save()

    def _is_manager_of_employee(self, revision):
        try:
            return self.request.user.employee == revision.employee.reporting_manager
        except:
            return False

    @action(detail=True, methods=['post'])
    def approve_manager(self, request, pk=None):
        """Manager approval for salary revision."""
        revision = self.get_object()
        if revision.status != 'PENDING_MANAGER':
            return Response({'error': 'Revision is not pending manager approval'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role not in ['Superadmin', 'Admin'] and not self._is_manager_of_employee(revision):
            return Response({'error': 'Only the employee\'s reporting manager can approve at this stage'}, status=status.HTTP_403_FORBIDDEN)
        revision.status = 'PENDING_HR'
        revision.approved_by_manager = request.user
        revision.save()
        return Response({'status': 'Manager approved'})

    @action(detail=True, methods=['post'])
    def approve_hr(self, request, pk=None):
        """HR approval for salary revision."""
        revision = self.get_object()
        if revision.status != 'PENDING_HR':
            return Response({'error': 'Revision is not pending HR approval'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role not in ['Superadmin', 'Admin']:
            return Response({'error': 'Only HR Admin can approve at this stage'}, status=status.HTTP_403_FORBIDDEN)
        revision.status = 'PENDING_FINANCE'
        revision.approved_by_hr = request.user
        revision.save()
        return Response({'status': 'HR approved'})

    @action(detail=True, methods=['post'])
    def approve_finance(self, request, pk=None):
        """Finance approval for salary revision."""
        revision = self.get_object()
        if revision.status != 'PENDING_FINANCE':
            return Response({'error': 'Revision is not pending finance approval'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role not in ['Superadmin', 'Admin', 'Finance']:
            return Response({'error': 'Only Finance can approve at this stage'}, status=status.HTTP_403_FORBIDDEN)
        revision.status = 'APPROVED'
        revision.approved_by_finance = request.user
        revision.approved_date = timezone.now()
        revision.save()

        from hr.models import EmployeeSalary
        old_salary = EmployeeSalary.objects.filter(employee=revision.employee, is_active=True).order_by('-effective_from').first()
        if old_salary:
            old_salary.is_active = False
            old_salary.effective_to = date(revision.effective_year, revision.effective_month, 1) - timedelta(days=1)
            old_salary.save()

        EmployeeSalary.objects.create(
            employee=revision.employee,
            salary_structure=old_salary.salary_structure if old_salary else None,
            ctc=revision.revised_ctc,
            gross_salary=revision.revised_gross,
            net_salary=revision.revised_gross - (old_salary.gross_salary - old_salary.net_salary if old_salary else Decimal('0')),
            basic_salary=revision.revised_basic,
            effective_from=date(revision.effective_year, revision.effective_month, 1),
            previous_salary=old_salary,
            is_active=True,
        )

        return Response({'status': 'Finance approved — salary updated'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject salary revision."""
        revision = self.get_object()
        if revision.status not in ['DRAFT', 'PENDING_MANAGER', 'PENDING_HR', 'PENDING_FINANCE']:
            return Response({'error': 'Revision is not pending approval'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role not in ['Superadmin', 'Admin', 'Finance'] and not self._is_manager_of_employee(revision):
            return Response({'error': 'Not authorized to reject this revision'}, status=status.HTTP_403_FORBIDDEN)
        revision.status = 'REJECTED'
        revision.notes = request.data.get('reason', revision.notes or '')
        revision.save()
        return Response({'status': 'Revision rejected'})

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get revisions pending approval (role-filtered)."""
        user = request.user
        qs = self.get_queryset()
        if user.role in ['Superadmin', 'Admin', 'Payroll Executive']:
            qs = qs.filter(status__in=['PENDING_MANAGER', 'PENDING_HR', 'PENDING_FINANCE'])
        elif user.role == 'Manager':
            qs = qs.filter(status='PENDING_MANAGER')
        elif user.role == 'Finance':
            qs = qs.filter(status='PENDING_FINANCE')
        else:
            qs = qs.none()
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class EmployeeLoanViewSet(viewsets.ModelViewSet):
    """ViewSet for Employee Loan management."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'loan_type', 'status', 'is_active']
    search_fields = ['employee__employee_id', 'employee__first_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeLoanListSerializer
        return EmployeeLoanSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return EmployeeLoan.objects.select_related('employee').all()
        try:
            employee = user.employee
            return EmployeeLoan.objects.filter(employee=employee).select_related('employee')
        except:
            return EmployeeLoan.objects.none()

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def approve(self, request, pk=None):
        """Approve a loan."""
        loan = self.get_object()
        if loan.status != 'PENDING':
            return Response({'error': 'Loan is not in pending status'}, status=status.HTTP_400_BAD_REQUEST)
        loan.status = 'APPROVED'
        loan.approved_by = request.user
        loan.approved_date = timezone.now()
        loan.save()
        return Response({'status': 'Loan approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def reject(self, request, pk=None):
        """Reject a loan."""
        loan = self.get_object()
        if loan.status != 'PENDING':
            return Response({'error': 'Loan is not in pending status'}, status=status.HTTP_400_BAD_REQUEST)
        loan.status = 'REJECTED'
        loan.purpose = request.data.get('reason', loan.purpose or '')
        loan.save()
        return Response({'status': 'Loan rejected'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def close(self, request, pk=None):
        """Close a loan (mark as fully paid)."""
        loan = self.get_object()
        loan.status = 'CLOSED'
        loan.closure_date = timezone.now().date()
        loan.outstanding_amount = Decimal('0')
        loan.is_active = False
        loan.save()
        return Response({'status': 'Loan closed'})

    @action(detail=False, methods=['get'])
    def my_loans(self, request):
        """Get current user's loans."""
        try:
            employee = request.user.employee
            loans = EmployeeLoan.objects.filter(employee=employee).select_related('employee')
            serializer = EmployeeLoanListSerializer(loans, many=True)
            return Response(serializer.data)
        except:
            return Response([], status=status.HTTP_200_OK)


class LoanRepaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing loan repayments."""
    serializer_class = LoanRepaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['loan', 'month', 'year', 'is_processed']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return LoanRepayment.objects.select_related('loan__employee').all()
        try:
            employee = user.employee
            return LoanRepayment.objects.filter(loan__employee=employee).select_related('loan__employee')
        except:
            return LoanRepayment.objects.none()


class EmployeeReimbursementViewSet(viewsets.ModelViewSet):
    """ViewSet for Employee Reimbursement management."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'expense_type', 'status']
    search_fields = ['employee__employee_id', 'description']

    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeReimbursementListSerializer
        return EmployeeReimbursementSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return EmployeeReimbursement.objects.select_related('employee', 'approved_by').all()
        try:
            employee = user.employee
            return EmployeeReimbursement.objects.filter(employee=employee).select_related('employee', 'approved_by')
        except:
            return EmployeeReimbursement.objects.none()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def approve(self, request, pk=None):
        """Approve a reimbursement."""
        reimbursement = self.get_object()
        if reimbursement.status != 'PENDING':
            return Response({'error': 'Reimbursement is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        reimbursement.status = 'APPROVED'
        reimbursement.approved_by = request.user
        reimbursement.approved_date = timezone.now()
        reimbursement.save()
        return Response({'status': 'Reimbursement approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def reject(self, request, pk=None):
        """Reject a reimbursement."""
        reimbursement = self.get_object()
        if reimbursement.status != 'PENDING':
            return Response({'error': 'Reimbursement is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        reimbursement.status = 'REJECTED'
        reimbursement.notes = request.data.get('reason', reimbursement.notes or '')
        reimbursement.save()
        return Response({'status': 'Reimbursement rejected'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsHRStaff])
    def mark_paid(self, request, pk=None):
        """Mark reimbursement as paid."""
        reimbursement = self.get_object()
        if reimbursement.status != 'APPROVED':
            return Response({'error': 'Reimbursement is not approved'}, status=status.HTTP_400_BAD_REQUEST)
        reimbursement.status = 'PAID'
        reimbursement.paid_date = timezone.now().date()
        reimbursement.save()
        return Response({'status': 'Reimbursement marked as paid'})

    @action(detail=False, methods=['get'])
    def my_reimbursements(self, request):
        """Get current user's reimbursements."""
        try:
            employee = request.user.employee
            reimbursements = EmployeeReimbursement.objects.filter(employee=employee)
            serializer = EmployeeReimbursementListSerializer(reimbursements, many=True)
            return Response(serializer.data)
        except:
            return Response([])


# ============================================================================
# MASTER DATA VIEWSETS
# ============================================================================

class DesignationViewSet(viewsets.ModelViewSet):
    """ViewSet for Designation master"""
    queryset = Designation.objects.filter(is_active=True)
    serializer_class = DesignationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'grade', 'is_active']
    search_fields = ['name', 'code']


class WorkLocationViewSet(viewsets.ModelViewSet):
    """ViewSet for Work Location master"""
    queryset = WorkLocation.objects.filter(is_active=True)
    serializer_class = WorkLocationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['state', 'city', 'is_active']
    search_fields = ['name', 'code', 'city']


class CostCenterViewSet(viewsets.ModelViewSet):
    """ViewSet for Cost Center master"""
    queryset = CostCenter.objects.filter(is_active=True)
    serializer_class = CostCenterSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'is_active']
    search_fields = ['name', 'code']


class ShiftViewSet(viewsets.ModelViewSet):
    """ViewSet for Shift master"""
    queryset = Shift.objects.filter(is_active=True)
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['shift_type', 'is_rotating', 'is_active']
    search_fields = ['name', 'code']


# ============================================================================
# EMPLOYEE MANAGEMENT VIEWSET
# ============================================================================

class EmployeeViewSet(viewsets.ModelViewSet):
    """ViewSet for Employee Master"""
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'designation', 'status', 'employment_type', 'work_location']
    search_fields = ['employee_id', 'first_name', 'last_name', 'personal_email', 'pan_number']

    def get_queryset(self):
        """Filter based on user role"""
        if self.request.user.role in ['Superadmin', 'Admin']:
            return Employee.objects.all().select_related(
                'department', 'designation', 'work_location', 'reporting_manager', 'user'
            )
        elif self.request.user.role == 'Manager':
            try:
                employee = self.request.user.employee
                # Manager sees their own team
                return Employee.objects.filter(
                    reporting_manager=employee
                ).select_related(
                    'department', 'designation', 'work_location', 'reporting_manager', 'user'
                )
            except:
                return Employee.objects.none()
        else:
            # Regular employees see only their own record
            try:
                return Employee.objects.filter(user=self.request.user)
            except:
                return Employee.objects.none()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EmployeeDetailSerializer
        return EmployeeListSerializer

    def perform_create(self, serializer):
        """Log employee creation."""
        instance = serializer.save()
        log_audit(
            user=self.request.user,
            action='employee_create',
            action_target=instance.user if instance.user else None,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            details={
                'employee_id': instance.employee_id,
                'employee_name': instance.get_full_name(),
                'department': str(instance.department.name) if instance.department else None,
            }
        )

    def perform_update(self, serializer):
        """Log employee field-level changes."""
        old_instance = self.get_object()
        old_data = {
            'first_name': old_instance.first_name,
            'last_name': old_instance.last_name,
            'personal_email': old_instance.personal_email,
            'personal_mobile': old_instance.personal_mobile,
            'department': str(old_instance.department.name) if old_instance.department else None,
            'designation': str(old_instance.designation.name) if old_instance.designation else None,
            'status': old_instance.status,
            'reporting_manager': str(old_instance.reporting_manager.get_full_name()) if old_instance.reporting_manager else None,
            'work_location': str(old_instance.work_location.name) if old_instance.work_location else None,
            'current_pin_code': old_instance.current_pin_code,
            'permanent_pin_code': old_instance.permanent_pin_code,
            'aadhaar_number': old_instance.aadhaar_number,
            'pan_number': old_instance.pan_number,
            'bank_account_number': old_instance.bank_account_number,
            'bank_name': old_instance.bank_name,
            'ifsc_code': old_instance.ifsc_code,
            'employment_type': old_instance.employment_type,
            'grade': old_instance.grade,
            'work_shift': old_instance.work_shift,
        }
        
        instance = serializer.save()
        new_data = {
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'personal_email': instance.personal_email,
            'personal_mobile': instance.personal_mobile,
            'department': str(instance.department.name) if instance.department else None,
            'designation': str(instance.designation.name) if instance.designation else None,
            'status': instance.status,
            'reporting_manager': str(instance.reporting_manager.get_full_name()) if instance.reporting_manager else None,
            'work_location': str(instance.work_location.name) if instance.work_location else None,
            'current_pin_code': instance.current_pin_code,
            'permanent_pin_code': instance.permanent_pin_code,
            'aadhaar_number': instance.aadhaar_number,
            'pan_number': instance.pan_number,
            'bank_account_number': instance.bank_account_number,
            'bank_name': instance.bank_name,
            'ifsc_code': instance.ifsc_code,
            'employment_type': instance.employment_type,
            'grade': instance.grade,
            'work_shift': instance.work_shift,
        }
        
        # Track which fields changed
        changes = {}
        for field in old_data:
            if old_data[field] != new_data[field]:
                changes[field] = {'old': old_data[field], 'new': new_data[field]}
        
        if changes:
            log_audit(
                user=self.request.user,
                action='employee_update',
                action_target=instance.user if instance.user else None,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                target_changes=changes,
                details={
                    'employee_id': instance.employee_id,
                    'employee_name': instance.get_full_name(),
                }
            )

    @action(detail=False, methods=['get'])
    def by_department(self, request):
        """Get employees filtered by department"""
        department_id = request.query_params.get('department_id')
        if department_id:
            from django.core.exceptions import ValidationError
            try:
                employees = self.get_queryset().filter(department_id=department_id)
                serializer = self.get_serializer(employees, many=True)
                return Response(serializer.data)
            except (ValidationError, ValueError):
                return Response(
                    {'error': 'Invalid department_id format. Expected a valid UUID.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response({'error': 'department_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_location(self, request):
        """Get employees filtered by location"""
        location_id = request.query_params.get('location_id')
        if location_id:
            from django.core.exceptions import ValidationError
            try:
                employees = self.get_queryset().filter(work_location_id=location_id)
                serializer = self.get_serializer(employees, many=True)
                return Response(serializer.data)
            except (ValidationError, ValueError):
                return Response(
                    {'error': 'Invalid location_id format. Expected a valid UUID.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response({'error': 'location_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def active_count(self, request):
        """Get count of active employees"""
        count = self.get_queryset().filter(status='ACTIVE').count()
        return Response({'active_employees': count})

    @action(detail=False, methods=['get'])
    def by_grade(self, request):
        """Get employees by grade"""
        grade = request.query_params.get('grade')
        if grade:
            employees = self.get_queryset().filter(grade=grade)
            serializer = self.get_serializer(employees, many=True)
            return Response(serializer.data)
        return Response({'error': 'grade parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def confirm_probation(self, request, pk=None):
        """Confirm employee after probation"""
        employee = self.get_object()
        if employee.status != 'ONBOARDING':
            return Response(
                {'error': 'Only onboarding employees can be confirmed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        employee.status = 'ACTIVE'
        employee.confirmation_date = timezone.now().date()
        employee.save()
        
        return Response(
            {'status': 'Employee confirmed', 'confirmation_date': employee.confirmation_date},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def initiate_separation(self, request, pk=None):
        """Initiate employee separation"""
        employee = self.get_object()
        reason = request.data.get('reason')
        separation_date = request.data.get('separation_date')

        if not reason or not separation_date:
            return Response(
                {'error': 'reason and separation_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        employee.status = 'NOTICE_PERIOD'
        employee.separation_reason = reason
        employee.separation_date = separation_date
        employee.save()

        return Response({'status': 'Separation initiated'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """
        Export all employees (filtered by query params) as CSV.
        Returns all employee fields in CSV format for bulk export.
        """
        import csv
        employees = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="employees_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        # Header row
        writer.writerow([
            'employee_id', 'first_name', 'middle_name', 'last_name',
            'personal_email', 'official_email', 'personal_mobile',
            'date_of_birth', 'gender', 'marital_status', 'blood_group', 'nationality',
            'current_address', 'current_city', 'current_state', 'current_country', 'current_pin_code',
            'permanent_address', 'permanent_city', 'permanent_state', 'permanent_country', 'permanent_pin_code',
            'aadhaar_number', 'pan_number', 'bank_account_number', 'bank_name', 'ifsc_code',
            'department', 'designation', 'work_location', 'employment_type',
            'date_of_joining', 'status', 'notice_period_days', 'grade', 'band',
            'work_shift', 'reporting_manager', 'cost_center',
        ])
        
        for emp in employees:
            writer.writerow([
                emp.employee_id,
                emp.first_name,
                emp.middle_name or '',
                emp.last_name,
                emp.personal_email,
                emp.official_email or '',
                emp.personal_mobile,
                emp.date_of_birth.isoformat() if emp.date_of_birth else '',
                emp.gender,
                emp.marital_status or '',
                emp.blood_group or '',
                emp.nationality or '',
                emp.current_address or '',
                emp.current_city or '',
                emp.current_state or '',
                emp.current_country or '',
                emp.current_pin_code or '',
                emp.permanent_address or '',
                emp.permanent_city or '',
                emp.permanent_state or '',
                emp.permanent_country or '',
                emp.permanent_pin_code or '',
                emp.aadhaar_number or '',
                emp.pan_number or '',
                emp.bank_account_number or '',
                emp.bank_name or '',
                emp.ifsc_code or '',
                emp.department.name if emp.department else '',
                emp.designation.name if emp.designation else '',
                emp.work_location.name if emp.work_location else '',
                emp.employment_type or '',
                emp.status,
                emp.notice_period_days,
                emp.grade or '',
                emp.band or '',
                emp.work_shift or '',
                emp.reporting_manager.get_full_name() if emp.reporting_manager else '',
                emp.cost_center.name if emp.cost_center else '',
            ])
        
        return response

    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        """
        Bulk import employees from CSV upload.
        
        Accepts a CSV file with headers matching employee fields.
        Required columns: first_name, last_name, personal_email, date_of_joining, gender
        Returns summary of created vs failed records.
        """
        import csv
        import io
        
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'CSV file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            decoded_file = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded_file))
        except Exception as e:
            return Response({'error': f'Invalid CSV file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        required_fields = ['first_name', 'last_name', 'personal_email', 'date_of_joining', 'gender']
        if not reader.fieldnames:
            return Response({'error': 'CSV file has no headers'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate required columns exist
        missing_fields = [f for f in required_fields if f not in reader.fieldnames]
        if missing_fields:
            return Response({
                'error': f'Missing required columns: {missing_fields}',
                'required': required_fields,
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from hr.models import Designation, WorkLocation
        
        created_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):
            try:
                # Validate required fields
                if not row.get('first_name') or not row.get('last_name') or not row.get('personal_email'):
                    errors.append(f'Row {row_num}: Missing required fields (first_name, last_name, personal_email)')
                    error_count += 1
                    continue
                
                # Check for duplicate email
                if Employee.objects.filter(personal_email=row['personal_email']).exists():
                    errors.append(f'Row {row_num}: Duplicate email {row["personal_email"]}')
                    error_count += 1
                    continue
                
                # Parse optional FK fields
                designation = None
                if row.get('designation'):
                    designation = Designation.objects.filter(name__iexact=row['designation']).first()
                
                work_location = None
                if row.get('work_location'):
                    work_location = WorkLocation.objects.filter(name__iexact=row['work_location']).first()
                
                # Parse date
                from datetime import date as dt_date
                try:
                    doj = dt_date.fromisoformat(row['date_of_joining'])
                except (ValueError, KeyError):
                    doj = date.today()
                
                employee = Employee(
                    first_name=row['first_name'],
                    middle_name=row.get('middle_name', ''),
                    last_name=row['last_name'],
                    personal_email=row['personal_email'],
                    official_email=row.get('official_email', ''),
                    personal_mobile=row.get('personal_mobile', ''),
                    date_of_birth=dt_date.fromisoformat(row.get('date_of_birth', '1990-01-01')),
                    gender=row.get('gender', 'MALE'),
                    marital_status=row.get('marital_status', 'SINGLE'),
                    blood_group=row.get('blood_group', ''),
                    nationality=row.get('nationality', 'Indian'),
                    current_address=row.get('current_address', ''),
                    current_city=row.get('current_city', ''),
                    current_state=row.get('current_state', ''),
                    current_country=row.get('current_country', 'India'),
                    current_pin_code=row.get('current_pin_code', '000000'),
                    permanent_address=row.get('permanent_address', ''),
                    permanent_city=row.get('permanent_city', ''),
                    permanent_state=row.get('permanent_state', ''),
                    permanent_country=row.get('permanent_country', 'India'),
                    permanent_pin_code=row.get('permanent_pin_code', '000000'),
                    aadhaar_number=row.get('aadhaar_number'),
                    pan_number=row.get('pan_number'),
                    bank_account_number=row.get('bank_account_number'),
                    bank_name=row.get('bank_name'),
                    ifsc_code=row.get('ifsc_code'),
                    employment_type=row.get('employment_type', 'PERMANENT'),
                    date_of_joining=doj,
                    status=row.get('status', 'ACTIVE'),
                    notice_period_days=int(row.get('notice_period_days', 30)),
                    grade=row.get('grade', ''),
                    band=row.get('band', ''),
                    work_shift=row.get('work_shift', 'GENERAL'),
                    designation=designation,
                    work_location=work_location,
                )
                employee.save()
                created_count += 1
                
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
                error_count += 1
        
        return Response({
            'created': created_count,
            'errors': error_count,
            'total': created_count + error_count,
            'error_details': errors[:50],
        })

    @action(detail=False, methods=['post'])
    def check_duplicates(self, request):
        """
        Check for potential duplicate employee records before creating.
        Accepts employee data and returns possible matches across Aadhaar, PAN, email, mobile.
        """
        serializer = DedupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        results = DedupService.check_duplicates(serializer.validated_data)
        
        return Response({
            'has_potential_duplicates': len(results) > 0,
            'matches': results,
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsHRAdmin])
    def bulk_dedup_check(self, request):
        """
        Run bulk dedup check across all or specified employees.
        Returns groups of potential duplicates.
        """
        serializer = BulkDedupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        results = DedupService.bulk_dedup_check(serializer.validated_data.get('employee_ids'))
        
        return Response(results)


class EmployeeDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Employee Documents"""
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [IsAuthenticated, IsEmployeeOrHR]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'document_type', 'is_verified']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return EmployeeDocument.objects.all()
        else:
            try:
                employee = user.employee
                return EmployeeDocument.objects.filter(employee=employee)
            except:
                return EmployeeDocument.objects.none()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a document"""
        document = self.get_object()
        document.is_verified = True
        document.verified_by = request.user
        document.verified_date = timezone.now()
        document.save()

        return Response({'status': 'Document verified'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        document = self.get_object()
        name = document.document_file.name
        ext = os.path.splitext(name)[1] or ''
        content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        filename = f"{document.document_type}_{document.employee.employee_id}{ext}"

        download_url = cloudinary.utils.private_download_url(
            name,
            '',
            type='upload',
            resource_type='raw',
            attachment=True,
            expires_at=9999999999,
        )
        resp = requests.get(download_url, allow_redirects=True)
        resp.raise_for_status()

        response = HttpResponse(resp.content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(resp.content)
        return response


# ============================================================================
# ATTENDANCE & LEAVE VIEWSETS
# ============================================================================

class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Leave Types (Read-only)"""
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]


class EmployeeLeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Employee Leave Balances"""
    serializer_class = EmployeeLeaveBalanceSerializer
    permission_classes = [IsAuthenticated, IsEmployeeOrHR]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'leave_type', 'financial_year']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return EmployeeLeaveBalance.objects.select_related('employee', 'leave_type')
        else:
            try:
                employee = user.employee
                return EmployeeLeaveBalance.objects.filter(employee=employee).select_related(
                    'employee', 'leave_type'
                )
            except:
                return EmployeeLeaveBalance.objects.none()

    @action(detail=False, methods=['get'])
    def current_year(self, request):
        """Get leave balances for current financial year for the logged-in employee"""
        today = datetime.now()
        if today.month >= 4:
            financial_year = f"{today.year}-{today.year + 1}"
        else:
            financial_year = f"{today.year - 1}-{today.year}"

        try:
            employee = request.user.employee
        except Exception:
            return Response([])
        
        balances = EmployeeLeaveBalance.objects.filter(
            employee=employee, financial_year=financial_year
        ).select_related('leave_type')
        serializer = self.get_serializer(balances, many=True)
        return Response(serializer.data)


class LeaveApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for Leave Applications"""
    serializer_class = LeaveApplicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'leave_type', 'approval_status']
    search_fields = ['employee__first_name', 'employee__last_name']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return LeaveApplication.objects.all().select_related(
                'employee', 'leave_type', 'approval_manager'
            )
        elif user.role == 'Manager':
            try:
                employee = user.employee
                return LeaveApplication.objects.filter(
                    employee__reporting_manager=employee
                ).select_related('employee', 'leave_type', 'approval_manager')
            except:
                return LeaveApplication.objects.none()
        else:
            try:
                employee = user.employee
                return LeaveApplication.objects.filter(employee=employee).select_related(
                    'employee', 'leave_type', 'approval_manager'
                )
            except:
                return LeaveApplication.objects.none()

    def _current_financial_year(self, target_date=None):
        if target_date is None:
            target_date = timezone.now().date()
        if target_date.month >= 4:
            return f"{target_date.year}-{target_date.year + 1}"
        return f"{target_date.year - 1}-{target_date.year}"

    def _get_leave_balance(self, employee, leave_type, financial_year):
        balance, _ = EmployeeLeaveBalance.objects.get_or_create(
            employee=employee,
            leave_type=leave_type,
            financial_year=financial_year,
            defaults={
                'opening_balance': 0,
                'current_balance': 0,
            }
        )
        return balance

    def _reconcile_balance_on_status_change(self, leave_application, restore=False):
        financial_year = self._current_financial_year(leave_application.date_from)
        leave_balance = self._get_leave_balance(
            leave_application.employee,
            leave_application.leave_type,
            financial_year
        )

        if restore:
            if leave_application.approval_status == 'APPROVED':
                leave_balance.used_days = max(leave_balance.used_days - leave_application.number_of_days, 0)
            leave_balance.pending_days = max(leave_balance.pending_days - leave_application.number_of_days, 0)
        else:
            if leave_application.approval_status == 'PENDING':
                leave_balance.pending_days += leave_application.number_of_days
            elif leave_application.approval_status == 'APPROVED':
                leave_balance.pending_days = max(leave_balance.pending_days - leave_application.number_of_days, 0)
                leave_balance.used_days += leave_application.number_of_days
            elif leave_application.approval_status == 'REJECTED':
                leave_balance.pending_days = max(leave_balance.pending_days - leave_application.number_of_days, 0)

        leave_balance.calculate_balance()
        leave_balance.save()
        return leave_balance

    def create(self, request, *args, **kwargs):
        """Create new leave application"""
        try:
            employee = request.user.employee
        except:
            return Response(
                {'error': 'User is not an employee'},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data.copy()
        data['employee'] = employee.id

        if not data.get('number_of_days') and data.get('date_from') and data.get('date_to'):
            try:
                from datetime import date
                date_from = datetime.fromisoformat(data['date_from']).date()
                date_to = datetime.fromisoformat(data['date_to']).date()
                data['number_of_days'] = (date_to - date_from).days + 1
            except Exception:
                pass

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        leave_application = serializer.save()

        if leave_application.leave_type is not None:
            balance = self._get_leave_balance(
                employee,
                leave_application.leave_type,
                self._current_financial_year(leave_application.date_from)
            )
            balance.pending_days += leave_application.number_of_days
            if not leave_application.leave_type.can_go_negative and balance.pending_days + balance.used_days > balance.opening_balance + balance.accrued_days:
                leave_application.delete()
                return Response(
                    {'error': 'Insufficient leave balance for this application'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            balance.calculate_balance()
            balance.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanApproveLeave])
    def approve(self, request, pk=None):
        """Approve leave application"""
        leave_application = self.get_object()
        if leave_application.approval_status != 'PENDING':
            return Response(
                {'error': 'Only pending leaves can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_application.approval_status = 'APPROVED'
        leave_application.approval_manager = request.user
        leave_application.approval_date = timezone.now()
        leave_application.approval_comment = request.data.get('comment', '')
        leave_application.save()

        self._reconcile_balance_on_status_change(leave_application)

        # Send notification
        try:
            NotificationDispatcher.on_leave_status_change(leave_application)
        except Exception:
            pass

        return Response({'status': 'Leave approved'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanApproveLeave])
    def reject(self, request, pk=None):
        """Reject leave application"""
        leave_application = self.get_object()
        if leave_application.approval_status != 'PENDING':
            return Response(
                {'error': 'Only pending leaves can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_application.approval_status = 'REJECTED'
        leave_application.approval_manager = request.user
        leave_application.approval_date = timezone.now()
        leave_application.approval_comment = request.data.get('comment', '')
        leave_application.save()

        self._reconcile_balance_on_status_change(leave_application)

        # Send notification
        try:
            NotificationDispatcher.on_leave_status_change(leave_application)
        except Exception:
            pass

        return Response({'status': 'Leave rejected'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel leave application"""
        leave_application = self.get_object()
        
        if leave_application.employee.user != request.user and request.user.role not in ['Superadmin', 'Admin']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if leave_application.is_cancelled:
            return Response(
                {'error': 'Leave already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_application.is_cancelled = True
        leave_application.cancelled_by = request.user
        leave_application.cancelled_date = timezone.now()
        leave_application.cancellation_reason = request.data.get('reason', '')
        leave_application.approval_status = 'CANCELLED'
        leave_application.save()

        self._reconcile_balance_on_status_change(leave_application, restore=True)

        return Response({'status': 'Leave cancelled'}, status=status.HTTP_200_OK)


class AttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Attendance Records"""
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, CanViewAttendance]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'date', 'status']
    search_fields = ['employee__first_name', 'employee__last_name']

    def get_queryset(self):
        user = self.request.user
        qs = self._base_queryset(user)
        month = self.request.query_params.get('date__month') if self.request else None
        year = self.request.query_params.get('date__year') if self.request else None
        if month and year:
            qs = qs.filter(date__month=month, date__year=year)
        return qs

    def _base_queryset(self, user=None):
        if user is None:
            user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return Attendance.objects.select_related('employee', 'regularized_by')
        elif user.role == 'Manager':
            try:
                employee = user.employee
                return Attendance.objects.filter(
                    employee__reporting_manager=employee
                ).select_related('employee', 'regularized_by')
            except:
                return Attendance.objects.none()
        else:
            try:
                employee = user.employee
                return Attendance.objects.filter(employee=employee).select_related(
                    'employee', 'regularized_by'
                )
            except:
                return Attendance.objects.none()

    def create(self, request, *args, **kwargs):
        """Create attendance if not already recorded for the employee/date"""
        try:
            employee = request.user.employee
        except Exception:
            return Response({'error': 'User is not an employee'}, status=status.HTTP_400_BAD_REQUEST)

        date_str = request.data.get('date')
        if not date_str:
            return Response({'error': 'date is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attendance_date = datetime.fromisoformat(date_str).date()
        except Exception:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=attendance_date,
            defaults={
                'check_in_time': request.data.get('check_in_time'),
                'check_in_location': request.data.get('check_in_location'),
                'status': request.data.get('status', 'PRESENT'),
                'shift': request.data.get('shift', employee.work_shift or 'GENERAL'),
                'remarks': request.data.get('remarks', ''),
            }
        )

        if not created:
            return Response(
                {'error': 'Attendance already exists for this date', 'id': attendance.id},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get attendance for today"""
        today = timezone.now().date()
        attendance = self._base_queryset().filter(date=today)
        serializer = self.get_serializer(attendance, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """Get monthly attendance report"""
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not month or not year:
            return Response(
                {'error': 'month and year parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        attendance = self._base_queryset().filter(date__month=month, date__year=year)
        
        report_data = {
            'month': month,
            'year': year,
            'present_days': attendance.filter(status='PRESENT').count(),
            'absent_days': attendance.filter(status='ABSENT').count(),
            'half_day_count': attendance.filter(status='HALF_DAY').count(),
            'wfh_days': attendance.filter(status='WFH').count(),
        }

        return Response(report_data)

    @action(detail=True, methods=['post'])
    def regularize(self, request, pk=None):
        """Regularize attendance"""
        attendance = self.get_object()
        if attendance.is_regularized:
            return Response(
                {'error': 'Attendance already regularized'},
                status=status.HTTP_400_BAD_REQUEST
            )

        attendance.is_regularized = True
        attendance.regularized_by = request.user
        attendance.regularization_reason = request.data.get('reason', '')
        attendance.save()

        return Response({'status': 'Attendance regularized'}, status=status.HTTP_200_OK)


class CompensatoryOffViewSet(viewsets.ModelViewSet):
    """ViewSet for Compensatory Off"""
    serializer_class = CompensatoryOffSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return CompensatoryOff.objects.select_related('employee')
        else:
            try:
                employee = user.employee
                return CompensatoryOff.objects.filter(employee=employee)
            except:
                return CompensatoryOff.objects.none()


# ============================================================================
# PAYROLL VIEWSETS
# ============================================================================

class SalaryComponentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Salary Components (Read-only)"""
    queryset = SalaryComponent.objects.filter(is_active=True)
    serializer_class = SalaryComponentSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']


class SalaryStructureViewSet(viewsets.ModelViewSet):
    """ViewSet for Salary Structures"""
    queryset = SalaryStructure.objects.filter(is_active=True)
    serializer_class = SalaryStructureSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['grade', 'band', 'designation']
    search_fields = ['name', 'code']


class EmployeeSalaryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Employee Salary (Read-only for employees)"""
    serializer_class = EmployeeSalarySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'is_active']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return EmployeeSalary.objects.select_related('employee', 'salary_structure')
        elif user.role == 'Manager':
            try:
                employee = user.employee
                return EmployeeSalary.objects.filter(
                    employee__reporting_manager=employee
                ).select_related('employee', 'salary_structure')
            except:
                return EmployeeSalary.objects.none()
        else:
            try:
                employee = user.employee
                return EmployeeSalary.objects.filter(employee=employee).select_related(
                    'employee', 'salary_structure'
                )
            except:
                return EmployeeSalary.objects.none()


class PayrollViewSet(viewsets.ModelViewSet):
    """
    Enhanced ViewSet for Payroll with engine-based processing.
    Supports:
    - Engine-based salary calculation with attendance integration
    - Statutory deductions (PF, ESI, PT, TDS)
    - Salary revision arrears
    - Loan EMI deductions
    - Test mode (parallel run)
    - Reports generation
    - Bank file generation
    """
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated, CanProcessPayroll]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'month', 'year', 'status']
    search_fields = ['employee__employee_id', 'payroll_period']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin', 'Payroll Executive']:
            return Payroll.objects.select_related(
                'employee', 'processed_by', 'approved_by'
            ).prefetch_related('components')
        else:
            return Payroll.objects.none()

    def get_permissions(self):
        if self.action in ['my_payslips', 'payslip', 'download_payslip']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def _get_payslip_payroll(self, request, pk):
        """
        Fetch a payroll record for payslip viewing, allowing payroll admins
        to view anyone's and employees to view only their own.
        """
        payroll = Payroll.objects.select_related('employee').filter(pk=pk).first()
        if not payroll:
            return None

        if request.user.role in ['Superadmin', 'Admin', 'Payroll Executive']:
            return payroll

        employee = getattr(request.user, 'employee', None)
        if not employee or payroll.employee_id != employee.id:
            raise PermissionDenied('You may only view your own payslip.')
        return payroll

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanProcessPayroll])
    def process_payroll(self, request):
        """
        Process payroll using the PayrollEngine.
        Supports test mode for parallel runs before live processing.
        """
        serializer = PayrollProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        month = serializer.validated_data['month']
        year = serializer.validated_data['year']
        is_test_mode = serializer.validated_data.get('test_mode', False)
        
        filters = {}
        if serializer.validated_data.get('department'):
            filters['department'] = serializer.validated_data['department']
        if serializer.validated_data.get('location'):
            filters['location'] = serializer.validated_data['location']
        
        processor = BatchPayrollProcessor(month, year, filters)
        results = processor.process_all(request.user, is_test_mode=is_test_mode)
        
        return Response(results, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanProcessPayroll])
    def process_single(self, request):
        """
        Process payroll for a single employee.
        """
        employee_id = request.data.get('employee_id')
        month = request.data.get('month')
        year = request.data.get('year')
        is_test_mode = request.data.get('test_mode', False)
        
        if not all([employee_id, month, year]):
            return Response(
                {'error': 'employee_id, month, and year are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            employee = Employee.objects.get(id=employee_id)
            month = int(month)
            year = int(year)
        except (Employee.DoesNotExist, ValueError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            engine = PayrollEngine(employee, month, year)
            result = engine.process(request.user, is_test_mode=is_test_mode)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanProcessPayroll])
    def process_all(self, request):
        """
        Process payroll for ALL eligible employees (convenience endpoint).
        """
        serializer = PayrollProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        month = serializer.validated_data['month']
        year = serializer.validated_data['year']
        is_test_mode = serializer.validated_data.get('test_mode', False)
        
        processor = BatchPayrollProcessor(month, year)
        results = processor.process_all(request.user, is_test_mode=is_test_mode)
        
        return Response(results, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanProcessPayroll])
    def approve(self, request, pk=None):
        """Approve a single payroll record."""
        payroll = self.get_object()
        if payroll.status not in ['PROCESSED', 'DRAFT']:
            return Response(
                {'error': 'Only processed payroll can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payroll.status = 'APPROVED'
        payroll.approved_by = request.user
        payroll.approved_date = timezone.now()
        payroll.save()

        # Send notification
        try:
            NotificationDispatcher.on_payroll_approved(payroll)
        except Exception:
            pass

        return Response({'status': 'Payroll approved'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def download_payslip(self, request, pk=None):
        """Download payslip as PDF."""
        payroll = self._get_payslip_payroll(request, pk)
        if not payroll:
            return Response({'error': 'Payroll not found'}, status=status.HTTP_404_NOT_FOUND)
        generator = PaySlipGenerator(payroll)
        return generator.generate_response()

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanProcessPayroll])
    def bulk_approve(self, request):
        """
        Approve multiple payroll records at once.
        Accepts list of payroll IDs or approves all PROCESSED records for a period.
        """
        serializer = PayrollApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ids = serializer.validated_data.get('ids', [])
        all_employees = serializer.validated_data.get('all_employees', False)
        remarks = serializer.validated_data.get('remarks', '')
        
        if all_employees:
            updated = Payroll.objects.filter(status='PROCESSED').update(
                status='APPROVED',
                approved_by=request.user,
                approved_date=timezone.now(),
            )
            return Response({'status': f'{updated} payroll records approved'})
        
        if ids:
            updated = Payroll.objects.filter(id__in=ids, status='PROCESSED').update(
                status='APPROVED',
                approved_by=request.user,
                approved_date=timezone.now(),
            )
            return Response({'status': f'{updated} payroll records approved'})
        
        return Response({'error': 'Provide ids or set all_employees=true'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanProcessPayroll])
    def mark_paid(self, request, pk=None):
        """Mark a payroll record as paid."""
        payroll = self.get_object()
        if payroll.status != 'APPROVED':
            return Response(
                {'error': 'Only approved payroll can be marked paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payroll.status = 'PAID'
        payroll.bank_transfer_date = request.data.get('transfer_date', timezone.now().date())
        payroll.transaction_id = request.data.get('transaction_id', '')
        payroll.save()
        
        return Response({'status': 'Payroll marked as paid'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def payslip(self, request, pk=None):
        """Get payslip data for a payroll record."""
        payroll = self._get_payslip_payroll(request, pk)
        if not payroll:
            return Response({'error': 'Payroll not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PayrollSerializer(payroll)
        data = serializer.data
        
        # Add employee bank details
        emp = payroll.employee
        data['bank_details'] = {
            'account_number': emp.bank_account_number or '',
            'bank_name': emp.bank_name or '',
            'ifsc_code': emp.ifsc_code or '',
        }
        
        # Add YTD totals
        ytd = Payroll.objects.filter(
            employee=payroll.employee,
            year=payroll.year,
            month__lte=payroll.month,
            status__in=['PROCESSED', 'APPROVED', 'PAID'],
        ).aggregate(
            total_gross=Sum('gross_salary'),
            total_deductions=Sum('total_deductions'),
            total_net=Sum('net_salary'),
        )
        data['ytd'] = {
            'gross': float(ytd.get('total_gross') or 0),
            'deductions': float(ytd.get('total_deductions') or 0),
            'net': float(ytd.get('total_net') or 0),
        }
        
        return Response(data)

    @action(detail=False, methods=['get'])
    def my_payslips(self, request):
        """Get payslips for the current user (ESS)."""
        try:
            employee = request.user.employee
        except:
            return Response({'error': 'User is not an employee'}, status=status.HTTP_400_BAD_REQUEST)
        
        year = request.query_params.get('year', datetime.now().year)
        payrolls = Payroll.objects.filter(
            employee=employee,
            year=year,
        ).select_related('processed_by', 'approved_by').prefetch_related('components').order_by('-month')
        
        page = self.paginate_queryset(payrolls)
        if page is not None:
            serializer = PayrollSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PayrollSerializer(payrolls, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def form16(self, request):
        """Download Form 16 PDF for an employee for a given financial year."""
        employee_id = request.query_params.get('employee_id')
        financial_year = request.query_params.get('financial_year')
        
        if not employee_id or not financial_year:
            return Response(
                {'error': 'employee_id and financial_year are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)
        
        generator = Form16Generator(employee, financial_year)
        return generator.generate_response()

    @action(detail=False, methods=['get'])
    def salary_certificate(self, request):
        """Download salary certificate as PDF."""
        employee_id = request.query_params.get('employee_id')
        months = int(request.query_params.get('months', 6))
        
        if not employee_id:
            return Response({'error': 'employee_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)
        
        generator = SalaryCertificateGenerator(employee, months)
        return generator.generate_response()

    @action(detail=False, methods=['get'])
    def salary_register(self, request):
        """Generate salary register for a period."""
        serializer = PayrollReportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        month = serializer.validated_data['month']
        year = serializer.validated_data['year']
        report_type = serializer.validated_data.get('report_type', 'salary_register')
        
        generator = PayrollReportGenerator(month, year)
        
        if report_type == 'salary_register':
            data = generator.salary_register()
        elif report_type == 'department_summary':
            data = generator.department_wise_summary()
        elif report_type == 'variance_report':
            prev_month = serializer.validated_data.get('previous_month')
            prev_year = serializer.validated_data.get('previous_year')
            data = generator.variance_report(prev_month, prev_year)
        else:
            return Response({'error': f'Unknown report type: {report_type}'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(data)

    @action(detail=False, methods=['get'])
    def department_summary(self, request):
        """Get department-wise payroll cost summary."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if not month or not year:
            return Response({'error': 'month and year required'}, status=status.HTTP_400_BAD_REQUEST)
        
        generator = PayrollReportGenerator(int(month), int(year))
        data = generator.department_wise_summary()
        return Response(data)

    @action(detail=False, methods=['get'])
    def variance_report(self, request):
        """Get month-over-month payroll variance."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if not month or not year:
            return Response({'error': 'month and year required'}, status=status.HTTP_400_BAD_REQUEST)
        
        prev_month = request.query_params.get('previous_month')
        prev_year = request.query_params.get('previous_year')
        
        generator = PayrollReportGenerator(int(month), int(year))
        data = generator.variance_report(
            int(prev_month) if prev_month else None,
            int(prev_year) if prev_year else None,
        )
        return Response(data)

    @action(detail=False, methods=['get'])
    def bank_file(self, request):
        """Generate bank transfer file (NEFT/RTGS)."""
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        file_format = request.query_params.get('transfer_mode', 'NEFT')

        if not month or not year:
            return Response({'error': 'month and year required'}, status=status.HTTP_400_BAD_REQUEST)
        
        generator = BankFileGenerator(int(month), int(year))
        
        if file_format == 'RTGS':
            content = generator.generate_rtgs_file()
        else:
            content = generator.generate_neft_file()
        
        filename = f"salary_transfer_{file_format}_{month}_{year}.txt"
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get payroll dashboard statistics."""
        year = request.query_params.get('year', datetime.now().year)
        month = request.query_params.get('month', datetime.now().month)
        
        current_month = Payroll.objects.filter(month=month, year=year).aggregate(
            total_gross=Sum('gross_salary'),
            total_net=Sum('net_salary'),
            total_deductions=Sum('total_deductions'),
            employee_count=Count('id', distinct=True),
            approved=Count('id', filter=Q(status='APPROVED')),
            paid=Count('id', filter=Q(status='PAID')),
        )
        
        ytd = Payroll.objects.filter(year=year).aggregate(
            ytd_gross=Sum('gross_salary'),
            ytd_net=Sum('net_salary'),
        )
        
        return Response({
            'current_month': {
                'total_gross': float(current_month.get('total_gross') or 0),
                'total_net': float(current_month.get('total_net') or 0),
                'total_deductions': float(current_month.get('total_deductions') or 0),
                'employee_count': current_month.get('employee_count') or 0,
                'approved': current_month.get('approved') or 0,
                'paid': current_month.get('paid') or 0,
            },
            'ytd': {
                'gross': float(ytd.get('ytd_gross') or 0),
                'net': float(ytd.get('ytd_net') or 0),
            }
        })


class HolidayViewSet(viewsets.ModelViewSet):
    """ViewSet for Holidays"""
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_national', 'applicable_locations']
    search_fields = ['name']

    @action(detail=False, methods=['get'])
    def current_year(self, request):
        """Get holidays for current year"""
        current_year = timezone.now().year
        holidays = self.get_queryset().filter(holiday_date__year=current_year)
        serializer = self.get_serializer(holidays, many=True)
        return Response(serializer.data)


# ============================================================================
# STATUTORY COMPLIANCE VIEWSETS
# ============================================================================

class PFConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for PF Configuration"""
    queryset = PFConfiguration.objects.filter(is_active=True)
    serializer_class = PFConfigurationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]

class PFContributionViewSet(viewsets.ModelViewSet):
    """ViewSet for PF Contributions"""
    serializer_class = PFContributionSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'month', 'year']

    def get_queryset(self):
        return PFContribution.objects.select_related('employee')

class ESIConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for ESI Configuration"""
    queryset = ESIConfiguration.objects.filter(is_active=True)
    serializer_class = ESIConfigurationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]

class ESIContributionViewSet(viewsets.ModelViewSet):
    """ViewSet for ESI Contributions"""
    serializer_class = ESIContributionSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'month', 'year']

    def get_queryset(self):
        return ESIContribution.objects.select_related('employee')

class ProfessionalTaxSlabViewSet(viewsets.ModelViewSet):
    """ViewSet for Professional Tax Slabs"""
    queryset = ProfessionalTaxSlab.objects.filter(is_active=True)
    serializer_class = ProfessionalTaxSlabSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['state', 'frequency']
    search_fields = ['state']

class PTContributionViewSet(viewsets.ModelViewSet):
    """ViewSet for PT Deductions"""
    serializer_class = PTContributionSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'month', 'year', 'state']

    def get_queryset(self):
        return PTContribution.objects.select_related('employee')

class TDSConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for TDS Configuration"""
    queryset = TDSConfiguration.objects.filter(is_active=True)
    serializer_class = TDSConfigurationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]

class InvestmentDeclarationViewSet(viewsets.ModelViewSet):
    """ViewSet for Employee Investment Declarations (Form 12BB)"""
    serializer_class = InvestmentDeclarationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'financial_year', 'is_approved']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return InvestmentDeclaration.objects.select_related('employee')
        else:
            try:
                employee = user.employee
                return InvestmentDeclaration.objects.filter(employee=employee)
            except:
                return InvestmentDeclaration.objects.none()

class TDSCalculationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for TDS Calculations"""
    serializer_class = TDSCalculationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'financial_year', 'month', 'year']

    def get_queryset(self):
        return TDSCalculation.objects.select_related('employee')

class GratuityConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for Gratuity Configuration"""
    queryset = GratuityConfiguration.objects.filter(is_active=True)
    serializer_class = GratuityConfigurationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]

class GratuityCalculationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Gratuity Calculations"""
    serializer_class = GratuityCalculationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'is_eligible']

    def get_queryset(self):
        return GratuityCalculation.objects.select_related('employee')

class BonusConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for Bonus Configuration"""
    queryset = BonusConfiguration.objects.filter(is_active=True)
    serializer_class = BonusConfigurationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]

class BonusCalculationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Bonus Calculations"""
    serializer_class = BonusCalculationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'financial_year', 'is_paid']

    def get_queryset(self):
        return BonusCalculation.objects.select_related('employee')

class ComplianceCalendarEntryViewSet(viewsets.ModelViewSet):
    """ViewSet for Compliance Calendar"""
    serializer_class = ComplianceCalendarEntrySerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['compliance_type', 'status', 'frequency', 'period_year']
    search_fields = ['title']

    def get_queryset(self):
        return ComplianceCalendarEntry.objects.all()

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming compliance events"""
        from datetime import date, timedelta
        days = int(request.query_params.get('days', 30))
        today = date.today()
        cutoff = today + timedelta(days=days)
        events = self.get_queryset().filter(due_date__gte=today, due_date__lte=cutoff, status='PENDING')
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue compliance events"""
        from datetime import date
        events = self.get_queryset().filter(due_date__lt=date.today(), status='PENDING')
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark a compliance event as completed"""
        event = self.get_object()
        event.status = 'COMPLETED'
        event.completed_date = timezone.now()
        event.completed_by = request.user
        event.reference_number = request.data.get('reference_number', '')
        event.save()
        return Response({'status': 'Compliance event marked as completed'}, status=status.HTTP_200_OK)


# ============================================================================
# STATUTORY COMPLIANCE FORMS VIEWSETS
# ============================================================================

class VPFContributionViewSet(viewsets.ModelViewSet):
    """ViewSet for VPF (Voluntary PF) contributions."""
    serializer_class = VPFContributionSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'month', 'year', 'is_active']

    def get_queryset(self):
        return VPFContribution.objects.select_related('employee').all()

    @action(detail=False, methods=['get'])
    def my_vpf(self, request):
        """Get current employee's VPF contributions."""
        try:
            emp = request.user.employee
            vpfs = VPFContribution.objects.filter(employee=emp)
            serializer = VPFContributionSerializer(vpfs, many=True)
            return Response(serializer.data)
        except Exception:
            return Response([])


class PFStatementViewSet(viewsets.ModelViewSet):
    """ViewSet for PF statutory forms (Form 2, 10C, 10D, 19, 31, etc)."""
    serializer_class = PFStatementSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'form_type', 'status']
    search_fields = ['employee__employee_id', 'employee__first_name', 'epfo_reference']

    def get_queryset(self):
        return PFStatement.objects.select_related('employee').all()

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update form status (submitted, acknowledged, completed, rejected)."""
        stmt = self.get_object()
        stmt.status = request.data.get('status', stmt.status)
        if request.data.get('epfo_reference'):
            stmt.epfo_reference = request.data['epfo_reference']
        if stmt.status in ['SUBMITTED', 'ACKNOWLEDGED']:
            stmt.submitted_date = timezone.now()
        if stmt.status == 'COMPLETED':
            stmt.completed_date = timezone.now()
        stmt.remarks = request.data.get('remarks', stmt.remarks)
        stmt.save()
        return Response({'status': f'Form status updated to {stmt.status}'})

    @action(detail=False, methods=['get'])
    def pending_forms(self, request):
        """Get forms that are pending submission."""
        pending = self.get_queryset().filter(status='PENDING')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_form_type(self, request):
        """Get forms filtered by form type."""
        form_type = request.query_params.get('form_type')
        if form_type:
            items = self.get_queryset().filter(form_type=form_type)
            serializer = self.get_serializer(items, many=True)
            return Response(serializer.data)
        return Response({'error': 'form_type parameter required'}, status=status.HTTP_400_BAD_REQUEST)


class ESICardViewSet(viewsets.ModelViewSet):
    """ViewSet for ESI Card / IP Number management."""
    serializer_class = ESICardSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'is_verified', 'is_active']
    search_fields = ['ip_number', 'employee__employee_id', 'employee__first_name']

    def get_queryset(self):
        return ESICard.objects.select_related('employee').all()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify an ESI card."""
        card = self.get_object()
        card.is_verified = True
        card.save()
        return Response({'status': 'ESI card verified'})


class LowerDeductionCertificateViewSet(viewsets.ModelViewSet):
    """ViewSet for Form 15G/15H - Lower/No TDS deduction certificates."""
    serializer_class = LowerDeductionCertificateSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'financial_year', 'certificate_type', 'is_verified']
    search_fields = ['employee__employee_id', 'employee__first_name']

    def get_queryset(self):
        return LowerDeductionCertificate.objects.select_related('employee', 'verified_by').all()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a certificate."""
        cert = self.get_object()
        cert.is_verified = True
        cert.verified_by = request.user
        cert.verified_date = timezone.now()
        cert.remarks = request.data.get('remarks', cert.remarks)
        cert.save()
        return Response({'status': 'Certificate verified'})

    @action(detail=False, methods=['get'])
    def my_certificates(self, request):
        """Get current user's certificates."""
        try:
            emp = request.user.employee
            certs = LowerDeductionCertificate.objects.filter(employee=emp)
            serializer = self.get_serializer(certs, many=True)
            return Response(serializer.data)
        except Exception:
            return Response([])


class PTEnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Professional Tax Enrollment tracking."""
    serializer_class = PTEnrollmentSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'state', 'is_active']
    search_fields = ['employee__employee_id', 'enrollment_number', 'state']

    def get_queryset(self):
        return PTEnrollment.objects.select_related('employee').all()


class InternationalWorkerViewSet(viewsets.ModelViewSet):
    """ViewSet for International Workers (separate PF rules)."""
    serializer_class = InternationalWorkerSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'country_of_origin', 'has_ssa', 'is_active']
    search_fields = ['employee__employee_id', 'passport_number', 'country_of_origin']

    def get_queryset(self):
        return InternationalWorker.objects.select_related('employee').all()


class Form12BAViewSet(viewsets.ModelViewSet):
    """ViewSet for Form 12BA - Perquisite Statement tracking."""
    serializer_class = Form12BASerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'financial_year', 'perquisite_type', 'is_taxable']
    search_fields = ['employee__employee_id', 'employee__first_name']

    def get_queryset(self):
        return Form12BA.objects.select_related('employee').all()

    @action(detail=False, methods=['get'])
    def perquisite_summary(self, request):
        """Get aggregated perquisite summary for an employee for a financial year."""
        employee_id = request.query_params.get('employee_id')
        financial_year = request.query_params.get('financial_year')
        if employee_id and financial_year:
            from django.db.models import Sum
            perqs = Form12BA.objects.filter(
                employee_id=employee_id,
                financial_year=financial_year
            ).values('perquisite_type', 'is_taxable').annotate(
                total=Sum('amount')
            )
            return Response(list(perqs))
        return Response({'error': 'employee_id and financial_year required'}, status=status.HTTP_400_BAD_REQUEST)


class Form24QReturnViewSet(viewsets.ModelViewSet):
    """ViewSet for Form 24Q - Quarterly TDS Return tracking."""
    serializer_class = Form24QReturnSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['financial_year', 'quarter', 'status']
    search_fields = ['financial_year', 'token_number']

    def get_queryset(self):
        return Form24QReturn.objects.all()

    @action(detail=True, methods=['post'])
    def mark_filed(self, request, pk=None):
        """Mark Form 24Q as filed."""
        ret = self.get_object()
        ret.status = 'FILED'
        ret.filing_date = request.data.get('filing_date', timezone.now().date())
        ret.token_number = request.data.get('token_number', ret.token_number)
        ret.total_tds_deducted = request.data.get('total_tds_deducted', ret.total_tds_deducted)
        ret.total_tds_deposited = request.data.get('total_tds_deposited', ret.total_tds_deposited)
        ret.total_deductees = request.data.get('total_deductees', ret.total_deductees)
        ret.save()
        return Response({'status': 'Form 24Q marked as filed'})

    @action(detail=False, methods=['get'])
    def pending_returns(self, request):
        """Get pending returns for current financial year."""
        pending = self.get_queryset().filter(status='PENDING')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def current_year(self, request):
        """Get all returns for current financial year."""
        from datetime import date
        today = date.today()
        fy = f"{today.year-1 if today.month < 4 else today.year}-{today.year if today.month < 4 else today.year+1}"
        returns = self.get_queryset().filter(financial_year=fy)
        serializer = self.get_serializer(returns, many=True)
        return Response(serializer.data)


# ============================================================================
# NEW VIEWSETS: LWF, OVERTIME, SHIFT SWAP, ATTENDANCE REGULARIZATION
# ============================================================================

from hr.models import (
    LWFConfiguration, LWFContribution,
    OvertimeRequest, ShiftSwapRequest, AttendanceRegularizationRequest
)
from hr.serializers import (
    LWFConfigurationSerializer, LWFContributionSerializer,
    OvertimeRequestSerializer, ShiftSwapRequestSerializer,
    AttendanceRegularizationRequestSerializer
)


class LWFConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for Labour Welfare Fund configuration per state."""
    serializer_class = LWFConfigurationSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['state', 'frequency', 'is_active']
    search_fields = ['state']

    def get_queryset(self):
        return LWFConfiguration.objects.all()


class LWFContributionViewSet(viewsets.ModelViewSet):
    """ViewSet for LWF contribution records."""
    serializer_class = LWFContributionSerializer
    permission_classes = [IsAuthenticated, IsHRStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'period', 'year', 'state', 'is_challan_generated']
    search_fields = ['employee__employee_id', 'employee__first_name']

    def get_queryset(self):
        return LWFContribution.objects.select_related('employee').all()

    @action(detail=True, methods=['post'])
    def generate_challan(self, request, pk=None):
        """Mark LWF challan as generated."""
        contrib = self.get_object()
        contrib.is_challan_generated = True
        contrib.challan_reference = request.data.get('challan_reference', '')
        contrib.save()
        return Response({'status': 'LWF challan generated'})

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark LWF contribution as paid."""
        contrib = self.get_object()
        contrib.paid_date = timezone.now().date()
        contrib.save()
        return Response({'status': 'LWF marked as paid'})

    @action(detail=False, methods=['get'])
    def pending_challans(self, request):
        """Get LWF contributions with unpaid challans."""
        pending = self.get_queryset().filter(is_challan_generated=False)
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary_by_state(self, request):
        """Summarize LWF contributions by state for a given year."""
        year = request.query_params.get('year', datetime.now().year)
        summary = (
            LWFContribution.objects
            .filter(year=year)
            .values('state')
            .annotate(
                total_employee=Sum('employee_contribution'),
                total_employer=Sum('employer_contribution'),
                total=Sum('total_contribution'),
                count=Count('id')
            )
        )
        return Response(list(summary))


class OvertimeRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for Overtime Request management."""
    serializer_class = OvertimeRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'status', 'date']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return OvertimeRequest.objects.select_related('employee', 'approved_by').all()
        elif user.role == 'Manager':
            try:
                emp = user.employee
                return OvertimeRequest.objects.filter(
                    employee__reporting_manager=emp
                ).select_related('employee', 'approved_by')
            except Exception:
                return OvertimeRequest.objects.none()
        else:
            try:
                emp = user.employee
                return OvertimeRequest.objects.filter(employee=emp)
            except Exception:
                return OvertimeRequest.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            instance = serializer.save(employee=emp)
        except Exception:
            instance = serializer.save()
        instance.calculate_ot_hours()
        instance.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrHR])
    def approve(self, request, pk=None):
        """Approve overtime request."""
        ot = self.get_object()
        if ot.status != 'PENDING':
            return Response({'error': 'Only pending OT requests can be approved'}, status=status.HTTP_400_BAD_REQUEST)
        ot.status = 'APPROVED'
        ot.approved_by = request.user
        ot.approved_date = timezone.now()
        ot.approval_comment = request.data.get('comment', '')
        ot.save()
        return Response({'status': 'Overtime approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrHR])
    def reject(self, request, pk=None):
        """Reject overtime request."""
        ot = self.get_object()
        ot.status = 'REJECTED'
        ot.approval_comment = request.data.get('reason', '')
        ot.approved_by = request.user
        ot.save()
        return Response({'status': 'Overtime rejected'})

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get OT requests pending approval (for manager/HR)."""
        pending = self.get_queryset().filter(status='PENDING')
        page = self.paginate_queryset(pending)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_overtime(self, request):
        """Get current user's OT requests."""
        try:
            emp = request.user.employee
            ots = OvertimeRequest.objects.filter(employee=emp)
            serializer = self.get_serializer(ots, many=True)
            return Response(serializer.data)
        except Exception:
            return Response([])


class ShiftSwapRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for Shift Swap Requests between employees."""
    serializer_class = ShiftSwapRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['requesting_employee', 'target_employee', 'status']
    search_fields = ['requesting_employee__first_name', 'target_employee__first_name']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return ShiftSwapRequest.objects.select_related(
                'requesting_employee', 'target_employee', 'approved_by'
            ).all()
        try:
            emp = user.employee
            return ShiftSwapRequest.objects.filter(
                Q(requesting_employee=emp) | Q(target_employee=emp)
            ).select_related('requesting_employee', 'target_employee')
        except Exception:
            return ShiftSwapRequest.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            serializer.save(requesting_employee=emp)
        except Exception:
            serializer.save()

    @action(detail=True, methods=['post'])
    def give_consent(self, request, pk=None):
        """Target employee gives consent (accept/decline)."""
        swap = self.get_object()
        accepted = request.data.get('accepted', False)
        swap.target_employee_consented = bool(accepted)
        swap.target_consent_date = timezone.now()
        if accepted:
            swap.status = 'PENDING_MANAGER'
        else:
            swap.status = 'REJECTED'
            swap.rejection_reason = request.data.get('reason', 'Declined by target employee')
        swap.save()
        return Response({'status': f"Consent: {'Accepted' if accepted else 'Declined'}"})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrHR])
    def approve(self, request, pk=None):
        """Manager approves the shift swap."""
        swap = self.get_object()
        if swap.status != 'PENDING_MANAGER':
            return Response({'error': 'Swap is not pending manager approval'}, status=status.HTTP_400_BAD_REQUEST)
        swap.status = 'APPROVED'
        swap.approved_by = request.user
        swap.approved_date = timezone.now()
        swap.save()
        return Response({'status': 'Shift swap approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrHR])
    def reject(self, request, pk=None):
        """Manager rejects the shift swap."""
        swap = self.get_object()
        swap.status = 'REJECTED'
        swap.approved_by = request.user
        swap.rejection_reason = request.data.get('reason', '')
        swap.save()
        return Response({'status': 'Shift swap rejected'})

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Requesting employee withdraws the swap."""
        swap = self.get_object()
        swap.status = 'WITHDRAWN'
        swap.save()
        return Response({'status': 'Shift swap withdrawn'})

    @action(detail=False, methods=['get'])
    def pending_consent(self, request):
        """Swaps pending target employee consent."""
        try:
            emp = request.user.employee
            swaps = ShiftSwapRequest.objects.filter(
                target_employee=emp, status='PENDING_CONSENT'
            )
            serializer = self.get_serializer(swaps, many=True)
            return Response(serializer.data)
        except Exception:
            return Response([])


class AttendanceRegularizationRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for Attendance Regularization Requests."""
    serializer_class = AttendanceRegularizationRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee', 'status']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['Superadmin', 'Admin']:
            return AttendanceRegularizationRequest.objects.select_related(
                'employee', 'attendance', 'approved_by'
            ).all()
        elif user.role == 'Manager':
            try:
                emp = user.employee
                return AttendanceRegularizationRequest.objects.filter(
                    employee__reporting_manager=emp
                ).select_related('employee', 'attendance')
            except Exception:
                return AttendanceRegularizationRequest.objects.none()
        else:
            try:
                emp = user.employee
                return AttendanceRegularizationRequest.objects.filter(employee=emp)
            except Exception:
                return AttendanceRegularizationRequest.objects.none()

    def perform_create(self, serializer):
        try:
            emp = self.request.user.employee
            serializer.save(employee=emp)
        except Exception:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrHR])
    def approve(self, request, pk=None):
        """Approve regularization and apply to attendance record."""
        reg_request = self.get_object()
        if reg_request.status != 'PENDING':
            return Response({'error': 'Only pending requests can be approved'}, status=status.HTTP_400_BAD_REQUEST)
        reg_request.status = 'APPROVED'
        reg_request.approved_by = request.user
        reg_request.approved_date = timezone.now()
        reg_request.approval_comment = request.data.get('comment', '')
        reg_request.save()
        # Apply changes to attendance
        reg_request.apply()
        return Response({'status': 'Regularization approved and applied to attendance'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrHR])
    def reject(self, request, pk=None):
        """Reject regularization request."""
        reg_request = self.get_object()
        if reg_request.status != 'PENDING':
            return Response({'error': 'Only pending requests can be rejected'}, status=status.HTTP_400_BAD_REQUEST)
        reg_request.status = 'REJECTED'
        reg_request.approved_by = request.user
        reg_request.approved_date = timezone.now()
        reg_request.approval_comment = request.data.get('reason', '')
        reg_request.save()
        return Response({'status': 'Regularization request rejected'})

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get regularization requests pending approval."""
        pending = self.get_queryset().filter(status='PENDING')
        page = self.paginate_queryset(pending)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Get current user's regularization requests."""
        try:
            emp = request.user.employee
            reqs = AttendanceRegularizationRequest.objects.filter(employee=emp)
            serializer = self.get_serializer(reqs, many=True)
            return Response(serializer.data)
        except Exception:
            return Response([])



# ============================================================================
# DATA SECURITY VIEWSETS
# ============================================================================

class IPAccessRestrictionViewSet(viewsets.ModelViewSet):
    """ViewSet for IP-based access control rules."""
    permission_classes = [IsAuthenticated, IsHRAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['restriction_type', 'role_required', 'is_active']

    def get_queryset(self):
        return IPAccessRestriction.objects.all()

    @action(detail=False, methods=['get'])
    def check_ip(self, request):
        """Check if current request IP is allowed."""
        ip_address = request.META.get('REMOTE_ADDR', '')
        module = request.query_params.get('module', '')
        
        allowed = IPAccessRestrictionService.is_ip_allowed(
            ip_address, user=request.user
        )
        return Response({
            'ip_address': ip_address,
            'module': module,
            'allowed': allowed,
        })

    @action(detail=False, methods=['get'])
    def my_access(self, request):
        """Get IP access restrictions that apply to current user."""
        ip_address = request.META.get('REMOTE_ADDR', '')
        role = request.user.role
        
        restrictions = IPAccessRestriction.objects.filter(
            is_active=True
        ).filter(
            Q(role_required=role) | Q(role_required='ANY') | Q(role_required__isnull=True) |
            Q(user=request.user)
        )
        
        serializer = IPAccessRestrictionSerializer(restrictions, many=True)
        return Response({
            'ip_address': ip_address,
            'restrictions': serializer.data,
        })


class DataRetentionViewSet(viewsets.ViewSet):
    """ViewSet for data retention policies and purging."""
    permission_classes = [IsAuthenticated, IsHRAdmin]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get data retention policy summary."""
        summary = DataRetentionService.get_retention_summary()
        return Response(summary)

    @action(detail=False, methods=['get'])
    def purgable(self, request):
        """Get records eligible for purging by data type."""
        data_type = request.query_params.get('data_type', 'EMPLOYEE')
        result = DataRetentionService.get_records_to_purge(data_type)
        return Response(result)

