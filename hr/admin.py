from django.contrib import admin
from django.utils.html import format_html
from hr.models import (
    Designation, CostCenter, WorkLocation, Employee, EmployeeDocument,
    LeaveType, EmployeeLeaveBalance, LeaveApplication, Attendance, Shift,
    CompensatoryOff, SalaryComponent, SalaryStructure, SalaryStructureDetail,
    EmployeeSalary, Payroll, PayrollComponentDetail, Holiday,
    SalaryRevision, EmployeeLoan, LoanRepayment, EmployeeReimbursement,
    PFConfiguration, PFContribution, ESIConfiguration, ESIContribution,
    ProfessionalTaxSlab, PTContribution, TDSConfiguration,
    InvestmentDeclaration, TDSCalculation, GratuityConfiguration,
    GratuityCalculation, BonusConfiguration, BonusCalculation,
    ComplianceCalendarEntry
)


# Register your models here.

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'grade', 'band', 'is_active']
    list_filter = ['department', 'grade', 'is_active', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WorkLocation)
class WorkLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'city', 'state', 'country', 'is_active']
    list_filter = ['state', 'country', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'city']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'budget', 'is_active']
    list_filter = ['department', 'is_active', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'shift_type', 'start_time', 'end_time', 'is_active']
    list_filter = ['shift_type', 'is_rotating', 'is_active', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


class EmployeeDocumentInline(admin.TabularInline):
    model = EmployeeDocument
    extra = 1
    fields = ['document_type', 'document_number', 'issue_date', 'expiry_date', 'is_verified']
    readonly_fields = ['created_at']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'get_full_name', 'department', 'designation', 'status', 'date_of_joining']
    list_filter = ['status', 'employment_type', 'department', 'designation', 'date_of_joining', 'created_at']
    search_fields = ['employee_id', 'first_name', 'last_name', 'personal_email', 'pan_number', 'aadhaar_number']
    readonly_fields = ['employee_id', 'get_full_name', 'get_age', 'created_at', 'updated_at']
    inlines = [EmployeeDocumentInline]

    fieldsets = (
        ('System Information', {
            'fields': ('employee_id', 'user', 'status')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'middle_name', 'last_name', 'date_of_birth', 'get_age',
                      'gender', 'marital_status', 'blood_group', 'nationality', 'photo')
        }),
        ('Contact Details', {
            'fields': ('personal_email', 'personal_mobile')
        }),
        ('Current Address', {
            'fields': ('current_address', 'current_city', 'current_state', 'current_country', 'current_pin_code')
        }),
        ('Permanent Address', {
            'fields': ('permanent_address', 'permanent_city', 'permanent_state', 'permanent_country', 'permanent_pin_code')
        }),
        ('Emergency Contacts', {
            'fields': ('emergency_contact_1_name', 'emergency_contact_1_mobile', 'emergency_contact_1_relation',
                      'emergency_contact_2_name', 'emergency_contact_2_mobile', 'emergency_contact_2_relation')
        }),
        ('Identity Documents', {
            'fields': ('aadhaar_number', 'pan_number', 'passport_number', 'voter_id_number', 'driving_license_number')
        }),
        ('Bank Details', {
            'fields': ('bank_account_number', 'bank_name', 'bank_branch', 'ifsc_code', 'account_holder_name')
        }),
        ('Family Details', {
            'fields': ('spouse_name', 'number_of_children', 'dependents')
        }),
        ('Employment Information', {
            'fields': ('employment_type', 'date_of_joining', 'probation_end_date', 'confirmation_date', 'notice_period_days')
        }),
        ('Organization', {
            'fields': ('department', 'designation', 'work_location', 'cost_center', 'grade', 'band',
                      'reporting_manager', 'dotted_reporting_manager', 'company_entity', 'work_shift')
        }),
        ('Separation Information', {
            'fields': ('separation_date', 'separation_reason', 'separation_notes'),
            'classes': ('collapse',)
        }),
        ('Other', {
            'fields': ('is_active', 'notes'),
            'classes': ('collapse',)
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'

    def get_age(self, obj):
        return obj.get_age()
    get_age.short_description = 'Age'


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'document_type', 'document_number', 'is_verified', 'created_at']
    list_filter = ['document_type', 'is_verified', 'created_at']
    search_fields = ['employee__employee_id', 'document_number']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'leave_type', 'default_annual_allocation', 'is_encashable', 'is_active']
    list_filter = ['leave_type', 'accrual_frequency', 'is_encashable', 'is_active', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EmployeeLeaveBalance)
class EmployeeLeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'financial_year', 'current_balance', 'last_updated']
    list_filter = ['financial_year', 'leave_type', 'last_updated']
    search_fields = ['employee__employee_id', 'leave_type__name']
    readonly_fields = ['last_updated', 'created_at']


@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'date_from', 'date_to', 'approval_status', 'applied_date']
    list_filter = ['approval_status', 'leave_type', 'applied_date', 'created_at']
    search_fields = ['employee__employee_id', 'employee__first_name', 'employee__last_name']
    readonly_fields = ['applied_date', 'approval_date', 'cancelled_date', 'created_at', 'updated_at']
    actions = ['approve_action', 'reject_action']

    def approve_action(self, request, queryset):
        queryset.filter(approval_status='PENDING').update(approval_status='APPROVED', approval_manager=request.user)
    approve_action.short_description = 'Approve selected leave applications'

    def reject_action(self, request, queryset):
        queryset.filter(approval_status='PENDING').update(approval_status='REJECTED', approval_manager=request.user)
    reject_action.short_description = 'Reject selected leave applications'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'status', 'working_hours', 'is_late', 'is_regularized']
    list_filter = ['status', 'date', 'is_late', 'is_regularized', 'created_at']
    search_fields = ['employee__employee_id', 'employee__first_name', 'employee__last_name']
    readonly_fields = ['working_hours', 'created_at', 'updated_at']


@admin.register(CompensatoryOff)
class CompensatoryOffAdmin(admin.ModelAdmin):
    list_display = ['employee', 'earned_on_date', 'earned_hours', 'availed_on_date', 'status']
    list_filter = ['status', 'earned_on_date', 'created_at']
    search_fields = ['employee__employee_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'component_type', 'is_taxable', 'is_statutory', 'is_active']
    list_filter = ['component_type', 'is_taxable', 'is_statutory', 'is_active', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


class SalaryStructureDetailInline(admin.TabularInline):
    model = SalaryStructureDetail
    extra = 1


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'grade', 'band', 'effective_from', 'is_active']
    list_filter = ['grade', 'band', 'is_active', 'effective_from', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [SalaryStructureDetailInline]


@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'ctc', 'gross_salary', 'net_salary', 'effective_from', 'is_active']
    list_filter = ['is_active', 'effective_from', 'created_at']
    search_fields = ['employee__employee_id']
    readonly_fields = ['created_at', 'updated_at']


class PayrollComponentDetailInline(admin.TabularInline):
    model = PayrollComponentDetail
    extra = 0
    can_delete = False


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['employee', 'payroll_period', 'gross_salary', 'net_salary', 'status', 'processed_date']
    list_filter = ['status', 'month', 'year', 'processed_date', 'created_at']
    search_fields = ['employee__employee_id', 'payroll_period']
    readonly_fields = ['payroll_period', 'processed_date', 'approved_date', 'created_at', 'updated_at']
    inlines = [PayrollComponentDetailInline]

    fieldsets = (
        ('Employee Information', {
            'fields': ('employee', 'payroll_period')
        }),
        ('Period', {
            'fields': ('month', 'year')
        }),
        ('Attendance', {
            'fields': ('working_days', 'present_days', 'absent_days', 'half_day_count', 'leave_days')
        }),
        ('Salary Calculation', {
            'fields': ('gross_salary', 'total_deductions', 'net_salary', 'arrears', 'final_salary')
        }),
        ('Status & Payment', {
            'fields': ('status', 'bank_transfer_date', 'transaction_id')
        }),
        ('Approval', {
            'fields': ('processed_by', 'processed_date', 'approved_by', 'approved_date'),
            'classes': ('collapse',)
        }),
        ('Other', {
            'fields': ('remarks',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'holiday_date', 'is_national', 'created_at']
    list_filter = ['is_national', 'holiday_date', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


# ============================================================================
# STATUTORY COMPLIANCE ADMIN
# ============================================================================


@admin.register(PFConfiguration)
class PFConfigurationAdmin(admin.ModelAdmin):
    list_display = ['effective_from', 'employee_contribution_pct', 'employer_epf_pct', 'wage_ceiling', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PFContribution)
class PFContributionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month', 'year', 'total_employee_contribution', 'total_employer_contribution']
    list_filter = ['month', 'year', 'is_ecr_generated']
    search_fields = ['employee__employee_id', 'employee__first_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ESIConfiguration)
class ESIConfigurationAdmin(admin.ModelAdmin):
    list_display = ['effective_from', 'employee_contribution_pct', 'employer_contribution_pct', 'wage_ceiling', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ESIContribution)
class ESIContributionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month', 'year', 'total_contribution', 'is_challan_generated']
    list_filter = ['month', 'year', 'is_challan_generated']
    search_fields = ['employee__employee_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProfessionalTaxSlab)
class ProfessionalTaxSlabAdmin(admin.ModelAdmin):
    list_display = ['state', 'salary_from', 'salary_to', 'tax_amount', 'frequency', 'is_active']
    list_filter = ['state', 'frequency', 'is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PTContribution)
class PTContributionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month', 'year', 'state', 'pt_amount']
    list_filter = ['state', 'month', 'year']
    search_fields = ['employee__employee_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TDSConfiguration)
class TDSConfigurationAdmin(admin.ModelAdmin):
    list_display = ['financial_year', 'standard_deduction_old', 'standard_deduction_new', 'education_cess_pct', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InvestmentDeclaration)
class InvestmentDeclarationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'financial_year', 'tax_regime', 'is_submitted', 'is_approved']
    list_filter = ['financial_year', 'tax_regime', 'is_approved']
    search_fields = ['employee__employee_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TDSCalculation)
class TDSCalculationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'financial_year', 'month', 'year', 'ytd_total_tax', 'current_month_tds']
    list_filter = ['financial_year', 'month', 'year']
    search_fields = ['employee__employee_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(GratuityConfiguration)
class GratuityConfigurationAdmin(admin.ModelAdmin):
    list_display = ['formula_numerator', 'formula_denominator', 'min_service_years', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(GratuityCalculation)
class GratuityCalculationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'years_of_service', 'is_eligible', 'gratuity_amount']
    list_filter = ['is_eligible']
    search_fields = ['employee__employee_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BonusConfiguration)
class BonusConfigurationAdmin(admin.ModelAdmin):
    list_display = ['financial_year', 'wage_ceiling', 'minimum_bonus_pct', 'maximum_bonus_pct', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BonusCalculation)
class BonusCalculationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'financial_year', 'bonus_percentage', 'bonus_amount', 'is_paid']
    list_filter = ['financial_year', 'is_paid']
    search_fields = ['employee__employee_id']
    readonly_fields = ['created_at', 'updated_at']


# ============================================================================
# PAYROLL ENHANCEMENTS ADMIN
# ============================================================================


@admin.register(SalaryRevision)
class SalaryRevisionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'previous_ctc', 'revised_ctc', 'percentage_increase', 'status', 'effective_month', 'effective_year', 'is_processed']
    list_filter = ['status', 'revision_type', 'effective_year', 'is_processed']
    search_fields = ['employee__employee_id', 'employee__first_name', 'employee__last_name']
    readonly_fields = ['percentage_increase', 'is_processed', 'created_at', 'updated_at']
    actions = ['approve_selected']

    def approve_selected(self, request, queryset):
        from django.utils import timezone
        queryset.filter(status='PENDING_FINANCE').update(status='APPROVED', approved_date=timezone.now())
    approve_selected.short_description = 'Approve selected revisions'


@admin.register(EmployeeLoan)
class EmployeeLoanAdmin(admin.ModelAdmin):
    list_display = ['employee', 'loan_type', 'principal_amount', 'emi_amount', 'outstanding_amount', 'status']
    list_filter = ['loan_type', 'status', 'sanction_date']
    search_fields = ['employee__employee_id', 'employee__first_name']
    readonly_fields = ['paid_amount', 'paid_emis', 'outstanding_amount', 'created_at', 'updated_at']


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'month', 'year', 'payment_date']
    list_filter = ['month', 'year', 'is_processed']
    readonly_fields = ['payment_date', 'created_at']


@admin.register(EmployeeReimbursement)
class EmployeeReimbursementAdmin(admin.ModelAdmin):
    list_display = ['employee', 'expense_type', 'amount', 'status', 'applied_date']
    list_filter = ['expense_type', 'status', 'applied_date']
    search_fields = ['employee__employee_id', 'description']
    actions = ['approve_reimbursements']

    def approve_reimbursements(self, request, queryset):
        from django.utils import timezone
        queryset.filter(status='PENDING').update(status='APPROVED', approved_by=request.user, approved_date=timezone.now())
    approve_reimbursements.short_description = 'Approve selected reimbursements'


@admin.register(ComplianceCalendarEntry)
class ComplianceCalendarEntryAdmin(admin.ModelAdmin):
    list_display = ['compliance_type', 'title', 'due_date', 'frequency', 'status']
    list_filter = ['compliance_type', 'status', 'frequency', 'period_year']
    search_fields = ['title', 'reference_number']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['mark_as_completed']

    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='COMPLETED', completed_date=timezone.now())
    mark_as_completed.short_description = 'Mark selected as completed'
