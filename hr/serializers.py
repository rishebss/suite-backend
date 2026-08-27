import uuid
from rest_framework import serializers
from authentication.models import User, Department
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


# ============================================================================
# MASTER DATA SERIALIZERS
# ============================================================================

class DepartmentSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'manager', 'manager_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DesignationSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Designation
        fields = ['id', 'code', 'name', 'description', 'department', 'department_name', 'grade', 'band', 'is_active']
        read_only_fields = ['id']


class WorkLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkLocation
        fields = ['id', 'code', 'name', 'city', 'state', 'country', 'pin_code', 'address', 'is_active']
        read_only_fields = ['id']


class CostCenterSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = CostCenter
        fields = ['id', 'code', 'name', 'description', 'department', 'department_name', 'budget', 'is_active']
        read_only_fields = ['id']


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ['id', 'code', 'name', 'shift_type', 'description', 'start_time', 'end_time',
                  'break_duration_minutes', 'is_rotating', 'night_shift_allowance', 'is_active']
        read_only_fields = ['id']


# ============================================================================
# EMPLOYEE SERIALIZERS
# ============================================================================

class EmployeeDocumentSerializer(serializers.ModelSerializer):
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)

    class Meta:
        model = EmployeeDocument
        fields = ['id', 'employee', 'document_type', 'document_file', 'document_number',
                  'issue_date', 'expiry_date', 'is_verified', 'verified_by', 'verified_by_name',
                  'verified_date', 'remarks', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class EmployeeListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing employees (also used for creation)"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    location_name = serializers.CharField(source='work_location.name', read_only=True)
    reporting_manager_name = serializers.CharField(source='reporting_manager.get_full_name', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = Employee
        fields = ['id', 'employee_id', 'user', 'full_name', 'first_name', 'middle_name', 'last_name',
                  'date_of_birth', 'gender', 'marital_status', 'blood_group', 'nationality',
                  'personal_email', 'official_email', 'personal_mobile',
                  'current_address', 'current_city', 'current_state', 'current_country', 'current_pin_code',
                  'permanent_address', 'permanent_city', 'permanent_state', 'permanent_country', 'permanent_pin_code',
                  'aadhaar_number', 'pan_number', 'bank_account_number', 'ifsc_code', 'bank_name',
                  'department', 'department_name', 'designation', 'designation_name',
                  'work_location', 'location_name', 'work_shift',
                  'status', 'employment_type', 'date_of_joining', 'notice_period_days',
                  'reporting_manager', 'reporting_manager_name',
                  'is_active', 'created_at']
        read_only_fields = ['id', 'employee_id', 'created_at']


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """Complete serializer for employee details"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    location_name = serializers.CharField(source='work_location.name', read_only=True)
    reporting_manager_name = serializers.CharField(source='reporting_manager.get_full_name', read_only=True)
    dotted_manager_name = serializers.CharField(source='dotted_reporting_manager.get_full_name', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(source='get_age', read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'user', 'full_name', 'first_name', 'middle_name', 'last_name',
            'date_of_birth', 'age', 'gender', 'marital_status', 'blood_group', 'nationality',
            'personal_email', 'official_email', 'personal_mobile', 'current_address', 'current_city', 'current_state',
            'current_country', 'current_pin_code', 'permanent_address', 'permanent_city',
            'permanent_state', 'permanent_country', 'permanent_pin_code', 'emergency_contact_1_name',
            'emergency_contact_1_mobile', 'emergency_contact_1_relation', 'emergency_contact_2_name',
            'emergency_contact_2_mobile', 'emergency_contact_2_relation', 'aadhaar_number', 'pan_number',
            'passport_number', 'voter_id_number', 'driving_license_number', 'bank_account_number',
            'bank_name', 'bank_branch', 'ifsc_code', 'account_holder_name', 'spouse_name',
            'number_of_children', 'dependents', 'employment_type', 'date_of_joining',
            'probation_end_date', 'confirmation_date', 'notice_period_days', 'status',
            'separation_date', 'separation_reason', 'separation_notes', 'department', 'department_name',
            'designation', 'designation_name', 'work_location', 'location_name', 'cost_center',
            'grade', 'band', 'reporting_manager', 'reporting_manager_name', 'dotted_reporting_manager',
            'dotted_manager_name', 'company_entity', 'work_shift', 'photo', 'is_active', 'notes',
            'documents', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'employee_id', 'created_at', 'updated_at']


# ============================================================================
# ATTENDANCE & LEAVE SERIALIZERS
# ============================================================================

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'code', 'name', 'leave_type', 'description', 'default_annual_allocation',
                  'accrual_frequency', 'max_carry_forward', 'can_go_negative', 'min_balance_required',
                  'max_continuous_days', 'is_encashable', 'encashment_max_days', 'is_active']
        read_only_fields = ['id']


class EmployeeLeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = EmployeeLeaveBalance
        fields = ['id', 'employee', 'employee_id', 'leave_type', 'leave_type_name', 'financial_year',
                  'opening_balance', 'accrued_days', 'used_days', 'pending_days', 'encashed_days',
                  'lapsed_days', 'current_balance', 'last_updated']
        read_only_fields = ['id', 'last_updated']


class LeaveApplicationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    approval_manager_name = serializers.CharField(source='approval_manager.get_full_name', read_only=True)
    cancelled_by_name = serializers.CharField(source='cancelled_by.get_full_name', read_only=True)

    class Meta:
        model = LeaveApplication
        fields = ['id', 'employee', 'employee_name', 'leave_type', 'leave_type_name', 'date_from',
                  'date_to', 'number_of_days', 'reason', 'remarks', 'approval_status', 'applied_date',
                  'approval_manager', 'approval_manager_name', 'approval_date', 'approval_comment',
                  'is_cancelled', 'cancelled_by', 'cancelled_by_name', 'cancelled_date',
                  'cancellation_reason', 'is_backdated', 'created_at', 'updated_at']
        read_only_fields = ['id', 'applied_date', 'created_at', 'updated_at']


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    regularized_by_name = serializers.CharField(source='regularized_by.get_full_name', read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'employee', 'employee_name', 'date', 'check_in_time', 'check_out_time',
                  'check_in_location', 'check_out_location', 'status', 'working_hours', 'is_late',
                  'late_by_minutes', 'is_early_checkout', 'early_by_minutes', 'is_regularized',
                  'regularized_by', 'regularized_by_name', 'regularization_reason', 'shift', 'remarks',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.calculate_working_hours()
        instance.save()
        return instance


class CompensatoryOffSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = CompensatoryOff
        fields = ['id', 'employee', 'employee_name', 'earned_on_date', 'earned_hours',
                  'availed_on_date', 'status', 'remarks', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# PAYROLL SERIALIZERS
# ============================================================================

class SalaryComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryComponent
        fields = ['id', 'code', 'name', 'component_type', 'is_fixed', 'depends_on_basic',
                  'percentage_of_basic', 'is_taxable', 'is_statutory', 'exemption_limit',
                  'gl_account', 'description', 'is_active', 'order']
        read_only_fields = ['id']


class SalaryStructureDetailSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source='component.name', read_only=True)
    component_code = serializers.CharField(source='component.code', read_only=True)

    class Meta:
        model = SalaryStructureDetail
        fields = ['id', 'component', 'component_name', 'component_code', 'amount', 'is_percentage', 'order']
        read_only_fields = ['id']


class SalaryStructureSerializer(serializers.ModelSerializer):
    components = SalaryStructureDetailSerializer(many=True, read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)

    class Meta:
        model = SalaryStructure
        fields = ['id', 'code', 'name', 'grade', 'band', 'designation', 'designation_name',
                  'effective_from', 'effective_to', 'description', 'is_active', 'components',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeSalarySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    salary_structure_name = serializers.CharField(source='salary_structure.name', read_only=True)

    class Meta:
        model = EmployeeSalary
        fields = ['id', 'employee', 'employee_name', 'salary_structure', 'salary_structure_name',
                  'ctc', 'gross_salary', 'net_salary', 'basic_salary', 'effective_from',
                  'effective_to', 'is_active', 'previous_salary', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollComponentDetailSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source='component.name', read_only=True)
    component_code = serializers.CharField(source='component.code', read_only=True)

    class Meta:
        model = PayrollComponentDetail
        fields = ['id', 'component', 'component_name', 'component_code', 'amount']
        read_only_fields = ['id']


class PayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    components = PayrollComponentDetailSerializer(many=True, read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = Payroll
        fields = ['id', 'employee', 'employee_name', 'month', 'year', 'payroll_period',
                  'working_days', 'present_days', 'absent_days', 'half_day_count', 'leave_days',
                  'gross_salary', 'total_deductions', 'net_salary', 'arrears', 'final_salary',
                  'status', 'bank_transfer_date', 'transaction_id', 'processed_by', 'processed_by_name',
                  'processed_date', 'approved_by', 'approved_by_name', 'approved_date', 'remarks',
                  'components', 'created_at', 'updated_at']
        read_only_fields = ['id', 'payroll_period', 'status', 'processed_by', 'processed_date',
                            'approved_by', 'approved_date', 'bank_transfer_date', 'transaction_id',
                            'created_at', 'updated_at']


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'name', 'holiday_date', 'is_national', 'applicable_locations', 'description']
        read_only_fields = ['id']


# ============================================================================
# STATUTORY COMPLIANCE SERIALIZERS
# ============================================================================

class PFConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PFConfiguration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PFContributionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = PFContribution
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ESIConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ESIConfiguration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ESIContributionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = ESIContribution
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProfessionalTaxSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalTaxSlab
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PTContributionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = PTContribution
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class TDSConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TDSConfiguration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvestmentDeclarationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = InvestmentDeclaration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class TDSCalculationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = TDSCalculation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class GratuityConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GratuityConfiguration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class GratuityCalculationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = GratuityCalculation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class BonusConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusConfiguration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class BonusCalculationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = BonusCalculation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ComplianceCalendarEntrySerializer(serializers.ModelSerializer):
    completed_by_name = serializers.CharField(source='completed_by.get_full_name', read_only=True)

    class Meta:
        model = ComplianceCalendarEntry
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# PAYROLL ENHANCEMENT SERIALIZERS
# ============================================================================

class SalaryRevisionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    recommended_by_name = serializers.CharField(source='recommended_by.get_full_name', read_only=True)
    approved_by_manager_name = serializers.CharField(source='approved_by_manager.get_full_name', read_only=True)
    approved_by_hr_name = serializers.CharField(source='approved_by_hr.get_full_name', read_only=True)

    class Meta:
        model = SalaryRevision
        fields = '__all__'
        read_only_fields = ['id', 'percentage_increase', 'is_processed', 'arrears_amount',
                            'status', 'approved_by_manager', 'approved_by_hr', 'approved_by_finance',
                            'approved_date', 'processed_in_payroll', 'created_at', 'updated_at']


class SalaryRevisionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing revisions."""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    department_name = serializers.CharField(source='employee.department.name', read_only=True)

    class Meta:
        model = SalaryRevision
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_field', 'department_name',
            'previous_ctc', 'revised_ctc', 'percentage_increase',
            'revision_type', 'status', 'effective_month', 'effective_year',
            'recommended_by', 'is_processed', 'created_at',
        ]
        read_only_fields = ['id', 'percentage_increase', 'created_at']


class EmployeeLoanSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = EmployeeLoan
        fields = '__all__'
        read_only_fields = ['id', 'paid_amount', 'paid_emis', 'outstanding_amount',
                            'status', 'approved_by', 'approved_date', 'closure_date',
                            'created_at', 'updated_at']


class EmployeeLoanListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing loans."""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = EmployeeLoan
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_field',
            'loan_type', 'principal_amount', 'emi_amount', 'total_emis',
            'paid_emis', 'outstanding_amount', 'status', 'sanction_date',
        ]
        read_only_fields = ['id', 'paid_emis', 'outstanding_amount']


class LoanRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRepayment
        fields = '__all__'
        read_only_fields = ['id', 'payment_date', 'created_at']


class EmployeeReimbursementSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = EmployeeReimbursement
        fields = '__all__'
        read_only_fields = ['id', 'applied_date', 'status', 'approved_by', 'approved_date',
                            'payroll', 'paid_date', 'created_at', 'updated_at']


class EmployeeReimbursementListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing reimbursements."""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = EmployeeReimbursement
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_field',
            'expense_type', 'description', 'amount', 'expense_date',
            'status', 'applied_date',
        ]
        read_only_fields = ['id', 'applied_date', 'created_at']


# ============================================================================
# PAYROLL PROCESSING & REPORT SERIALIZERS
# ============================================================================

class PayrollProcessSerializer(serializers.Serializer):
    """Serializer for initiating payroll processing."""
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField()
    test_mode = serializers.BooleanField(default=False)
    department = serializers.UUIDField(required=False, allow_null=True)
    location = serializers.UUIDField(required=False, allow_null=True)


class PayrollApproveSerializer(serializers.Serializer):
    """Serializer for approving payroll."""
    ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    all_employees = serializers.BooleanField(default=False)
    remarks = serializers.CharField(required=False, allow_blank=True)


class BankFileSerializer(serializers.Serializer):
    """Serializer for bank file generation."""
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField()
    format = serializers.ChoiceField(choices=['NEFT', 'RTGS'], default='NEFT')


class PayrollReportSerializer(serializers.Serializer):
    """Serializer for generating payroll reports."""
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField()
    report_type = serializers.ChoiceField(
        choices=['salary_register', 'department_summary', 'variance_report'],
        default='salary_register'
    )
    previous_month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    previous_year = serializers.IntegerField(required=False)


# ============================================================================
# NEW MODEL SERIALIZERS: LWF, OVERTIME, SHIFT SWAP, REGULARIZATION
# ============================================================================

from hr.models import (
    LWFConfiguration, LWFContribution,
    OvertimeRequest, ShiftSwapRequest, AttendanceRegularizationRequest
)


class LWFConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LWFConfiguration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class LWFContributionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)

    class Meta:
        model = LWFContribution
        fields = '__all__'
        read_only_fields = ['id', 'total_contribution', 'created_at', 'updated_at']


class OvertimeRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = OvertimeRequest
        fields = '__all__'
        read_only_fields = ['id', 'employee', 'ot_amount', 'created_at', 'updated_at']


class ShiftSwapRequestSerializer(serializers.ModelSerializer):
    requesting_employee_name = serializers.CharField(
        source='requesting_employee.get_full_name', read_only=True
    )
    target_employee_name = serializers.CharField(
        source='target_employee.get_full_name', read_only=True
    )
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = ShiftSwapRequest
        fields = '__all__'
        read_only_fields = ['id', 'requesting_employee', 'created_at', 'updated_at']


class AttendanceRegularizationRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    attendance_date = serializers.DateField(source='attendance.date', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = AttendanceRegularizationRequest
        fields = '__all__'
        read_only_fields = ['id', 'employee', 'created_at', 'updated_at']



# ============================================================================
# STATUTORY COMPLIANCE FORMS SERIALIZERS
# ============================================================================

class VPFContributionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    class Meta:
        model = VPFContribution
        fields = '__all__'
        read_only_fields = ['id', 'vpf_amount', 'created_at', 'updated_at']


class PFStatementSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    form_type_display = serializers.CharField(source='get_form_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    class Meta:
        model = PFStatement
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ESICardSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    class Meta:
        model = ESICard
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class LowerDeductionCertificateSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    certificate_type_display = serializers.CharField(source='get_certificate_type_display', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    class Meta:
        model = LowerDeductionCertificate
        fields = '__all__'
        read_only_fields = ['id', 'is_verified', 'verified_date', 'created_at', 'updated_at']


class PTEnrollmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    class Meta:
        model = PTEnrollment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class InternationalWorkerSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    class Meta:
        model = InternationalWorker
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class Form12BASerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_id_field = serializers.CharField(source='employee.employee_id', read_only=True)
    perquisite_type_display = serializers.CharField(source='get_perquisite_type_display', read_only=True)
    class Meta:
        model = Form12BA
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class Form24QReturnSerializer(serializers.ModelSerializer):
    quarter_display = serializers.CharField(source='get_quarter_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    class Meta:
        model = Form24QReturn
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# DATA SECURITY SERIALIZERS
# ============================================================================

class IPAccessRestrictionSerializer(serializers.ModelSerializer):
    restriction_type_display = serializers.CharField(source='get_restriction_type_display', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = IPAccessRestriction
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DedupSerializer(serializers.Serializer):
    """Serializer for employee duplicate check request."""
    aadhaar_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    pan_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    personal_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    personal_mobile = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class BulkDedupSerializer(serializers.Serializer):
    """Serializer for bulk dedup check request."""
    employee_ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
