from decimal import Decimal, ROUND_HALF_UP
import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from core.models import Main
from authentication.models import User, Department
from hr.managers import EmployeeManager, AttendanceManager, LeaveManager


# ============================================================================
# CONSTANTS AND CHOICES
# ============================================================================

EMPLOYMENT_TYPE = (
    ('PERMANENT', 'Permanent'),
    ('CONTRACT', 'Contract'),
    ('TRAINEE', 'Trainee'),
    ('INTERN', 'Intern'),
    ('PART_TIME', 'Part-Time'),
)

EMPLOYEE_STATUS = (
    ('CANDIDATE', 'Candidate'),
    ('OFFERED', 'Offered'),
    ('ONBOARDING', 'Onboarding'),
    ('ACTIVE', 'Active'),
    ('ON_LEAVE', 'On Leave'),
    ('NOTICE_PERIOD', 'Notice Period'),
    ('SEPARATED', 'Separated'),
)

SEPARATION_REASON = (
    ('RESIGNED', 'Resigned'),
    ('TERMINATED', 'Terminated'),
    ('ABSCONDED', 'Absconded'),
    ('RETIRED', 'Retired'),
    ('DECEASED', 'Deceased'),
)

GENDER = (
    ('MALE', 'Male'),
    ('FEMALE', 'Female'),
    ('OTHER', 'Other'),
)

MARITAL_STATUS = (
    ('SINGLE', 'Single'),
    ('MARRIED', 'Married'),
    ('DIVORCED', 'Divorced'),
    ('WIDOWED', 'Widowed'),
)

BLOOD_GROUP = (
    ('A_POSITIVE', 'A+'),
    ('A_NEGATIVE', 'A-'),
    ('B_POSITIVE', 'B+'),
    ('B_NEGATIVE', 'B-'),
    ('AB_POSITIVE', 'AB+'),
    ('AB_NEGATIVE', 'AB-'),
    ('O_POSITIVE', 'O+'),
    ('O_NEGATIVE', 'O-'),
)

SHIFT_TYPE = (
    ('GENERAL', 'General (9 AM - 6 PM)'),
    ('ROTATIONAL', 'Rotational'),
    ('NIGHT', 'Night Shift'),
    ('FLEXIBLE', 'Flexible'),
    ('REMOTE', 'Remote'),
)

ATTENDANCE_STATUS = (
    ('PRESENT', 'Present'),
    ('ABSENT', 'Absent'),
    ('HALF_DAY', 'Half Day'),
    ('WFH', 'Work From Home'),
    ('ON_LEAVE', 'On Leave'),
)

LEAVE_STATUS = (
    ('PENDING', 'Pending'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
    ('CANCELLED', 'Cancelled'),
)

DOCUMENT_TYPE = (
    ('OFFER_LETTER', 'Offer Letter'),
    ('APPOINTMENT_LETTER', 'Appointment Letter'),
    ('10TH_CERTIFICATE', '10th Certificate'),
    ('12TH_CERTIFICATE', '12th Certificate'),
    ('UG_CERTIFICATE', 'UG Certificate'),
    ('PG_CERTIFICATE', 'PG Certificate'),
    ('PROFESSIONAL_CERT', 'Professional Certificate'),
    ('EXPERIENCE_CERT', 'Experience Certificate'),
    ('BGV_DOCUMENT', 'BGV Document'),
    ('AADHAAR', 'Aadhaar'),
    ('PAN', 'PAN'),
    ('PASSPORT', 'Passport'),
    ('VOTER_ID', 'Voter ID'),
    ('DRIVING_LICENSE', 'Driving License'),
    ('BANK_DETAILS', 'Bank Details'),
    ('OTHER', 'Other'),
)

LEAVE_TYPE = (
    ('CASUAL', 'Casual Leave'),
    ('SICK', 'Sick Leave'),
    ('EARNED', 'Earned Leave'),
    ('MATERNITY', 'Maternity Leave'),
    ('PATERNITY', 'Paternity Leave'),
    ('BEREAVEMENT', 'Bereavement Leave'),
    ('COMP_OFF', 'Compensatory Off'),
    ('OPTIONAL', 'Optional Holiday'),
    ('LWP', 'Leave Without Pay'),
    ('MARRIAGE', 'Marriage Leave'),
    ('STUDY', 'Study Leave'),
)

SALARY_COMPONENT_TYPE = (
    ('EARNINGS', 'Earnings'),
    ('DEDUCTIONS', 'Deductions'),
    ('FIXED', 'Fixed'),
    ('VARIABLE', 'Variable'),
)


# ============================================================================
# PHASE 1: CORE HR - EMPLOYEE MASTER
# ============================================================================

class Designation(Main):
    """Job Designation/Position Master"""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    grade = models.CharField(max_length=20, blank=True, null=True)  # E.g., E1, M1, S1
    band = models.CharField(max_length=20, blank=True, null=True)   # E.g., IC1, IC2
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Designation'
        verbose_name_plural = 'Designations'

    def __str__(self):
        return f"{self.name} ({self.code})"


class CostCenter(Main):
    """Cost Center for allocation of expenses"""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Cost Center'
        verbose_name_plural = 'Cost Centers'

    def __str__(self):
        return f"{self.name} ({self.code})"


class WorkLocation(Main):
    """Work Location/Branch Master"""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    pin_code = models.CharField(max_length=10, blank=True)
    address = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Work Location'
        verbose_name_plural = 'Work Locations'

    def __str__(self):
        return f"{self.name} ({self.city})"


class Employee(Main):
    """Core Employee Master Model"""
    
    # System Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee_id = models.CharField(max_length=20, unique=True)  # EMP-YYYY-XXXX
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee')
    
    # ========== PERSONAL INFORMATION ==========
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS, null=True, blank=True)
    blood_group = models.CharField(max_length=20, choices=BLOOD_GROUP, null=True, blank=True)
    nationality = models.CharField(max_length=50, default='Indian')
    
    # Contact Details
    personal_email = models.EmailField(unique=True)
    official_email = models.EmailField(unique=True, blank=True, null=True,
        help_text="Company-provided email address")
    personal_mobile = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Invalid phone number')]
    )
    
    # Current Address
    current_address = models.TextField()
    current_city = models.CharField(max_length=50)
    current_state = models.CharField(max_length=50)
    current_country = models.CharField(max_length=50, default='India')
    current_pin_code = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^\d{6}$', 'PIN code must be exactly 6 digits')]
    )
    
    # Permanent Address
    permanent_address = models.TextField()
    permanent_city = models.CharField(max_length=50)
    permanent_state = models.CharField(max_length=50)
    permanent_country = models.CharField(max_length=50, default='India')
    permanent_pin_code = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^\d{6}$', 'PIN code must be exactly 6 digits')]
    )
    
    # Emergency Contacts (storing as JSON would be better, implementing as separate model in Phase 1.5)
    emergency_contact_1_name = models.CharField(max_length=100, blank=True)
    emergency_contact_1_mobile = models.CharField(max_length=20, blank=True)
    emergency_contact_1_relation = models.CharField(max_length=50, blank=True)
    
    emergency_contact_2_name = models.CharField(max_length=100, blank=True)
    emergency_contact_2_mobile = models.CharField(max_length=20, blank=True)
    emergency_contact_2_relation = models.CharField(max_length=50, blank=True)
    
    # ========== IDENTITY DOCUMENTS ==========
    aadhaar_number = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\d{12}$', 'Aadhaar must be 12 digits')],
        help_text="12-digit Aadhaar number"
    )
    pan_number = models.CharField(
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', 'Invalid PAN format')],
        help_text="PAN in format: ABCDE1234F"
    )
    passport_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    voter_id_number = models.CharField(max_length=20, blank=True, null=True)
    driving_license_number = models.CharField(max_length=20, blank=True, null=True)
    
    # ========== BANK DETAILS ==========
    bank_account_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_branch = models.CharField(max_length=100, blank=True, null=True)
    ifsc_code = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^[A-Z]{4}0[A-Z0-9]{6}$', 'Invalid IFSC code')]
    )
    account_holder_name = models.CharField(max_length=100, blank=True, null=True)
    
    # ========== FAMILY DETAILS ==========
    spouse_name = models.CharField(max_length=100, blank=True, null=True)
    number_of_children = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    dependents = models.TextField(blank=True, null=True, help_text="JSON or comma-separated list")
    
    # ========== EMPLOYMENT INFORMATION ==========
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE)
    date_of_joining = models.DateField()
    probation_end_date = models.DateField(blank=True, null=True)
    confirmation_date = models.DateField(blank=True, null=True)
    notice_period_days = models.IntegerField(default=30)
    
    # Employment Status
    status = models.CharField(max_length=20, choices=EMPLOYEE_STATUS, default='ONBOARDING')
    
    # Separation Info (if separated)
    separation_date = models.DateField(blank=True, null=True)
    separation_reason = models.CharField(max_length=20, choices=SEPARATION_REASON, blank=True, null=True)
    separation_notes = models.TextField(blank=True, null=True)
    
    # ========== ORGANIZATION HIERARCHIES ==========
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='employees')
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, related_name='employees')
    work_location = models.ForeignKey(WorkLocation, on_delete=models.SET_NULL, null=True, related_name='employees')
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    grade = models.CharField(max_length=20, blank=True, null=True)  # E.g., E1, M1
    band = models.CharField(max_length=20, blank=True, null=True)   # E.g., IC1, IC2
    
    # Reporting
    reporting_manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    dotted_reporting_manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dotted_subordinates'
    )
    
    # Additional Employment Fields
    company_entity = models.CharField(max_length=100, blank=True, null=True)
    work_shift = models.CharField(max_length=20, choices=SHIFT_TYPE, default='GENERAL')
    
    # Photo
    photo = models.ImageField(upload_to='employee_photos/%Y/%m/', blank=True, null=True)
    
    # Additional Info
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    # Managers
    objects = EmployeeManager()
    
    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['aadhaar_number']),
            models.Index(fields=['pan_number']),
            models.Index(fields=['status']),
            models.Index(fields=['department']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"
    
    def get_full_name(self):
        """Return employee's full name"""
        name = f"{self.first_name} {self.last_name}"
        if self.middle_name:
            name = f"{self.first_name} {self.middle_name} {self.last_name}"
        return name.strip()
    
    def get_age(self):
        """Calculate employee's age"""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def save(self, *args, **kwargs):
        # Generate employee_id if not exists using configurable format
        if not self.employee_id:
            from django.conf import settings
            from datetime import datetime
            
            emp_id_format = getattr(settings, 'EMPLOYEE_ID_FORMAT', 'EMP-{year}-{seq:04d}')
            count = Employee.objects.filter(
                created_at__year=datetime.now().year
            ).count() + 1
            year = datetime.now().year
            self.employee_id = emp_id_format.format(year=year, seq=count)
        
        super().save(*args, **kwargs)


class EmployeeDocument(Main):
    """Document management for employees"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE)
    document_file = models.FileField(max_length=255, upload_to='hr/employee_documents/%Y/%m/')
    document_number = models.CharField(max_length=100, blank=True, null=True)
    issue_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verified_date = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Employee Document'
        verbose_name_plural = 'Employee Documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_document_type_display()}"


# ============================================================================
# PHASE 1: ATTENDANCE & LEAVE MANAGEMENT
# ============================================================================

class LeaveType(Main):
    """Leave Type Master"""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE)
    description = models.TextField(blank=True, null=True)
    
    # Leave Policy
    default_annual_allocation = models.IntegerField(default=0)  # No. of days per year
    accrual_frequency = models.CharField(
        max_length=20,
        choices=[
            ('MONTHLY', 'Monthly'),
            ('QUARTERLY', 'Quarterly'),
            ('ANNUAL', 'Annual'),
        ],
        default='ANNUAL'
    )
    max_carry_forward = models.IntegerField(default=0)  # Max days that can be carried forward
    can_go_negative = models.BooleanField(default=False)  # Allow negative balance
    min_balance_required = models.IntegerField(default=0)  # Min balance to apply leave
    max_continuous_days = models.IntegerField(default=999)  # Max continuous days allowed
    is_encashable = models.BooleanField(default=False)  # Can unused leave be paid?
    encashment_max_days = models.IntegerField(default=0)  # Max days that can be encashed
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Leave Type'
        verbose_name_plural = 'Leave Types'

    def __str__(self):
        return f"{self.name} ({self.code})"


class EmployeeLeaveBalance(Main):
    """Track leave balance for each employee per leave type"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    financial_year = models.CharField(max_length=9)  # E.g., "2025-2026"
    
    opening_balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    accrued_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pending_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Pending approval
    encashed_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    lapsed_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    current_balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'leave_type', 'financial_year')
        verbose_name = 'Employee Leave Balance'
        verbose_name_plural = 'Employee Leave Balances'

    def __str__(self):
        return f"{self.employee.employee_id} - {self.leave_type.name} ({self.financial_year})"
    
    def calculate_balance(self):
        """Recalculate current balance"""
        self.current_balance = (
            self.opening_balance +
            self.accrued_days -
            self.used_days -
            self.encashed_days -
            self.lapsed_days +
            self.pending_days
        )
        return self.current_balance


class LeaveApplication(Main):
    """Leave Application/Request"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_applications')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.SET_NULL, null=True)
    
    # Dates
    date_from = models.DateField()
    date_to = models.DateField()
    number_of_days = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Application Info
    reason = models.TextField()
    remarks = models.TextField(blank=True, null=True)
    
    # Approval Workflow
    approval_status = models.CharField(max_length=20, choices=LEAVE_STATUS, default='PENDING')
    applied_date = models.DateTimeField(auto_now_add=True)
    
    # Manager Approval
    approval_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )
    approval_date = models.DateTimeField(blank=True, null=True)
    approval_comment = models.TextField(blank=True, null=True)
    
    # Cancellation
    is_cancelled = models.BooleanField(default=False)
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_leaves'
    )
    cancelled_date = models.DateTimeField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    
    # Validation
    is_backdated = models.BooleanField(default=False)
    
    objects = LeaveManager()

    class Meta:
        verbose_name = 'Leave Application'
        verbose_name_plural = 'Leave Applications'
        ordering = ['-applied_date']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.leave_type.name} ({self.date_from} to {self.date_to})"


class Attendance(Main):
    """Daily attendance record"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    
    # Check-in / Check-out
    check_in_time = models.TimeField(blank=True, null=True)
    check_out_time = models.TimeField(blank=True, null=True)
    
    # Location (GPS)
    check_in_location = models.CharField(max_length=255, blank=True, null=True)
    check_out_location = models.CharField(max_length=255, blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='ABSENT')
    
    # Duration
    working_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Flags
    is_late = models.BooleanField(default=False)
    late_by_minutes = models.IntegerField(default=0)
    is_early_checkout = models.BooleanField(default=False)
    early_by_minutes = models.IntegerField(default=0)
    
    # Regularization
    is_regularized = models.BooleanField(default=False)
    regularized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    regularization_reason = models.TextField(blank=True, null=True)
    
    # Shift Info
    shift = models.CharField(max_length=20, choices=SHIFT_TYPE, default='GENERAL')
    
    # Notes
    remarks = models.TextField(blank=True, null=True)
    
    objects = AttendanceManager()

    class Meta:
        unique_together = ('employee', 'date')
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.date} ({self.status})"
    
    def calculate_working_hours(self):
        """Calculate working hours from check-in/out times"""
        if self.check_in_time and self.check_out_time:
            from datetime import datetime
            check_in = datetime.combine(self.date, self.check_in_time)
            check_out = datetime.combine(self.date, self.check_out_time)
            duration = check_out - check_in
            self.working_hours = duration.total_seconds() / 3600
            return self.working_hours
        return 0


class Shift(Main):
    """Shift Master and Configuration"""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPE)
    description = models.TextField(blank=True, null=True)
    
    # Timing
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_duration_minutes = models.IntegerField(default=60)
    
    # Frequency
    is_rotating = models.BooleanField(default=False)
    rotation_pattern = models.TextField(blank=True, null=True, help_text="Days or weeks for rotation")
    
    # Allowances
    night_shift_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Shift'
        verbose_name_plural = 'Shifts'

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"


class CompensatoryOff(Main):
    """Compensatory Off (Comp-Off) Management"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='comp_offs')
    earned_on_date = models.DateField()  # Date employee worked extra
    earned_hours = models.DecimalField(max_digits=5, decimal_places=2)
    
    availed_on_date = models.DateField(blank=True, null=True)  # Date comp-off was taken
    status = models.CharField(
        max_length=20,
        choices=[
            ('EARNED', 'Earned'),
            ('AVAILED', 'Availed'),
            ('LAPSED', 'Lapsed'),
        ],
        default='EARNED'
    )
    
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Compensatory Off'
        verbose_name_plural = 'Compensatory Offs'

    def __str__(self):
        return f"{self.employee.employee_id} - Comp-Off ({self.earned_on_date})"


# ============================================================================
# PHASE 1: BASIC PAYROLL STRUCTURE
# ============================================================================

class SalaryComponent(Main):
    """Salary Components Master (Earnings, Deductions)"""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    component_type = models.CharField(max_length=20, choices=SALARY_COMPONENT_TYPE)
    
    # Classification
    is_fixed = models.BooleanField(default=True)
    depends_on_basic = models.BooleanField(default=False)  # If True, calculated as % of basic
    percentage_of_basic = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Tax & Statutory
    is_taxable = models.BooleanField(default=False)
    is_statutory = models.BooleanField(default=False)
    exemption_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # GL Account (for accounting integration)
    gl_account = models.CharField(max_length=100, blank=True, null=True)
    
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)  # Display order

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Salary Component'
        verbose_name_plural = 'Salary Components'

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.get_component_type_display()}"


class SalaryStructure(Main):
    """Salary Structure Template"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    
    # Applicable to
    grade = models.CharField(max_length=20, blank=True, null=True)
    band = models.CharField(max_length=20, blank=True, null=True)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Effective Dates
    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Salary Structure'
        verbose_name_plural = 'Salary Structures'
        ordering = ['code']

    def __str__(self):
        return f"{self.name} ({self.code})"


class SalaryStructureDetail(Main):
    """Components in a Salary Structure"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    salary_structure = models.ForeignKey(SalaryStructure, on_delete=models.CASCADE, related_name='components')
    component = models.ForeignKey(SalaryComponent, on_delete=models.CASCADE)
    
    # Amount
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    is_percentage = models.BooleanField(default=False)  # If True, amount is %
    
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = ('salary_structure', 'component')
        ordering = ['order']
        verbose_name = 'Salary Structure Detail'
        verbose_name_plural = 'Salary Structure Details'

    def __str__(self):
        return f"{self.salary_structure.code} - {self.component.name}"


class EmployeeSalary(Main):
    """Employee Salary Details"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_details')
    salary_structure = models.ForeignKey(SalaryStructure, on_delete=models.SET_NULL, null=True)
    
    # CTC Details
    ctc = models.DecimalField(max_digits=15, decimal_places=2)  # Cost to Company
    gross_salary = models.DecimalField(max_digits=15, decimal_places=2)
    net_salary = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Basic Components
    basic_salary = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Effective Dates
    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    
    # Previous Salary (for increment tracking)
    previous_salary = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='next_salary'
    )

    class Meta:
        verbose_name = 'Employee Salary'
        verbose_name_plural = 'Employee Salaries'
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.effective_from}"


class Payroll(Main):
    """Monthly Payroll Record"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payroll_records')
    
    # Period
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()
    payroll_period = models.CharField(max_length=20)  # E.g., "2025-01"
    
    # Attendance
    working_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    present_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    absent_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    half_day_count = models.IntegerField(default=0)
    
    # Leave
    leave_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Salary Calculation
    gross_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Additional
    arrears = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    final_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PROCESSED', 'Processed'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Bank Details
    bank_transfer_date = models.DateField(blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Audit
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    processed_date = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payrolls'
    )
    approved_date = models.DateTimeField(blank=True, null=True)
    
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'month', 'year')
        verbose_name = 'Payroll'
        verbose_name_plural = 'Payrolls'
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.payroll_period}"


class PayrollComponentDetail(Main):
    """Component-wise breakdown for a payroll"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='components')
    component = models.ForeignKey(SalaryComponent, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        unique_together = ('payroll', 'component')
        verbose_name = 'Payroll Component Detail'
        verbose_name_plural = 'Payroll Component Details'

    def __str__(self):
        return f"{self.payroll.payroll_period} - {self.component.name}: {self.amount}"


# Special Models for Enhanced Functionality

class Holiday(Main):
    """Holiday Calendar Master"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    holiday_date = models.DateField()
    is_national = models.BooleanField(default=True)
    applicable_locations = models.ManyToManyField(WorkLocation, blank=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Holiday'
        verbose_name_plural = 'Holidays'
        ordering = ['holiday_date']

    def __str__(self):
        return f"{self.name} ({self.holiday_date})"


# ==========================================
# RECRUITMENT & ONBOARDING MODELS
# ==========================================

class JobRequisition(Main):
    """Job Requisition Form (JRF)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='requisitions_raised')
    vacancies = models.PositiveIntegerField()
    priority = models.CharField(max_length=20, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Critical', 'Critical')])
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Closed', 'Closed')], default='Pending')
    justification = models.TextField()
    budget_allocated = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Job Requisition'
        verbose_name_plural = 'Job Requisitions'
        ordering = ['-created_at']

class Candidate(Main):
    """Candidate Database for ATS"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    resume = models.FileField(upload_to='resumes/%Y/%m/', null=True, blank=True)
    source = models.CharField(max_length=50, null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    class Meta:
        verbose_name = 'Candidate'
        verbose_name_plural = 'Candidates'

class JobApplication(Main):
    """ATS Pipeline for a Candidate"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    requisition = models.ForeignKey(JobRequisition, on_delete=models.CASCADE, related_name='applications')
    stage = models.CharField(max_length=50, choices=[
        ('Applied', 'Applied'), ('Screening', 'Screening'), ('L1_Interview', 'L1 Interview'),
        ('L2_Interview', 'L2 Interview'), ('HR_Round', 'HR Round'), ('Offered', 'Offered'),
        ('Accepted', 'Accepted'), ('Rejected', 'Rejected')
    ], default='Applied')
    applied_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Job Application'
        verbose_name_plural = 'Job Applications'
        unique_together = ['candidate', 'requisition']

# ==========================================
# PERFORMANCE MANAGEMENT SYSTEM (PMS)
# ==========================================

class AppraisalCycle(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)  # e.g. FY 2025-26 Annual Appraisal
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Closed', 'Closed')])
    
    class Meta:
        verbose_name = 'Appraisal Cycle'
        verbose_name_plural = 'Appraisal Cycles'

class PerformanceGoal(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='goals')
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE)
    description = models.TextField()
    weightage = models.DecimalField(max_digits=5, decimal_places=2)  # percentage
    status = models.CharField(max_length=20, default='Pending')

class PerformanceReview(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reviews')
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE)
    self_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    manager_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    final_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    manager_comments = models.TextField(null=True, blank=True)

# ==========================================
# TRAINING & DEVELOPMENT (L&D)
# ==========================================

class TrainingProgram(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    training_type = models.CharField(max_length=50, choices=[('Internal', 'Internal'), ('External', 'External'), ('Online', 'Online')])
    start_date = models.DateField()
    end_date = models.DateField()
    trainer_name = models.CharField(max_length=100, null=True, blank=True)

class TrainingNomination(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('Nominated', 'Nominated'), ('Approved', 'Approved'), ('Completed', 'Completed'), ('Failed', 'Failed')])
    completion_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

# ==========================================
# EXIT MANAGEMENT
# ==========================================

class Resignation(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='resignations')
    submitted_on = models.DateField(auto_now_add=True)
    reason = models.TextField()
    requested_last_working_day = models.DateField()
    approved_last_working_day = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Withdrawn', 'Withdrawn')], default='Pending')

# ============================================================================
# PAYROLL ENHANCEMENTS: SALARY REVISION, LOANS, REIMBURSEMENTS
# ============================================================================

class SalaryRevision(Main):
    """Salary Revision / Increment Workflow"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_revisions')
    
    # Previous salary details
    previous_ctc = models.DecimalField(max_digits=15, decimal_places=2)
    previous_gross = models.DecimalField(max_digits=15, decimal_places=2)
    previous_basic = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Revised salary details
    revised_ctc = models.DecimalField(max_digits=15, decimal_places=2)
    revised_gross = models.DecimalField(max_digits=15, decimal_places=2)
    revised_basic = models.DecimalField(max_digits=15, decimal_places=2)
    percentage_increase = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Effective period
    effective_month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    effective_year = models.IntegerField()
    
    # Revision type
    revision_type = models.CharField(max_length=50, choices=[
        ('ANNUAL_INCREMENT', 'Annual Increment'),
        ('PROMOTION', 'Promotion'),
        ('MERIT', 'Merit Increase'),
        ('CORRECTION', 'Correction'),
        ('OTHER', 'Other'),
    ], default='ANNUAL_INCREMENT')
    
    # Reason / Notes
    reason = models.TextField(blank=True, null=True)
    
    # Approval Workflow
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_MANAGER', 'Pending Manager Approval'),
        ('PENDING_HR', 'Pending HR Approval'),
        ('PENDING_FINANCE', 'Pending Finance Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Approvals
    recommended_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommended_revisions')
    approved_by_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='manager_approved_revisions')
    approved_by_hr = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hr_approved_revisions')
    approved_by_finance = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_approved_revisions')
    approved_date = models.DateTimeField(blank=True, null=True)
    
    # Processing
    is_processed = models.BooleanField(default=False)  # Has this revision been applied in payroll
    processed_in_payroll = models.ForeignKey(Payroll, on_delete=models.SET_NULL, null=True, blank=True, related_name='salary_revisions')
    
    # Arrears
    arrears_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Auto-calculated arrears for backdated revisions")
    arrears_paid = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Salary Revision'
        verbose_name_plural = 'Salary Revisions'
        ordering = ['-effective_year', '-effective_month', '-created_at']

    def __str__(self):
        return f"{self.employee.employee_id} - Revision ({self.effective_month}/{self.effective_year})"

    def save(self, *args, **kwargs):
        if self.revised_ctc and self.previous_ctc and self.previous_ctc > 0:
            try:
                pct = (
                    (self.revised_ctc - self.previous_ctc) / self.previous_ctc * Decimal('100')
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                self.percentage_increase = pct if pct <= Decimal('999.99') else Decimal('999.99')
            except Exception:
                self.percentage_increase = Decimal('999.99')
        super().save(*args, **kwargs)


class EmployeeLoan(Main):
    """Employee Loan / Advance Management"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='loans')
    
    loan_type = models.CharField(max_length=50, choices=[
        ('PERSONAL', 'Personal Loan'),
        ('VEHICLE', 'Vehicle Loan'),
        ('HOUSING', 'Housing Loan'),
        ('EMERGENCY', 'Emergency Loan'),
        ('SALARY_ADVANCE', 'Salary Advance'),
        ('OTHER', 'Other'),
    ])
    
    # Loan Details
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0,
        help_text="Annual interest rate in %")
    total_interest = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_payable = models.DecimalField(max_digits=15, decimal_places=2)
    
    # EMI
    emi_amount = models.DecimalField(max_digits=15, decimal_places=2)
    total_emis = models.IntegerField(help_text="Total number of EMIs")
    emi_frequency = models.CharField(max_length=20, choices=[
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
    ], default='MONTHLY')
    
    # Payment Tracking
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_emis = models.IntegerField(default=0)
    outstanding_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Dates
    sanction_date = models.DateField()
    first_emi_date = models.DateField()
    closure_date = models.DateField(blank=True, null=True)
    
    # Approval
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('REJECTED', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='loan_requests')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='loan_approvals')
    approved_date = models.DateTimeField(blank=True, null=True)
    
    purpose = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Employee Loan'
        verbose_name_plural = 'Employee Loans'
        ordering = ['-sanction_date']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_loan_type_display()} ({self.principal_amount})"

    def save(self, *args, **kwargs):
        if not self.total_payable:
            self.total_payable = self.principal_amount + self.total_interest
        if not self.outstanding_amount:
            self.outstanding_amount = self.total_payable
        super().save(*args, **kwargs)


class LoanRepayment(Main):
    """Individual Loan EMI Repayment Record"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(EmployeeLoan, on_delete=models.CASCADE, related_name='repayments')
    payroll = models.ForeignKey(Payroll, on_delete=models.SET_NULL, null=True, blank=True, related_name='loan_repayments')
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()
    
    payment_date = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Loan Repayment'
        verbose_name_plural = 'Loan Repayments'
        unique_together = ('loan', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.loan.employee.employee_id} - EMI {self.month}/{self.year}"


class EmployeeReimbursement(Main):
    """Employee Expense Reimbursement Management"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reimbursements')
    
    expense_type = models.CharField(max_length=50, choices=[
        ('MEDICAL', 'Medical'),
        ('TRAVEL', 'Travel'),
        ('MOBILE', 'Mobile'),
        ('INTERNET', 'Internet'),
        ('CONVEYANCE', 'Conveyance'),
        ('FUEL', 'Fuel'),
        ('FOOD', 'Food'),
        ('STATIONERY', 'Stationery'),
        ('OTHER', 'Other'),
    ])
    
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    expense_date = models.DateField()
    
    # Bill / Document
    bill_document = models.FileField(upload_to='reimbursements/%Y/%m/', blank=True, null=True)
    bill_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Approval
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    applied_date = models.DateField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_reimbursements')
    approved_date = models.DateTimeField(blank=True, null=True)
    
    # Payment
    payroll = models.ForeignKey(Payroll, on_delete=models.SET_NULL, null=True, blank=True, related_name='reimbursements')
    paid_date = models.DateField(blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Employee Reimbursement'
        verbose_name_plural = 'Employee Reimbursements'
        ordering = ['-applied_date']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_expense_type_display()} ({self.amount})"


# ============================================================================
# CORE HR ENHANCEMENTS: FAMILY, EMERGENCY CONTACTS, MULTI-BANK
# ============================================================================

class EmployeeFamily(Main):
    """Family member details for employee (insurance, nomination)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='family_members')
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50, choices=[
        ('SPOUSE', 'Spouse'),
        ('CHILD', 'Child'),
        ('FATHER', 'Father'),
        ('MOTHER', 'Mother'),
        ('SIBLING', 'Sibling'),
        ('OTHER', 'Other'),
    ])
    date_of_birth = models.DateField(blank=True, null=True)
    is_dependent = models.BooleanField(default=False, help_text="Dependent for insurance purposes")
    is_nominee = models.BooleanField(default=False, help_text="Nominee for PF/Gratuity")
    nomination_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True,
        help_text="Percentage of nomination (if nominee)")
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Employee Family Member'
        verbose_name_plural = 'Employee Family Members'
        ordering = ['-is_nominee', 'name']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.name} ({self.get_relationship_display()})"


class EmployeeEmergencyContact(Main):
    """Emergency contacts for employee"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    mobile = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Emergency Contact'
        verbose_name_plural = 'Emergency Contacts'
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.name} ({self.relationship})"


class EmployeeBankAccount(Main):
    """Multi-bank account support for employees"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='bank_accounts')
    account_type = models.CharField(max_length=20, choices=[
        ('PRIMARY', 'Primary'),
        ('SECONDARY', 'Secondary'),
    ], default='SECONDARY')
    account_holder_name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100)
    branch_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=30)
    ifsc_code = models.CharField(max_length=11,
        validators=[RegexValidator(r'^[A-Z]{4}0[A-Z0-9]{6}$', 'Invalid IFSC code')])
    is_verified = models.BooleanField(default=False)
    verified_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Employee Bank Account'
        verbose_name_plural = 'Employee Bank Accounts'
        unique_together = ('employee', 'account_number')

    def __str__(self):
        return f"{self.employee.employee_id} - {self.bank_name} ({self.account_type})"


class EmployeeDocumentVersion(Main):
    """Document version control - never delete, only supersede"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(EmployeeDocument, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    document_file = models.FileField(max_length=255, upload_to='hr/employee_documents_versions/%Y/%m/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_date = models.DateTimeField(auto_now_add=True)
    change_reason = models.CharField(max_length=200, blank=True, null=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Document Version'
        verbose_name_plural = 'Document Versions'
        ordering = ['document', '-version_number']
        unique_together = ('document', 'version_number')

    def __str__(self):
        return f"{self.document.employee.employee_id} - {self.document.document_type} v{self.version_number}"


# ============================================================================
# EXIT MANAGEMENT ENHANCEMENTS: EXIT INTERVIEW, F&F, ALUMNI
# ============================================================================

class ExitClearance(Main):
    """Extended Exit Clearance with department-level tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resignation = models.ForeignKey('Resignation', on_delete=models.CASCADE, related_name='clearances')
    department_code = models.CharField(max_length=50, choices=[
        ('IT', 'Information Technology'),
        ('ADMIN', 'Administration'),
        ('FINANCE', 'Finance'),
        ('PROJECTS', 'Projects'),
        ('HR', 'Human Resources'),
        ('LIBRARY', 'Library'),
        ('SECURITY', 'Security'),
    ], default='HR')
    department_name = models.CharField(max_length=100, blank=True)
    is_cleared = models.BooleanField(default=False)
    cleared_date = models.DateTimeField(blank=True, null=True)
    cleared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    comments = models.TextField(blank=True, null=True)
    checklist_items = models.JSONField(default=list, blank=True, help_text="List of items checked")

    class Meta:
        verbose_name = 'Exit Clearance'
        verbose_name_plural = 'Exit Clearances'
        unique_together = ('resignation', 'department_code')

    def __str__(self):
        return f"{self.resignation.employee.employee_id} - {self.department_name}"


class ExitInterview(Main):
    """Structured exit interview"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resignation = models.ForeignKey('Resignation', on_delete=models.CASCADE, related_name='exit_interviews')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='exit_interviews')
    interview_date = models.DateField(auto_now_add=True)
    interviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conducted_exit_interviews')
    is_anonymous = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ], default='PENDING')
    overall_satisfaction = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    rehire_recommendation = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('YES', 'Yes'), ('NO', 'No'), ('MAYBE', 'Maybe')
    ])
    hr_notes = models.TextField(blank=True, null=True, help_text="HR team notes (confidential)")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Exit Interview'
        verbose_name_plural = 'Exit Interviews'

    def __str__(self):
        return f"{self.employee.employee_id} - {self.interview_date}"


class ExitInterviewResponse(Main):
    """Individual response to exit interview questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(ExitInterview, on_delete=models.CASCADE, related_name='responses')
    question_code = models.CharField(max_length=50)
    question_text = models.TextField()
    response_type = models.CharField(max_length=20, choices=[
        ('text', 'Text'),
        ('choice', 'Multiple Choice'),
        ('rating', 'Rating'),
    ])
    choice_response = models.CharField(max_length=100, blank=True, null=True)
    text_response = models.TextField(blank=True, null=True)
    rating_response = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    options = models.JSONField(default=list, blank=True, help_text="Available options if choice type")
    rating_scale = models.IntegerField(default=5)

    class Meta:
        verbose_name = 'Exit Interview Response'
        verbose_name_plural = 'Exit Interview Responses'

    def __str__(self):
        return f"{self.interview.employee.employee_id} - {self.question_code}: {self.choice_response or self.text_response or self.rating_response}"


class FnFSettlement(Main):
    """Full & Final Settlement Record"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='fnf_settlements')
    resignation = models.ForeignKey('Resignation', on_delete=models.CASCADE, related_name='fnf_settlements', null=True, blank=True)
    exit_date = models.DateField()
    
    # Earnings
    last_month_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    leave_encashment = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gratuity_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    bonus_proration = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_earnings = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Deductions
    notice_recovery = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    loan_recovery = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Totals
    total_earnings = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_settlement = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Approval
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_HR', 'Pending HR Review'),
        ('PENDING_FINANCE', 'Pending Finance Approval'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Audit
    prepared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prepared_fn_f')
    approved_by_hr = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hr_approved_fn_f')
    approved_by_finance = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_approved_fn_f')
    approved_date = models.DateTimeField(blank=True, null=True)
    payment_date = models.DateField(blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Experience letter
    experience_letter_issued = models.BooleanField(default=False)
    relieving_letter_issued = models.BooleanField(default=False)
    form16_issued = models.BooleanField(default=False)
    
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'F&F Settlement'
        verbose_name_plural = 'F&F Settlements'

    def __str__(self):
        return f"{self.employee.employee_id} - F&F ({self.exit_date})"


class FnFSettlementComponent(Main):
    """Component breakdown of F&F Settlement"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    settlement = models.ForeignKey(FnFSettlement, on_delete=models.CASCADE, related_name='components')
    component_code = models.CharField(max_length=50)
    component_label = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    component_type = models.CharField(max_length=20, choices=[
        ('EARNING', 'Earning'),
        ('DEDUCTION', 'Deduction'),
    ])
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'F&F Component'
        verbose_name_plural = 'F&F Components'

    def __str__(self):
        return f"{self.settlement.employee.employee_id} - {self.component_label}: {self.amount}"


class AlumniRecord(Main):
    """Alumni portal - ex-employee access for payslips, Form 16"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='alumni_record')
    exit_date = models.DateField()
    email = models.EmailField(help_text="Personal email for alumni access")
    access_expiry_date = models.DateField(help_text="Access expires 3 years post-exit")
    can_access_payslips = models.BooleanField(default=True)
    can_access_form16 = models.BooleanField(default=True)
    can_download_experience_letter = models.BooleanField(default=True)
    is_rehire_eligible = models.BooleanField(default=True)
    rehire_flag = models.CharField(max_length=50, blank=True, null=True,
        help_text="Blacklist/grey list flag")
    last_access_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Alumni Record'
        verbose_name_plural = 'Alumni Records'

    def __str__(self):
        return f"{self.employee.employee_id} - Alumni (Exit: {self.exit_date})"


# ============================================================================
# ESS / MSS PORTAL ENHANCEMENTS: HELPDESK, ASSET REQUESTS
# ============================================================================

class HRTicket(Main):
    """HR Helpdesk Ticket System"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='hr_tickets')
    
    ticket_type = models.CharField(max_length=50, choices=[
        ('PAYROLL_QUERY', 'Payroll Query'),
        ('CERTIFICATE_REQUEST', 'Certificate Request'),
        ('IT_ACCESS', 'IT Access Request'),
        ('POLICY_CLARIFICATION', 'Policy Clarification'),
        ('BENEFITS', 'Benefits Query'),
        ('LEAVE_ISSUE', 'Leave Issue'),
        ('ATTENDANCE_ISSUE', 'Attendance Issue'),
        ('OTHER', 'Other'),
    ])
    
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=[
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ], default='MEDIUM')
    
    status = models.CharField(max_length=20, choices=[
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ], default='OPEN')
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    resolved_date = models.DateTimeField(blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)
    
    attachment = models.FileField(upload_to='hr_tickets/%Y/%m/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'HR Ticket'
        verbose_name_plural = 'HR Tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_ticket_type_display()}: {self.subject[:50]}"


class HRTicketConversation(Main):
    """Conversation/updates on HR tickets"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(HRTicket, on_delete=models.CASCADE, related_name='conversations')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    attachment = models.FileField(upload_to='hr_ticket_conversations/%Y/%m/', blank=True, null=True)
    is_internal = models.BooleanField(default=False, help_text="Internal note not visible to employee")

    class Meta:
        verbose_name = 'Ticket Conversation'
        verbose_name_plural = 'Ticket Conversations'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.ticket.id} - {self.user.email}: {self.message[:50]}"


class AssetRequest(Main):
    """Employee asset request (laptop, SIM, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='asset_requests')
    
    asset_type = models.CharField(max_length=50, choices=[
        ('LAPTOP', 'Laptop'),
        ('MOBILE', 'Mobile Phone'),
        ('SIM_CARD', 'SIM Card'),
        ('MONITOR', 'Monitor'),
        ('KEYBOARD', 'Keyboard/Mouse'),
        ('ACCESS_CARD', 'Access Card'),
        ('OTHER', 'Other'),
    ])
    
    reason = models.TextField()
    urgency = models.CharField(max_length=20, choices=[
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ], default='MEDIUM')
    
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('ALLOCATED', 'Allocated'),
        ('RETURNED', 'Returned'),
    ], default='PENDING')
    
    asset_serial = models.CharField(max_length=100, blank=True, null=True, help_text="Serial number when allocated")
    allocated_date = models.DateField(blank=True, null=True)
    returned_date = models.DateField(blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_asset_requests')
    
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Asset Request'
        verbose_name_plural = 'Asset Requests'

    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_asset_type_display()}"


# ============================================================================
# PERFORMANCE ENHANCEMENTS: OKR, 360 FEEDBACK, PIP, CALIBRATION
# ============================================================================

class OKR(Main):
    """OKR Framework - Objectives and Key Results"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='okrs')
    cycle = models.ForeignKey('AppraisalCycle', on_delete=models.CASCADE)
    
    objective = models.TextField(help_text="The Objective (what you want to achieve)")
    key_result = models.TextField(help_text="The Key Result (how you measure success)")
    
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    progress_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    start_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    target_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=[
        ('ON_TRACK', 'On Track'),
        ('AT_RISK', 'At Risk'),
        ('BEHIND', 'Behind'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ], default='ON_TRACK')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'OKR'
        verbose_name_plural = 'OKRs'

    def __str__(self):
        return f"{self.employee.employee_id} - {self.objective[:50]}"


class Feedback360(Main):
    """360° Feedback Request"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='feedback_received')
    reviewer = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='feedback_given')
    cycle = models.ForeignKey('AppraisalCycle', on_delete=models.CASCADE)
    
    relationship = models.CharField(max_length=50, choices=[
        ('PEER', 'Peer'),
        ('SUBORDINATE', 'Subordinate'),
        ('MANAGER', 'Manager'),
        ('SELF', 'Self'),
        ('CUSTOMER', 'Customer/External'),
    ])
    
    is_anonymous = models.BooleanField(default=True)
    is_submitted = models.BooleanField(default=False)
    submitted_date = models.DateTimeField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    
    # Ratings
    overall_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    strengths = models.TextField(blank=True, null=True)
    areas_for_improvement = models.TextField(blank=True, null=True)
    additional_comments = models.TextField(blank=True, null=True)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = '360° Feedback'
        verbose_name_plural = '360° Feedbacks'
        unique_together = ('employee', 'reviewer', 'cycle', 'relationship')

    def __str__(self):
        return f"{self.reviewer.get_full_name()} → {self.employee.get_full_name()} ({self.get_relationship_display()})"


class PIPlan(Main):
    """Performance Improvement Plan"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='pip_plans')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_pips')
    
    reason = models.TextField()
    goals = models.JSONField(default=list, help_text="List of improvement goals")
    
    start_date = models.DateField()
    review_date_30 = models.DateField(blank=True, null=True)
    review_date_60 = models.DateField(blank=True, null=True)
    review_date_90 = models.DateField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=[
        ('ACTIVE', 'Active'),
        ('IMPROVED', 'Improved - Completed'),
        ('EXTENDED', 'Extended'),
        ('TERMINATED', 'Terminated'),
    ], default='ACTIVE')
    
    manager_checkin_log = models.TextField(blank=True, null=True, help_text="Manager check-in notes")
    outcome_notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Performance Improvement Plan'
        verbose_name_plural = 'Performance Improvement Plans'

    def __str__(self):
        return f"{self.employee.employee_id} - PIP ({self.start_date})"


class CalibrationSession(Main):
    """Calibration discussion session for rating finalization"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey('AppraisalCycle', on_delete=models.CASCADE, related_name='calibration_sessions')
    name = models.CharField(max_length=200)
    session_date = models.DateTimeField()
    
    participants = models.ManyToManyField(User, related_name='calibration_sessions')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=[
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ], default='SCHEDULED')
    
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Calibration Session'
        verbose_name_plural = 'Calibration Sessions'


# ============================================================================
# TRAINING ENHANCEMENTS: TNI, SKILL MATRIX, ASSESSMENT
# ============================================================================

class Skill(Main):
    """Skill master for skill matrix"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, choices=[
        ('TECHNICAL', 'Technical'),
        ('SOFT_SKILL', 'Soft Skill'),
        ('MANAGEMENT', 'Management'),
        ('DOMAIN', 'Domain/Industry'),
        ('LANGUAGE', 'Language'),
        ('CERTIFICATION', 'Certification'),
    ])
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Skill'
        verbose_name_plural = 'Skills'

    def __str__(self):
        return self.name


class EmployeeSkill(Main):
    """Employee skill assessment"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    
    proficiency = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Beginner, 2=Intermediate, 3=Advanced, 4=Expert, 5=Thought Leader")
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    last_assessed_date = models.DateField(auto_now=True)
    certification = models.CharField(max_length=200, blank=True, null=True)
    certification_expiry = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Employee Skill'
        verbose_name_plural = 'Employee Skills'
        unique_together = ('employee', 'skill')

    def __str__(self):
        return f"{self.employee.employee_id} - {self.skill.name}: {self.proficiency}/5"


class TrainingNeed(Main):
    """Training Need Identification (TNI)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_needs')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, blank=True, null=True)
    
    need_type = models.CharField(max_length=20, choices=[
        ('SKILL_GAP', 'Skill Gap'),
        ('SELF_NOMINATION', 'Self Nomination'),
        ('MANAGER_RECOMMENDED', 'Manager Recommended'),
        ('MANDATORY', 'Mandatory (Compliance)'),
        ('INDUCTION', 'Induction/Training'),
    ])
    
    current_proficiency = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    target_proficiency = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    gap = models.IntegerField(editable=False)
    
    suggested_program = models.CharField(max_length=200, blank=True, null=True)
    priority = models.CharField(max_length=20, choices=[
        ('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical'),
    ], default='MEDIUM')
    
    status = models.CharField(max_length=20, choices=[
        ('IDENTIFIED', 'Identified'),
        ('TRAINING_SCHEDULED', 'Training Scheduled'),
        ('COMPLETED', 'Completed'),
        ('DEFERRED', 'Deferred'),
    ], default='IDENTIFIED')
    
    target_completion_date = models.DateField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Training Need'
        verbose_name_plural = 'Training Needs'

    def save(self, *args, **kwargs):
        self.gap = self.target_proficiency - self.current_proficiency
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_id} - {self.skill.name if self.skill else 'N/A'}"


class TrainingAssessment(Main):
    """Pre/Post training assessment"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nomination = models.ForeignKey('TrainingNomination', on_delete=models.CASCADE, related_name='assessments')
    assessment_type = models.CharField(max_length=20, choices=[
        ('PRE', 'Pre-Training'),
        ('POST', 'Post-Training'),
    ])
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    feedback = models.TextField(blank=True, null=True)
    assessed_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Training Assessment'
        verbose_name_plural = 'Training Assessments'
        unique_together = ('nomination', 'assessment_type')

    def __str__(self):
        return f"{self.nomination.employee.employee_id} - {self.get_assessment_type_display()} ({self.score}/{self.max_score})"


class TrainingCost(Main):
    """Training cost tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey('TrainingProgram', on_delete=models.CASCADE, related_name='costs')
    cost_type = models.CharField(max_length=50, choices=[
        ('VENUE', 'Venue'),
        ('TRAINER', 'Trainer Fee'),
        ('MATERIAL', 'Material'),
        ('TRAVEL', 'Travel'),
        ('FOOD', 'Food & Accommodation'),
        ('VENDOR', 'Vendor Fee'),
        ('OTHER', 'Other'),
    ])
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_by_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Training Cost'
        verbose_name_plural = 'Training Costs'

    def __str__(self):
        return f"{self.program.name} - {self.get_cost_type_display()}: {self.amount}"


# ============================================================================
# RECRUITMENT ENHANCEMENTS: INTERVIEW, OFFER, BGV, ONBOARDING
# ============================================================================

class InterviewSchedule(Main):
    """Interview scheduling with calendar integration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey('JobApplication', on_delete=models.CASCADE, related_name='interviews')
    
    interview_type = models.CharField(max_length=50, choices=[
        ('L1', 'Level 1 - Technical'),
        ('L2', 'Level 2 - Senior Technical'),
        ('HR', 'HR Round'),
        ('MANAGERIAL', 'Managerial'),
        ('PANEL', 'Panel Discussion'),
    ])
    
    scheduled_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    
    interviewers = models.ManyToManyField(User, related_name='scheduled_interviews')
    interview_mode = models.CharField(max_length=20, choices=[
        ('IN_PERSON', 'In Person'),
        ('VIDEO', 'Video Call'),
        ('PHONE', 'Phone Call'),
    ], default='VIDEO')
    meeting_link = models.URLField(blank=True, null=True, help_text="Google Meet/Zoom link")
    
    status = models.CharField(max_length=20, choices=[
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('RESCHEDULED', 'Rescheduled'),
    ], default='SCHEDULED')
    
    feedback = models.TextField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback_submitted = models.BooleanField(default=False)
    
    calendar_event_id = models.CharField(max_length=200, blank=True, null=True,
        help_text="Google/Outlook calendar event ID")
    
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Interview Schedule'
        verbose_name_plural = 'Interview Schedules'
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.application.candidate.email} - {self.get_interview_type_display()}"


class OfferLetter(Main):
    """Offer letter management"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey('JobApplication', on_delete=models.CASCADE, related_name='offer_letters')
    candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='offer_letters')
    requisition = models.ForeignKey('JobRequisition', on_delete=models.CASCADE, related_name='offer_letters')
    
    offer_date = models.DateField()
    joining_date = models.DateField()
    
    # Compensation
    ctc = models.DecimalField(max_digits=15, decimal_places=2)
    gross_salary = models.DecimalField(max_digits=15, decimal_places=2)
    basic_salary = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Offer details
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    work_location = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE, default='PERMANENT')
    probation_months = models.IntegerField(default=6)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('COUNTERED', 'Countered'),
        ('EXPIRED', 'Expired'),
    ], default='DRAFT')
    
    sent_date = models.DateTimeField(blank=True, null=True)
    response_date = models.DateTimeField(blank=True, null=True)
    acceptance_letter = models.FileField(upload_to='offer_acceptances/%Y/%m/', blank=True, null=True)
    
    # Document
    offer_document = models.FileField(upload_to='offer_letters/%Y/%m/', blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Offer Letter'
        verbose_name_plural = 'Offer Letters'

    def __str__(self):
        return f"{self.candidate.email} - {self.status}"


class BGVCheck(Main):
    """Background Verification tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='bgv_checks')
    offer = models.ForeignKey('OfferLetter', on_delete=models.CASCADE, related_name='bgv_checks', null=True, blank=True)
    
    vendor_name = models.CharField(max_length=100, blank=True, null=True,
        help_text="BGV vendor like AuthBridge, SpringVerify")
    vendor_reference = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=30, choices=[
        ('NOT_INITIATED', 'Not Initiated'),
        ('INITIATED', 'Initiated'),
        ('IN_PROGRESS', 'In Progress'),
        ('CLEAR', 'Clear'),
        ('DISCREPANT', 'Discrepant'),
    ], default='NOT_INITIATED')
    
    # Verification types
    identity_verified = models.BooleanField(default=False)
    address_verified = models.BooleanField(default=False)
    education_verified = models.BooleanField(default=False)
    employment_verified = models.BooleanField(default=False)
    criminal_verified = models.BooleanField(default=False)
    
    initiated_date = models.DateField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)
    report_file = models.FileField(upload_to='bgv_reports/%Y/%m/', blank=True, null=True)
    
    remarks = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'BGV Check'
        verbose_name_plural = 'BGV Checks'

    def __str__(self):
        return f"{self.candidate.email} - BGV: {self.status}"


class OnboardingTask(Main):
    """Onboarding checklist items"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='onboarding_tasks')
    
    task_type = models.CharField(max_length=30, choices=[
        ('PRE_JOINING', 'Pre-Joining'),
        ('DAY_1', 'Day 1'),
        ('DAY_7', 'Day 7'),
        ('DAY_30', 'Day 30'),
        ('DAY_60', 'Day 60'),
        ('DAY_90', 'Day 90'),
    ])
    
    task_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='onboarding_tasks_assigned')
    
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(blank=True, null=True)
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='onboarding_tasks_completed')
    
    due_date = models.DateField(blank=True, null=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Onboarding Task'
        verbose_name_plural = 'Onboarding Tasks'
        ordering = ['task_type', 'order']

    def __str__(self):
        return f"{self.employee.employee_id} - {self.task_name}"


# ============================================================================
# PHASE 3: STATUTORY COMPLIANCE
# ============================================================================

# -------- PROVIDENT FUND (PF) --------

class PFConfiguration(Main):
    """PF Configuration Master"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    employee_contribution_pct = models.DecimalField(max_digits=5, decimal_places=2, default=12.00,
        help_text="Employee PF contribution % of Basic+DA")
    employer_epf_pct = models.DecimalField(max_digits=5, decimal_places=2, default=3.67,
        help_text="Employer EPF contribution % of Basic+DA")
    employer_eps_pct = models.DecimalField(max_digits=5, decimal_places=2, default=8.33,
        help_text="Employer EPS contribution % of Basic+DA")
    employer_edli_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.50,
        help_text="EDLI contribution % of Basic+DA")
    employer_admin_charges_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)
    edli_admin_charges_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.01)

    wage_ceiling = models.DecimalField(max_digits=15, decimal_places=2, default=15000.00,
        help_text="Statutory wage ceiling for PF eligibility")
    eps_max_pensionable_salary = models.DecimalField(max_digits=15, decimal_places=2, default=15000.00,
        help_text="Max salary considered for EPS pension calculation")

    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'PF Configuration'
        verbose_name_plural = 'PF Configurations'

    def __str__(self):
        return f"PF Config effective {self.effective_from}"


class PFContribution(Main):
    """Monthly PF Contribution Record per Employee"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='pf_contributions')
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='pf_contributions', null=True, blank=True)

    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()

    # Wages
    basic_da = models.DecimalField(max_digits=15, decimal_places=2, help_text="Basic + DA for the month")
    gross_salary = models.DecimalField(max_digits=15, decimal_places=2)

    # Contributions
    employee_pf = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employer_epf = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employer_eps = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employer_edli = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employer_admin_charges = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    edli_admin_charges = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    total_employee_contribution = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_employer_contribution = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # UAN & KYC
    uan = models.CharField(max_length=12, blank=True, null=True)
    is_ecr_generated = models.BooleanField(default=False)
    ecr_file = models.FileField(upload_to='pf_ecr/%Y/%m/', blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'month', 'year')
        verbose_name = 'PF Contribution'
        verbose_name_plural = 'PF Contributions'
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.employee.employee_id} PF - {self.month}/{self.year}"


# -------- EMPLOYEE STATE INSURANCE (ESI) --------

class ESIConfiguration(Main):
    """ESI Configuration Master"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    employee_contribution_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.75,
        help_text="Employee ESI contribution % of gross salary")
    employer_contribution_pct = models.DecimalField(max_digits=5, decimal_places=2, default=3.25,
        help_text="Employer ESI contribution % of gross salary")
    wage_ceiling = models.DecimalField(max_digits=15, decimal_places=2, default=21000.00,
        help_text="Gross salary ceiling for ESI eligibility")

    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'ESI Configuration'
        verbose_name_plural = 'ESI Configurations'

    def __str__(self):
        return f"ESI Config effective {self.effective_from}"


class ESIContribution(Main):
    """Monthly ESI Contribution Record per Employee"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='esi_contributions')
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='esi_contributions', null=True, blank=True)

    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()

    gross_salary = models.DecimalField(max_digits=15, decimal_places=2)
    employee_contribution = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employer_contribution = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_contribution = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    ip_number = models.CharField(max_length=20, blank=True, null=True, help_text="Insured Person Number")
    is_challan_generated = models.BooleanField(default=False)

    class Meta:
        unique_together = ('employee', 'month', 'year')
        verbose_name = 'ESI Contribution'
        verbose_name_plural = 'ESI Contributions'

    def __str__(self):
        return f"{self.employee.employee_id} ESI - {self.month}/{self.year}"


# -------- PROFESSIONAL TAX (PT) --------

class ProfessionalTaxSlab(Main):
    """Professional Tax Slab Configuration per State"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    state = models.CharField(max_length=100)

    # Slab
    salary_from = models.DecimalField(max_digits=15, decimal_places=2)
    salary_to = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)

    frequency = models.CharField(max_length=20, choices=[
        ('MONTHLY', 'Monthly'),
        ('HALF_YEARLY', 'Half-Yearly'),
        ('ANNUAL', 'Annual'),
    ], default='MONTHLY')

    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Professional Tax Slab'
        verbose_name_plural = 'Professional Tax Slabs'
        ordering = ['state', 'salary_from']

    def __str__(self):
        return f"PT - {self.state} ({self.salary_from} to {self.salary_to or '∞'})"


class PTContribution(Main):
    """Professional Tax Deduction Record per Employee"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='pt_contributions')
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='pt_contributions', null=True, blank=True)

    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()

    gross_salary = models.DecimalField(max_digits=15, decimal_places=2)
    pt_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    state = models.CharField(max_length=100)

    class Meta:
        unique_together = ('employee', 'month', 'year')
        verbose_name = 'PT Deduction'
        verbose_name_plural = 'PT Deductions'

    def __str__(self):
        return f"{self.employee.employee_id} PT - {self.month}/{self.year}"


# -------- TAX DEDUCTED AT SOURCE (TDS) --------

class TDSConfiguration(Main):
    """TDS Configuration Master"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    financial_year = models.CharField(max_length=9, unique=True)

    enable_old_regime = models.BooleanField(default=True)
    enable_new_regime = models.BooleanField(default=True)

    old_regime_slabs = models.JSONField(default=dict, blank=True)
    new_regime_slabs = models.JSONField(default=dict, blank=True)

    standard_deduction_old = models.DecimalField(max_digits=15, decimal_places=2, default=50000.00)
    standard_deduction_new = models.DecimalField(max_digits=15, decimal_places=2, default=75000.00)

    education_cess_pct = models.DecimalField(max_digits=5, decimal_places=2, default=4.00)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'TDS Configuration'
        verbose_name_plural = 'TDS Configurations'

    def __str__(self):
        return f"TDS Config FY {self.financial_year}"


class InvestmentDeclaration(Main):
    """Employee Investment Declaration (Form 12BB)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='investment_declarations')
    financial_year = models.CharField(max_length=9)

    tax_regime = models.CharField(max_length=20, choices=[('OLD', 'Old Regime'), ('NEW', 'New Regime')], default='NEW')

    section_80c_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    section_80d_self_family = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    section_80d_parents = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    section_80g_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    hra_rent_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    lta_claimed = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    home_loan_interest = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    nps_employee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    is_submitted = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    submitted_date = models.DateTimeField(blank=True, null=True)
    approved_date = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    proof_document = models.FileField(upload_to='investment_proofs/%Y/%m/', blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'financial_year')
        verbose_name = 'Investment Declaration'
        verbose_name_plural = 'Investment Declarations'

    def __str__(self):
        return f"{self.employee.employee_id} - {self.financial_year}"


class TDSCalculation(Main):
    """Monthly TDS Calculation per Employee"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='tds_calculations')
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='tds_calculations', null=True, blank=True)
    financial_year = models.CharField(max_length=9)

    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()

    tax_regime = models.CharField(max_length=20, choices=[('OLD', 'Old Regime'), ('NEW', 'New Regime')], default='NEW')

    ytd_gross_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ytd_exemptions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ytd_standard_deduction = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ytd_deductions_80c = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ytd_other_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ytd_taxable_income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ytd_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ytd_cess = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ytd_total_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ytd_tds_deducted = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    current_month_tds = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        unique_together = ('employee', 'financial_year', 'month')
        verbose_name = 'TDS Calculation'
        verbose_name_plural = 'TDS Calculations'

    def __str__(self):
        return f"{self.employee.employee_id} TDS - {self.month}/{self.year}"


# -------- GRATUITY --------

class GratuityConfiguration(Main):
    """Gratuity Calculation Rules"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    formula_numerator = models.IntegerField(default=15,
        help_text="Number of days salary per year of service (15 as per Act)")
    formula_denominator = models.IntegerField(default=26,
        help_text="Days in a month (26 as per standard)")
    min_service_years = models.IntegerField(default=5,
        help_text="Minimum years of service for gratuity eligibility")

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Gratuity Configuration'
        verbose_name_plural = 'Gratuity Configurations'

    def __str__(self):
        return f"Gratuity Config ({self.formula_numerator}/{self.formula_denominator})"


class GratuityCalculation(Main):
    """Gratuity Calculation per Employee"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='gratuity_calculations')

    date_of_joining = models.DateField()
    date_of_exit = models.DateField()
    years_of_service = models.DecimalField(max_digits=5, decimal_places=2)
    is_eligible = models.BooleanField(default=False)

    last_drawn_basic_da = models.DecimalField(max_digits=15, decimal_places=2)
    gratuity_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    monthly_provision_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
        help_text="Monthly provision set aside")

    calculated_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Gratuity Calculation'
        verbose_name_plural = 'Gratuity Calculations'

    def __str__(self):
        return f"{self.employee.employee_id} - Gratuity: {self.gratuity_amount}"


# -------- BONUS --------

class BonusConfiguration(Main):
    """Bonus Calculation Rules"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    financial_year = models.CharField(max_length=9)

    wage_ceiling = models.DecimalField(max_digits=15, decimal_places=2, default=21000.00,
        help_text="Salary ceiling for bonus eligibility (Payment of Bonus Act)")
    minimum_bonus_pct = models.DecimalField(max_digits=5, decimal_places=2, default=8.33)
    maximum_bonus_pct = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)

    allocable_surplus = models.DecimalField(max_digits=15, decimal_places=2, default=0,
        help_text="Allocable surplus for the year")

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Bonus Configuration'
        verbose_name_plural = 'Bonus Configurations'

    def __str__(self):
        return f"Bonus Config FY {self.financial_year}"


class BonusCalculation(Main):
    """Bonus Calculation per Employee"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='bonus_calculations')

    financial_year = models.CharField(max_length=9)

    eligible_salary = models.DecimalField(max_digits=15, decimal_places=2,
        help_text="Salary considered for bonus calculation")
    bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    bonus_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    payout_date = models.DateField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    class Meta:
        unique_together = ('employee', 'financial_year')
        verbose_name = 'Bonus Calculation'
        verbose_name_plural = 'Bonus Calculations'

    def __str__(self):
        return f"{self.employee.employee_id} Bonus - {self.financial_year}"


# -------- COMPLIANCE CALENDAR --------

class ComplianceCalendarEntry(Main):
    """Compliance Calendar for statutory dues and filings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    compliance_type = models.CharField(max_length=50, choices=[
        ('PF', 'Provident Fund'),
        ('ESI', 'Employee State Insurance'),
        ('PT', 'Professional Tax'),
        ('TDS', 'TDS'),
        ('LWF', 'Labour Welfare Fund'),
        ('GRATUITY', 'Gratuity'),
        ('BONUS', 'Bonus'),
    ])

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    due_date = models.DateField()
    frequency = models.CharField(max_length=20, choices=[
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('HALF_YEARLY', 'Half-Yearly'),
        ('ANNUAL', 'Annual'),
    ])

    period_month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)], blank=True, null=True)
    period_year = models.IntegerField()
    period_quarter = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)], blank=True, null=True)
    period_half = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(2)], blank=True, null=True)

    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
        ('WAIVED', 'Waived'),
    ], default='PENDING')

    completed_date = models.DateTimeField(blank=True, null=True)
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Challan/Return reference")

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Compliance Calendar'
        verbose_name_plural = 'Compliance Calendar Entries'
        ordering = ['due_date']

    def __str__(self):
        return f"{self.get_compliance_type_display()} - {self.title} (Due: {self.due_date})"


# ============================================================================
# LABOUR WELFARE FUND (LWF) — Section 6.4
# ============================================================================

class LWFConfiguration(Main):
    """Labour Welfare Fund Slab Configuration per State"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    state = models.CharField(max_length=100)

    # Contribution amounts
    employee_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    employer_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    frequency = models.CharField(max_length=20, choices=[
        ('MONTHLY', 'Monthly'),
        ('HALF_YEARLY', 'Half-Yearly'),
        ('ANNUAL', 'Annual'),
    ], default='HALF_YEARLY', help_text="Most states: June & December")

    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'LWF Configuration'
        verbose_name_plural = 'LWF Configurations'
        ordering = ['state']
        unique_together = ('state', 'effective_from')

    def __str__(self):
        return f"LWF - {self.state} (Emp: ₹{self.employee_contribution}, Employer: ₹{self.employer_contribution})"


class LWFContribution(Main):
    """LWF Deduction Record per Employee"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='lwf_contributions')
    payroll = models.ForeignKey(
        'Payroll', on_delete=models.SET_NULL, null=True, blank=True, related_name='lwf_contributions'
    )
    config = models.ForeignKey(LWFConfiguration, on_delete=models.SET_NULL, null=True, blank=True)

    period = models.CharField(max_length=20, choices=[
        ('JAN_JUN', 'January–June'),
        ('JUL_DEC', 'July–December'),
        ('ANNUAL', 'Annual'),
    ])
    year = models.IntegerField()
    state = models.CharField(max_length=100)

    employee_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    employer_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_challan_generated = models.BooleanField(default=False)
    challan_reference = models.CharField(max_length=100, blank=True, null=True)
    paid_date = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = 'LWF Contribution'
        verbose_name_plural = 'LWF Contributions'
        ordering = ['-year', 'state']
        unique_together = ('employee', 'period', 'year')

    def __str__(self):
        return f"{self.employee.employee_id} LWF - {self.period}/{self.year}"

    def save(self, *args, **kwargs):
        self.total_contribution = self.employee_contribution + self.employer_contribution
        super().save(*args, **kwargs)


# ============================================================================
# OVERTIME MANAGEMENT — Section 4.5
# ============================================================================

class OvertimeRequest(Main):
    """Overtime Request and Approval Workflow"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='overtime_requests')
    attendance = models.ForeignKey(
        'Attendance', on_delete=models.SET_NULL, null=True, blank=True, related_name='overtime_requests'
    )

    # Overtime details
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    ot_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    reason = models.TextField()

    # Rate (1.5x or 2x)
    ot_rate_multiplier = models.DecimalField(
        max_digits=3, decimal_places=1, default=1.5,
        help_text="1.5 for regular OT, 2.0 for holiday/night OT (as per Factories Act)"
    )

    # Calculated amount (auto-filled on payroll processing)
    ot_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Approval
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PROCESSED', 'Processed in Payroll'),
    ], default='PENDING')

    approved_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_overtime_requests'
    )
    approved_date = models.DateTimeField(blank=True, null=True)
    approval_comment = models.TextField(blank=True, null=True)

    # Payroll linkage
    payroll = models.ForeignKey(
        'Payroll', on_delete=models.SET_NULL, null=True, blank=True, related_name='overtime_requests'
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Overtime Request'
        verbose_name_plural = 'Overtime Requests'
        ordering = ['-date']
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"{self.employee.employee_id} - OT {self.date} ({self.ot_hours}h)"

    def calculate_ot_hours(self):
        """Calculate OT hours from start/end time"""
        from datetime import datetime, date as d, timedelta
        if self.start_time and self.end_time:
            start = datetime.combine(d.today(), self.start_time)
            end = datetime.combine(d.today(), self.end_time)
            if end <= start:
                end += timedelta(days=1)
            diff = end - start
            self.ot_hours = round(diff.total_seconds() / 3600, 2)
        return self.ot_hours


# ============================================================================
# SHIFT SWAP REQUEST — Section 4.2
# ============================================================================

class ShiftSwapRequest(Main):
    """Shift Swap Request between Employees"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requesting_employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='shift_swap_requests_made'
    )
    target_employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='shift_swap_requests_received'
    )

    # Original shifts
    requesting_shift_date = models.DateField(help_text="Date requesting employee wants to swap FROM")
    target_shift_date = models.DateField(help_text="Date requesting employee wants to swap TO")

    requesting_shift = models.ForeignKey(
        'Shift', on_delete=models.SET_NULL, null=True, blank=True, related_name='swap_requests_from'
    )
    target_shift = models.ForeignKey(
        'Shift', on_delete=models.SET_NULL, null=True, blank=True, related_name='swap_requests_to'
    )

    reason = models.TextField()

    # Workflow: Employee → Target Employee Consent → Manager Approval
    target_employee_consented = models.BooleanField(null=True, blank=True, help_text="None=Pending, True=Accepted, False=Declined")
    target_consent_date = models.DateTimeField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=[
        ('PENDING_CONSENT', 'Pending Target Employee Consent'),
        ('PENDING_MANAGER', 'Pending Manager Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn'),
    ], default='PENDING_CONSENT')

    approved_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_shift_swaps'
    )
    approved_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Shift Swap Request'
        verbose_name_plural = 'Shift Swap Requests'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.requesting_employee.employee_id} ↔ {self.target_employee.employee_id} "
            f"({self.requesting_shift_date} ↔ {self.target_shift_date})"
        )


# ============================================================================
# ATTENDANCE REGULARIZATION REQUEST — Section 4.4 (Formal Approval Workflow)
# ============================================================================

class AttendanceRegularizationRequest(Main):
    """Formal Attendance Regularization Request with Manager Approval Workflow"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='regularization_requests')
    attendance = models.ForeignKey(
        'Attendance', on_delete=models.CASCADE, related_name='regularization_requests'
    )

    # What the employee is requesting
    requested_check_in = models.TimeField(blank=True, null=True)
    requested_check_out = models.TimeField(blank=True, null=True)
    requested_status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, blank=True, null=True)

    reason = models.TextField()

    # Approval
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ], default='PENDING')

    approved_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_regularizations'
    )
    approved_date = models.DateTimeField(blank=True, null=True)
    approval_comment = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Attendance Regularization Request'
        verbose_name_plural = 'Attendance Regularization Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.employee_id} - Regularization ({self.attendance.date})"

    def apply(self):
        """Apply approved regularization to the attendance record"""
        if self.status == 'APPROVED':
            att = self.attendance
            if self.requested_check_in:
                att.check_in_time = self.requested_check_in
            if self.requested_check_out:
                att.check_out_time = self.requested_check_out
            if self.requested_status:
                att.status = self.requested_status
            att.is_regularized = True
            att.regularized_by = self.approved_by
            att.regularization_reason = self.reason
            att.calculate_working_hours()
            att.save()


# ============================================================================
# STATUTORY COMPLIANCE FORMS & ENHANCEMENTS
# ============================================================================

class VPFContribution(Main):
    """Voluntary Provident Fund (VPF) Contribution Tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='vpf_contributions')
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='vpf_contributions', null=True, blank=True)
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()
    vpf_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Additional PF contribution % above statutory 12%")
    vpf_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = 'VPF Contribution'
        verbose_name_plural = 'VPF Contributions'
        unique_together = ('employee', 'month', 'year')
        ordering = ['-year', '-month']
    def __str__(self):
        return f"{self.employee.employee_id} VPF - {self.month}/{self.year} ({self.vpf_percentage}%)"


class PFStatement(Main):
    """PF statutory forms tracking: Form 2, 10C, 10D, 19, 31, 13, 11."""
    FORM_TYPES = [
        ('FORM_2', 'Form 2 - PF Nomination'),
        ('FORM_10C', 'Form 10C - EPS Withdrawal'),
        ('FORM_10D', 'Form 10D - Pension Claim'),
        ('FORM_19', 'Form 19 - PF Final Withdrawal'),
        ('FORM_31', 'Form 31 - PF Advance'),
        ('FORM_13', 'Form 13 - Transfer Claim'),
        ('FORM_11', 'Form 11 - New Employee Declaration'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='pf_statements')
    form_type = models.CharField(max_length=20, choices=FORM_TYPES)
    form_date = models.DateField()
    form_file = models.FileField(upload_to='pf_forms/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'), ('SUBMITTED', 'Submitted'),
        ('ACKNOWLEDGED', 'Acknowledged'), ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ], default='PENDING')
    epfo_reference = models.CharField(max_length=100, blank=True, null=True, help_text="EPFO acknowledgment/claim ID")
    submitted_date = models.DateTimeField(blank=True, null=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        verbose_name = 'PF Statement'
        verbose_name_plural = 'PF Statements'
        ordering = ['-form_date', 'employee']
    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_form_type_display()} ({self.get_status_display()})"


class ESICard(Main):
    """ESI Card / Insured Person (IP) tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='esi_cards')
    ip_number = models.CharField(max_length=50, unique=True, help_text="Insured Person Number")
    name_as_per_card = models.CharField(max_length=200, blank=True, null=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    card_file = models.FileField(upload_to='esi_cards/%Y/%m/', blank=True, null=True)
    dependents = models.JSONField(default=list, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    remarks = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = 'ESI Card'
        verbose_name_plural = 'ESI Cards'
    def __str__(self):
        return f"{self.employee.employee_id} - IP: {self.ip_number}"


class LowerDeductionCertificate(Main):
    """Form 15G / 15H - Lower/No TDS deduction certificate."""
    CERTIFICATE_TYPES = [
        ('FORM_15G', 'Form 15G - Lower TDS (Below 60 years)'),
        ('FORM_15H', 'Form 15H - No TDS (Senior Citizen 60+)'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='lower_deduction_certs')
    financial_year = models.CharField(max_length=9)
    certificate_type = models.CharField(max_length=20, choices=CERTIFICATE_TYPES)
    estimated_total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    estimated_tax_due = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    reason_for_no_tax = models.TextField(blank=True, null=True)
    submitted_date = models.DateField()
    certificate_file = models.FileField(upload_to='form_15gh/%Y/%m/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verified_date = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        verbose_name = 'Lower Deduction Certificate'
        verbose_name_plural = 'Lower Deduction Certificates (15G/15H)'
        unique_together = ('employee', 'financial_year', 'certificate_type')
    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_certificate_type_display()} ({self.financial_year})"


class PTEnrollment(Main):
    """Professional Tax Enrollment Certificate tracking per state."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='pt_enrollments')
    state = models.CharField(max_length=100)
    enrollment_number = models.CharField(max_length=100, blank=True, null=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    certificate_file = models.FileField(upload_to='pt_enrollments/%Y/%m/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    remarks = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = 'PT Enrollment'
        verbose_name_plural = 'PT Enrollments'
        unique_together = ('employee', 'state')
    def __str__(self):
        return f"{self.employee.employee_id} - PT Enrollment ({self.state})"


class InternationalWorker(Main):
    """International Workers (IW) tracking for separate PF rules."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='international_worker')
    passport_number = models.CharField(max_length=50)
    country_of_origin = models.CharField(max_length=100)
    visa_type = models.CharField(max_length=100, blank=True, null=True)
    visa_expiry_date = models.DateField(blank=True, null=True)
    employee_pf_pct = models.DecimalField(max_digits=5, decimal_places=2, default=12.00)
    employer_pf_pct = models.DecimalField(max_digits=5, decimal_places=2, default=12.00)
    has_ssa = models.BooleanField(default=False, help_text="Country has Social Security Agreement")
    ssa_country = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = 'International Worker'
        verbose_name_plural = 'International Workers'
    def __str__(self):
        return f"{self.employee.employee_id} - IW ({self.country_of_origin})"


class Form12BA(Main):
    """Form 12BA - Perquisite Statement for Form 16 Part B."""
    PERQUISITE_TYPES = [
        ('RENT_FREE_ACCOMMODATION', 'Rent-Free Accommodation'),
        ('CONCESSIONAL_RENT', 'Concessional Rent Accommodation'),
        ('MOTOR_CAR', 'Motor Car'),
        ('SWEEPER_GARDENER', 'Sweeper/Gardener/Servant'),
        ('GAS_ELECTRICITY', 'Gas/Electricity/Water'),
        ('EDUCATION', 'Children Education Allowance'),
        ('TRANSPORT', 'Transport Facility'),
        ('SUNDRY', 'Other Sundry Perquisites'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='form_12ba')
    financial_year = models.CharField(max_length=9)
    perquisite_type = models.CharField(max_length=50, choices=PERQUISITE_TYPES)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    is_taxable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = 'Form 12BA - Perquisite'
        verbose_name_plural = 'Form 12BA - Perquisites'
        ordering = ['-financial_year', 'employee']
    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_perquisite_type_display()} ({self.financial_year})"


class Form24QReturn(Main):
    """Quarterly TDS Return (Form 24Q) tracking and generation."""
    QUARTER_CHOICES = [
        ('Q1', 'Quarter 1 (Apr-Jun)'),
        ('Q2', 'Quarter 2 (Jul-Sep)'),
        ('Q3', 'Quarter 3 (Oct-Dec)'),
        ('Q4', 'Quarter 4 (Jan-Mar)'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    financial_year = models.CharField(max_length=9)
    quarter = models.CharField(max_length=5, choices=QUARTER_CHOICES)
    filing_date = models.DateField()
    due_date = models.DateField()
    token_number = models.CharField(max_length=100, blank=True, null=True, help_text="TRACES token")
    total_deductees = models.IntegerField(default=0)
    total_tds_deducted = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_tds_deposited = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'), ('FILED', 'Filed'), ('CORRECTED', 'Corrected Return Filed'),
    ], default='PENDING')
    return_file = models.FileField(upload_to='form_24q/%Y/%m/', blank=True, null=True)
    challan_file = models.FileField(upload_to='challan_281/%Y/%m/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = 'Form 24Q Return'
        verbose_name_plural = 'Form 24Q Returns'
        unique_together = ('financial_year', 'quarter')
        ordering = ['-financial_year', 'quarter']
    def __str__(self):
        return f"Form 24Q - {self.financial_year} {self.get_quarter_display()}"

# ============================================================================
# RECRUITMENT & ONBOARDING ENHANCEMENTS
# ============================================================================

class InternalJobPosting(Main):
    """
    Internal Job Portal (IJP) — Internal job postings visible to current employees.
    Enables internal-first hiring policy before external posting.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requisition = models.ForeignKey('JobRequisition', on_delete=models.CASCADE, related_name='internal_postings',
        null=True, blank=True, help_text="Linked job requisition (if any)")

    # Posting Details
    title = models.CharField(max_length=200, help_text="Job title as shown to employees")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    designation = models.ForeignKey('Designation', on_delete=models.SET_NULL, null=True)
    work_location = models.ForeignKey('WorkLocation', on_delete=models.SET_NULL, null=True)

    description = models.TextField(help_text="Detailed job description")
    requirements = models.TextField(blank=True, null=True, help_text="Required qualifications and skills")
    responsibilities = models.TextField(blank=True, null=True)

    # Details
    vacancies = models.PositiveIntegerField(default=1)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE, default='PERMANENT')
    grade = models.CharField(max_length=20, blank=True, null=True, help_text="Target grade/band")

    # Dates
    posting_date = models.DateField(auto_now_add=True)
    application_deadline = models.DateField(blank=True, null=True)
    expected_joining_date = models.DateField(blank=True, null=True)

    # Status
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('OPEN', 'Open for Applications'),
        ('CLOSED', 'Closed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    # Stats
    total_applications = models.IntegerField(default=0, editable=False)
    shortlisted_count = models.IntegerField(default=0, editable=False)

    is_active = models.BooleanField(default=True)
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Internal Job Posting (IJP)'
        verbose_name_plural = 'Internal Job Postings (IJP)'
        ordering = ['-posting_date']

    def __str__(self):
        return f"IJP: {self.title} ({self.get_status_display()})"


class InternalJobApplication(Main):
    """
    Internal job applications from existing employees for IJP postings.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    posting = models.ForeignKey(InternalJobPosting, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='internal_applications')

    # Application
    cover_note = models.TextField(blank=True, null=True, help_text="Why the employee is interested")
    current_designation = models.CharField(max_length=100, blank=True, null=True)
    current_department = models.CharField(max_length=100, blank=True, null=True)
    relevant_experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    # Manager Endorsement
    manager_endorsed = models.BooleanField(null=True, blank=True,
        help_text="Current manager's endorsement (None=Pending, True=Endorsed, False=Not Endorsed)")
    manager_comment = models.TextField(blank=True, null=True)

    # Status
    STATUS_CHOICES = [
        ('APPLIED', 'Applied'),
        ('SHORTLISTED', 'Shortlisted'),
        ('INTERVIEWED', 'Interviewed'),
        ('SELECTED', 'Selected'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPLIED')

    applied_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Internal Job Application'
        verbose_name_plural = 'Internal Job Applications'
        unique_together = ('posting', 'applicant')
        ordering = ['-applied_date']

    def __str__(self):
        return f"{self.applicant.employee_id} → {self.posting.title}"


class EmployeeReferral(Main):
    """
    Employee Referral Programme — track referrals and bonuses.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referring_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='referrals_made')
    referred_candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='referrals',
        null=True, blank=True)
    requisition = models.ForeignKey('JobRequisition', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='referrals')

    # Referred Person Details (in case candidate not yet in system)
    referred_name = models.CharField(max_length=200)
    referred_email = models.EmailField()
    referred_phone = models.CharField(max_length=20, blank=True, null=True)
    referred_resume = models.FileField(upload_to='referral_resumes/%Y/%m/', blank=True, null=True)

    # Referral Details
    relationship = models.CharField(max_length=100, blank=True, null=True,
        help_text="Relationship with referred person (ex-colleague, friend, etc.)")
    notes = models.TextField(blank=True, null=True)

    # Status Tracking
    STATUS_CHOICES = [
        ('REFERRED', 'Referred'),
        ('CONTACTED', 'Contacted'),
        ('INTERVIEWED', 'Interviewed'),
        ('HIRED', 'Hired - Bonus Due'),
        ('BONUS_PAID', 'Bonus Paid'),
        ('REJECTED', 'Rejected'),
        ('JOINED', 'Joined - Bonus Pending'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REFERRED')

    # Bonus
    bonus_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
        help_text="Referral bonus amount (if applicable)")
    bonus_paid = models.BooleanField(default=False)
    bonus_paid_date = models.DateField(blank=True, null=True)

    referral_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Employee Referral'
        verbose_name_plural = 'Employee Referrals'
        ordering = ['-referral_date']

    def __str__(self):
        return f"Referral by {self.referring_employee.employee_id}: {self.referred_name}"


class OnboardingBuddy(Main):
    """
    Buddy/Mentor assignment for new employees during onboarding.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    new_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='onboarding_buddies')
    buddy = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='buddy_assignments')

    # Assignment details
    role = models.CharField(max_length=20, choices=[
        ('BUDDY', 'Buddy'),
        ('MENTOR', 'Mentor'),
    ], default='BUDDY')

    assigned_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(blank=True, null=True, help_text="Buddy program end date (typically 90 days)")

    # Status
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    # Feedback
    buddy_rating = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating given by new employee to buddy (1-5)")
    new_employee_feedback = models.TextField(blank=True, null=True,
        help_text="New employee's feedback about buddy program")
    buddy_feedback = models.TextField(blank=True, null=True,
        help_text="Buddy's feedback about the new employee")

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Onboarding Buddy'
        verbose_name_plural = 'Onboarding Buddies'
        unique_together = ('new_employee', 'buddy', 'role')

    def __str__(self):
        return f"{self.buddy.employee_id} → {self.new_employee.employee_id} ({self.get_role_display()})"


class PreJoiningDocument(Main):
    """
    Digital document collection for candidates before joining.
    Generates a portal link for candidates to upload documents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.ForeignKey('OfferLetter', on_delete=models.CASCADE, related_name='pre_joining_documents')
    candidate = models.ForeignKey('Candidate', on_delete=models.CASCADE, related_name='pre_joining_docs')

    # Portal access
    portal_token = models.CharField(max_length=64, unique=True, blank=True,
        help_text="Unique token for candidate portal access")
    portal_expiry_date = models.DateField(blank=True, null=True,
        help_text="Portal access expiry date (typically 30 days before joining)")

    # Document types required
    REQUIRED_DOCUMENT_TYPES = [
        ('AADHAAR', 'Aadhaar Card'),
        ('PAN', 'PAN Card'),
        ('PHOTO', 'Passport-size Photo'),
        ('10TH', '10th Marksheet'),
        ('12TH', '12th Marksheet'),
        ('UG_DEGREE', 'UG Degree Certificate'),
        ('PG_DEGREE', 'PG Degree Certificate'),
        ('EXPERIENCE', 'Experience/Relieving Letters'),
        ('SALARY_SLIPS', 'Last 3 Months Salary Slips'),
        ('BANK_DETAILS', 'Bank Account Details Form'),
        ('PF_DECLARATION', 'PF Declaration Form'),
        ('ESI_DECLARATION', 'ESI Declaration Form'),
        ('VACCINATION', 'Vaccination Certificate'),
        ('OTHER', 'Other Documents'),
    ]

    # Status
    STATUS_CHOICES = [
        ('PENDING', 'Pending Upload'),
        ('UPLOADED', 'Uploaded'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected - Re-upload Required'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    last_activity = models.DateTimeField(blank=True, null=True,
        help_text="Last activity timestamp in portal")
    documents_uploaded = models.IntegerField(default=0, help_text="Number of documents uploaded")
    total_documents_required = models.IntegerField(default=13,
        help_text="Total number of documents required")

    # Welcome communication
    welcome_email_sent = models.BooleanField(default=False)
    welcome_email_date = models.DateTimeField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Pre-Joining Document Portal'
        verbose_name_plural = 'Pre-Joining Document Portals'

    def __str__(self):
        return f"Pre-Joining: {self.candidate.email}"

    def save(self, *args, **kwargs):
        import secrets
        if not self.portal_token:
            self.portal_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class OnboardingFeedback(Main):
    """
    Early feedback surveys for new employees (Day 30, Day 60, Day 90).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='onboarding_feedbacks')

    feedback_type = models.CharField(max_length=20, choices=[
        ('DAY_30', 'Day 30 Check-in'),
        ('DAY_60', 'Day 60 Check-in'),
        ('DAY_90', 'Day 90 Check-in'),
    ])

    # Satisfaction Ratings (1-5)
    overall_satisfaction = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="How satisfied are you with your role?")
    onboarding_process = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="How would you rate the onboarding process?")
    buddy_support = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True,
        help_text="How helpful was your buddy/mentor?")
    role_clarity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="How clear are your role and responsibilities?")

    # Open-ended
    what_is_going_well = models.TextField(blank=True, null=True)
    challenges_faced = models.TextField(blank=True, null=True)
    suggestions = models.TextField(blank=True, null=True)

    # Would recommend?
    would_recommend = models.BooleanField(null=True, blank=True,
        help_text="Would you recommend this company to others?")

    submitted_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Onboarding Feedback'
        verbose_name_plural = 'Onboarding Feedbacks'
        unique_together = ('employee', 'feedback_type')

    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_feedback_type_display()}"


# ============================================================================
# PMS ENHANCEMENT: GOAL LIBRARY, RATING SCALES, FORM DESIGNER, BELL CURVE, PROMOTION MATRIX
# ============================================================================

class GoalLibrary(Main):
    """
    Pre-built goal templates organized by department, designation, and job function.
    Enables quick goal assignment during appraisal cycles.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, help_text="Goal title")
    description = models.TextField(help_text="Detailed goal description")
    
    # Organization targeting
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Department this goal template applies to")
    designation = models.ForeignKey('Designation', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Designation/role this goal template applies to")
    
    # Goal categorization
    category = models.CharField(max_length=50, choices=[
        ('FINANCIAL', 'Financial'),
        ('CUSTOMER', 'Customer'),
        ('INTERNAL', 'Internal Process'),
        ('LEARNING', 'Learning & Growth'),
        ('PROJECT', 'Project Delivery'),
        ('COMPLIANCE', 'Compliance & Risk'),
        ('INNOVATION', 'Innovation'),
        ('LEADERSHIP', 'Leadership'),
        ('OTHER', 'Other'),
    ], default='OTHER')
    
    goal_type = models.CharField(max_length=20, choices=[
        ('SMART', 'SMART Goal'),
        ('OKR', 'Objective & Key Result'),
        ('KPI', 'KPI Target'),
        ('PROJECT', 'Project Milestone'),
    ], default='SMART')
    
    # Measurement
    success_metric = models.TextField(blank=True, null=True,
        help_text="How will success be measured?")
    target_value = models.CharField(max_length=100, blank=True, null=True,
        help_text="Expected target value/outcome")
    
    # Suggested weightage (default recommendation)
    suggested_weightage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00,
        help_text="Suggested weightage percentage")
    
    # Status
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Goal Library Template'
        verbose_name_plural = 'Goal Library Templates'
        ordering = ['category', 'title']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['department', 'designation']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"


class RatingScale(Main):
    """
    Configurable rating scales for performance appraisals.
    Supports 5-point, 9-point, and custom scales with labels.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g. 5-Point Scale, 9-Point Scale")
    description = models.TextField(blank=True, null=True)
    
    scale_type = models.CharField(max_length=20, choices=[
        ('STANDARD_5', '5-Point Standard'),
        ('STANDARD_9', '9-Point Standard'),
        ('CUSTOM', 'Custom Scale'),
        ('YES_NO', 'Yes/No'),
        ('SATISFACTION', 'Satisfaction (1-5)'),
    ], default='STANDARD_5')
    
    # For custom scales
    min_rating = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    max_rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    step = models.DecimalField(max_digits=3, decimal_places=1, default=0.5,
        help_text="Increment step (e.g. 0.5, 1.0)")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Rating Scale'
        verbose_name_plural = 'Rating Scales'
    
    def __str__(self):
        return f"{self.name} ({self.get_scale_type_display()})"


class RatingScaleOption(Main):
    """
    Individual options within a rating scale with labels and descriptions.
    E.g. 5 = 'Outstanding', 4 = 'Exceeds Expectations', etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scale = models.ForeignKey(RatingScale, on_delete=models.CASCADE, related_name='options')
    
    rating_value = models.DecimalField(max_digits=3, decimal_places=1,
        help_text="The numeric rating value")
    label = models.CharField(max_length=100,
        help_text="Short label like 'Outstanding', 'Meets Expectations'")
    description = models.TextField(blank=True, null=True,
        help_text="Detailed description of what this rating means")
    
    # Color coding for reports
    color_code = models.CharField(max_length=7, blank=True, null=True,
        help_text="Hex color code for visual representation (e.g. #22C55E)")
    
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Rating Scale Option'
        verbose_name_plural = 'Rating Scale Options'
        ordering = ['scale', '-rating_value']
        unique_together = ('scale', 'rating_value')
    
    def __str__(self):
        return f"{self.scale.name}: {self.rating_value} - {self.label}"


class AppraisalFormTemplate(Main):
    """
    Appraisal form designer template.
    Each form has multiple sections, each section has multiple questions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Form template name")
    description = models.TextField(blank=True, null=True)
    
    form_type = models.CharField(max_length=30, choices=[
        ('SELF_APPRAISAL', 'Self Appraisal'),
        ('MANAGER_APPRAISAL', 'Manager Appraisal'),
        ('PEER_REVIEW', 'Peer Review'),
        ('360_FEEDBACK', '360° Feedback'),
        ('EXIT_INTERVIEW', 'Exit Interview'),
        ('PROBATION', 'Probation Review'),
    ], default='SELF_APPRAISAL')
    
    # Applicable to
    applicable_departments = models.ManyToManyField(Department, blank=True,
        help_text="Leave empty to apply to all departments")
    applicable_designations = models.ManyToManyField('Designation', blank=True,
        help_text="Leave empty to apply to all designations")
    
    # Rating scale to use
    rating_scale = models.ForeignKey(RatingScale, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Default rating scale for this form")
    
    is_published = models.BooleanField(default=False,
        help_text="Published templates can be used in appraisal cycles")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Appraisal Form Template'
        verbose_name_plural = 'Appraisal Form Templates'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_form_type_display()})"


class AppraisalFormSection(Main):
    """Section within an appraisal form template."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_template = models.ForeignKey(AppraisalFormTemplate, on_delete=models.CASCADE,
        related_name='sections')
    
    title = models.CharField(max_length=200, help_text="Section title")
    description = models.TextField(blank=True, null=True,
        help_text="Instructions or context for this section")
    
    order = models.IntegerField(default=0)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
        help_text="Weightage of this section in the overall form (sum of all sections = 100%)")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Appraisal Form Section'
        verbose_name_plural = 'Appraisal Form Sections'
        ordering = ['form_template', 'order']
    
    def __str__(self):
        return f"{self.form_template.name} → {self.title}"


class AppraisalFormQuestion(Main):
    """Question within an appraisal form section."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(AppraisalFormSection, on_delete=models.CASCADE,
        related_name='questions')
    
    question_text = models.TextField()
    question_type = models.CharField(max_length=30, choices=[
        ('RATING', 'Rating (Scale)'),
        ('TEXT', 'Text/Open Ended'),
        ('MULTI_CHOICE', 'Multiple Choice'),
        ('YES_NO', 'Yes/No'),
        ('DROPDOWN', 'Dropdown'),
        ('DATE', 'Date'),
        ('FILE_UPLOAD', 'File Upload'),
    ], default='RATING')
    
    # For RATING type - which scale to use
    rating_scale = models.ForeignKey(RatingScale, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Leave empty to use form template default scale")
    
    # For MULTI_CHOICE / DROPDOWN type
    options = models.JSONField(default=list, blank=True,
        help_text="List of options for multi-choice/dropdown questions")
    
    # Validation
    is_required = models.BooleanField(default=True)
    min_value = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    max_value = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    max_length = models.IntegerField(null=True, blank=True,
        help_text="Max characters for text response")
    
    placeholder = models.CharField(max_length=200, blank=True, null=True)
    help_text = models.TextField(blank=True, null=True)
    
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Appraisal Form Question'
        verbose_name_plural = 'Appraisal Form Questions'
        ordering = ['section', 'order']
    
    def __str__(self):
        return f"{self.section.title} Q{self.order}: {self.question_text[:50]}"


class AppraisalFormResponse(Main):
    """
    Response to an appraisal form question for a specific employee review.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey('PerformanceReview', on_delete=models.CASCADE,
        related_name='form_responses')
    question = models.ForeignKey(AppraisalFormQuestion, on_delete=models.CASCADE)
    
    # Who submitted this response
    respondent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Who answered this question (employee, manager, peer)")
    respondent_type = models.CharField(max_length=20, choices=[
        ('SELF', 'Self'),
        ('MANAGER', 'Manager'),
        ('PEER', 'Peer'),
        ('SUBORDINATE', 'Subordinate'),
        ('HR', 'HR'),
    ], default='SELF')
    
    # Response values (one will be filled based on question_type)
    rating_value = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    text_response = models.TextField(blank=True, null=True)
    choice_response = models.CharField(max_length=200, blank=True, null=True)
    file_response = models.FileField(upload_to='appraisal_responses/%Y/%m/', blank=True, null=True)
    date_response = models.DateField(blank=True, null=True)
    
    submitted_date = models.DateTimeField(auto_now_add=True)
    is_draft = models.BooleanField(default=True,
        help_text="If True, response is saved as draft")
    
    class Meta:
        verbose_name = 'Appraisal Form Response'
        verbose_name_plural = 'Appraisal Form Responses'
        unique_together = ('review', 'question', 'respondent_type')
    
    def __str__(self):
        return f"Review {self.review.id} - Q: {self.question.question_text[:30]}"


class BellCurveConfig(Main):
    """
    Bell curve / forced ranking distribution configuration.
    Defines the expected percentage distribution across rating levels.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g. Standard Bell Curve, Aggressive, Soft")
    description = models.TextField(blank=True, null=True)
    
    cycle = models.ForeignKey('AppraisalCycle', on_delete=models.CASCADE,
        related_name='bell_curve_configs', null=True, blank=True)
    
    # Distribution percentages (must sum to 100)
    distribution = models.JSONField(default=dict,
        help_text='{"5": 10, "4": 20, "3": 40, "2": 20, "1": 10} in percentages')
    
    # Settings
    is_forced_ranking = models.BooleanField(default=False,
        help_text="If True, ratings are auto-adjusted to fit the curve")
    allow_override = models.BooleanField(default=True,
        help_text="Allow managers to override forced rank with justification")
    min_employees_for_curve = models.IntegerField(default=20,
        help_text="Minimum employees needed to apply bell curve")
    
    # Curve type
    curve_type = models.CharField(max_length=30, choices=[
        ('STANDARD_BELL', 'Standard Bell Curve'),
        ('SKEWED_RIGHT', 'Skewed Right (More High Performers)'),
        ('SKEWED_LEFT', 'Skewed Left (More Low Performers)'),
        ('FLAT', 'Flat Distribution'),
        ('CUSTOM', 'Custom Distribution'),
    ], default='STANDARD_BELL')
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Bell Curve Configuration'
        verbose_name_plural = 'Bell Curve Configurations'
    
    def __str__(self):
        return f"{self.name} ({self.get_curve_type_display()})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.distribution:
            total = sum(float(v) for v in self.distribution.values())
            if abs(total - 100.0) > 0.01:
                raise ValidationError({'distribution': f'Distribution percentages must sum to 100, got {total}'})


class PromotionMatrix(Main):
    """
    PMS Rating → Increment/Promotion mapping matrix.
    Defines what increment % and promotion recommendation corresponds to each rating.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g. FY 2025-26 Promotion Matrix")
    cycle = models.ForeignKey('AppraisalCycle', on_delete=models.CASCADE,
        related_name='promotion_matrices', null=True, blank=True)
    
    # Rating range this matrix applies to
    rating_scale = models.ForeignKey(RatingScale, on_delete=models.SET_NULL, null=True, blank=True)
    min_rating = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    max_rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    
    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Promotion Matrix'
        verbose_name_plural = 'Promotion Matrices'
        ordering = ['-effective_from']
    
    def __str__(self):
        return self.name


class PromotionMatrixRow(Main):
    """
    Individual row in the promotion matrix - maps a rating to increment % and recommendation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    matrix = models.ForeignKey(PromotionMatrix, on_delete=models.CASCADE, related_name='rows')
    
    rating_from = models.DecimalField(max_digits=3, decimal_places=1,
        help_text="Minimum rating for this bracket")
    rating_to = models.DecimalField(max_digits=3, decimal_places=1,
        help_text="Maximum rating for this bracket")
    
    min_increment_pct = models.DecimalField(max_digits=5, decimal_places=2,
        help_text="Minimum increment %")
    max_increment_pct = models.DecimalField(max_digits=5, decimal_places=2,
        help_text="Maximum increment %")
    
    promotion_recommended = models.BooleanField(default=False,
        help_text="Is promotion recommended for this rating bracket?")
    promotion_notes = models.TextField(blank=True, null=True,
        help_text="E.g. 'Fast track promotion eligible'")
    
    bonus_recommended = models.DecimalField(max_digits=5, decimal_places=2, default=0,
        help_text="Recommended performance bonus % of CTC")
    
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Promotion Matrix Row'
        verbose_name_plural = 'Promotion Matrix Rows'
        ordering = ['matrix', 'rating_from']
    
    def __str__(self):
        return f"{self.matrix.name}: Rating {self.rating_from}-{self.rating_to} → {self.min_increment_pct}-{self.max_increment_pct}%"


class GoalCascade(Main):
    """
    Goal cascade: Company → Department → Team → Individual.
    Tracks how organizational goals flow down to individual contributors.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Source goal (the higher-level goal being cascaded)
    source_type = models.CharField(max_length=30, choices=[
        ('COMPANY', 'Company Goal'),
        ('DEPARTMENT', 'Department Goal'),
        ('TEAM', 'Team Goal'),
    ])
    source_description = models.TextField(help_text="The higher-level goal description")
    
    # Target
    target_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Department this goal cascades to")
    target_team = models.CharField(max_length=200, blank=True, null=True,
        help_text="Team name (if cascading to a team)")
    target_employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
        related_name='cascaded_goals', null=True, blank=True,
        help_text="Employee this cascades to")
    
    # Cascade details
    aligned_goal = models.ForeignKey(PerformanceGoal, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cascaded_from',
        help_text="The PerformanceGoal this cascade is linked to")
    cycle = models.ForeignKey('AppraisalCycle', on_delete=models.CASCADE,
        related_name='goal_cascades')
    
    contribution = models.TextField(blank=True, null=True,
        help_text="How does the target contribute to this source goal?")
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00,
        help_text="% of the source goal this cascade represents")
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Goal Cascade'
        verbose_name_plural = 'Goal Cascades'
    
    def __str__(self):
        return f"{self.get_source_type_display()} → {self.target_department or self.target_team or self.target_employee}"


# ============================================================================
# ENHANCE APPRAISAL CYCLE - ADD WORKFLOW STAGES
# ============================================================================

class AppraisalCycleStage(Main):
    """
    Workflow stages within an appraisal cycle.
    Each cycle can have customizable stages with dates and status.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey('AppraisalCycle', on_delete=models.CASCADE,
        related_name='stages')
    
    stage_type = models.CharField(max_length=50, choices=[
        ('GOAL_SETTING', 'Goal Setting'),
        ('MID_YEAR_REVIEW', 'Mid-Year Review'),
        ('SELF_APPRAISAL', 'Self Appraisal'),
        ('MANAGER_APPRAISAL', 'Manager Appraisal'),
        ('PEER_FEEDBACK', 'Peer Feedback'),
        ('CALIBRATION', 'Calibration'),
        ('RATING_FINALISATION', 'Rating Finalisation'),
        ('APPRAISAL_DISCUSSION', 'Appraisal Discussion'),
        ('INCREMENT_PROMOTION', 'Increment & Promotion Decision'),
        ('CLOSED', 'Closed'),
    ])
    
    name = models.CharField(max_length=200, help_text="Display name for this stage")
    description = models.TextField(blank=True, null=True)
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Status
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('SKIPPED', 'Skipped'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Optional form template for this stage
    form_template = models.ForeignKey(AppraisalFormTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cycle_stages')
    
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Appraisal Cycle Stage'
        verbose_name_plural = 'Appraisal Cycle Stages'
        ordering = ['cycle', 'order']
        unique_together = ('cycle', 'stage_type')
    
    def __str__(self):
        return f"{self.cycle.name} → {self.get_stage_type_display()}"




# ============================================================================
# DATA SECURITY: IP ACCESS RESTRICTION
# ============================================================================

class IPAccessRestriction(Main):
    """
    IP-based access control for restricting access to sensitive HR screens.
    Supports whitelist and blacklist modes with CIDR notation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Rule name e.g. Payroll IP Whitelist")
    
    restriction_type = models.CharField(max_length=20, choices=[
        ('WHITELIST', 'Whitelist - Only allow listed IPs'),
        ('BLACKLIST', 'Blacklist - Block listed IPs'),
    ], default='WHITELIST')
    
    # Networks in CIDR notation
    allowed_networks = models.JSONField(default=list, blank=True,
        help_text='List of CIDR ranges e.g. ["10.0.0.0/8", "192.168.1.0/24"]')
    blocked_networks = models.JSONField(default=list, blank=True,
        help_text='List of CIDR ranges to block')
    
    # Applicable to
    role_required = models.CharField(max_length=50, blank=True, null=True,
        help_text="Role this restriction applies to (ANY for all)")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Specific user this restriction applies to")
    
    # Screen/Module access
    applicable_modules = models.JSONField(default=list, blank=True,
        help_text='List of modules: ["payroll", "employee_data", "compliance"]')
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'IP Access Restriction'
        verbose_name_plural = 'IP Access Restrictions'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_restriction_type_display()})"


# ============================================================================
# PHASE 4: ADDITIONAL HR MODULES
# ============================================================================

# -------- POSH (SEXUAL HARASSMENT) COMPLIANCE --------

POSH_COMPLAINT_STATUS = (
    ('DRAFT', 'Draft'),
    ('SUBMITTED', 'Submitted'),
    ('UNDER_INVESTIGATION', 'Under Investigation'),
    ('INQUIRY_COMPLETED', 'Inquiry Completed'),
    ('RESOLVED', 'Resolved'),
    ('DISMISSED', 'Dismissed'),
    ('CLOSED', 'Closed'),
)

POSH_COMPLAINT_TYPE = (
    ('VERBAL', 'Verbal Harassment'),
    ('PHYSICAL', 'Physical Harassment'),
    ('VISUAL', 'Visual / Display'),
    ('CYBER', 'Cyber / Electronic'),
    ('THIRD_PARTY', 'Third Party Harassment'),
    ('OTHER', 'Other'),
)


class POSHComplaint(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complainant = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='posh_complaints_filed')
    is_anonymous = models.BooleanField(default=False)
    respondent = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='posh_complaints_against')
    complaint_type = models.CharField(max_length=30, choices=POSH_COMPLAINT_TYPE, default='OTHER')
    incident_date = models.DateField()
    incident_location = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField()
    supporting_evidence = models.FileField(upload_to='posh_evidence/%Y/%m/', blank=True, null=True)
    icc_members = models.ManyToManyField(User, blank=True, related_name='posh_cases')
    presiding_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='posh_presiding')
    status = models.CharField(max_length=30, choices=POSH_COMPLAINT_STATUS, default='DRAFT')
    submitted_date = models.DateTimeField(blank=True, null=True)
    inquiry_start_date = models.DateField(blank=True, null=True)
    inquiry_completed_date = models.DateField(blank=True, null=True)
    resolution_date = models.DateField(blank=True, null=True)
    inquiry_findings = models.TextField(blank=True, null=True)
    action_taken = models.TextField(blank=True, null=True)
    closure_notes = models.TextField(blank=True, null=True)
    is_confidential = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'POSH Complaint'
        verbose_name_plural = 'POSH Complaints'
        ordering = ['-created_at']
        permissions = [('can_view_posh_case', 'Can view POSH case details'), ('can_manage_icc', 'Can manage ICC committee')]

    def __str__(self):
        return f"POSH-{str(self.id)[:8].upper()} - {self.get_complaint_type_display()}"


class POSHInquiryNote(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complaint = models.ForeignKey(POSHComplaint, on_delete=models.CASCADE, related_name='inquiry_notes')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()
    is_confidential = models.BooleanField(default=True)
    attachment = models.FileField(upload_to='posh_inquiry_notes/%Y/%m/', blank=True, null=True)

    class Meta:
        verbose_name = 'POSH Inquiry Note'
        verbose_name_plural = 'POSH Inquiry Notes'
        ordering = ['created_at']

    def __str__(self):
        return f"Note on {self.complaint} by {self.author.get_full_name()}"


# -------- DATA PRIVACY CONSENT (DPDP ACT 2023 / GDPR) --------

CONSENT_TYPE = (
    ('DATA_COLLECTION', 'Data Collection Consent'),
    ('DATA_PROCESSING', 'Data Processing Consent'),
    ('DATA_RETENTION', 'Data Retention Consent'),
    ('DATA_SHARING', 'Data Sharing Consent'),
    ('BACKGROUND_VERIFICATION', 'Background Verification Consent'),
    ('BANK_DETAILS', 'Bank Details Processing'),
    ('EMERGENCY_CONTACT', 'Emergency Contact Processing'),
    ('HEALTH_DATA', 'Health Data Processing'),
    ('GENERAL', 'General Consent'),
)

CONSENT_STATUS = (
    ('PENDING', 'Pending'),
    ('GRANTED', 'Granted'),
    ('WITHDRAWN', 'Withdrawn'),
    ('EXPIRED', 'Expired'),
)


class DataConsentRecord(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='data_consents')
    consent_type = models.CharField(max_length=50, choices=CONSENT_TYPE)
    status = models.CharField(max_length=20, choices=CONSENT_STATUS, default='PENDING')
    consent_version = models.CharField(max_length=20)
    consent_text = models.TextField(help_text="Full text of what was consented to")
    consent_date = models.DateTimeField(auto_now_add=True)
    granted_date = models.DateTimeField(blank=True, null=True)
    withdrawn_date = models.DateTimeField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    consent_method = models.CharField(max_length=30, choices=[
        ('PORTAL', 'ESS Portal'), ('EMAIL', 'Email'), ('SIGNED_FORM', 'Signed Form'),
        ('HR_INTERVIEW', 'HR Interview'), ('API', 'API Integration'),
    ], default='PORTAL')
    consent_proof = models.FileField(upload_to='consent_proofs/%Y/%m/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Data Consent Record'
        verbose_name_plural = 'Data Consent Records'
        ordering = ['-consent_date']
        unique_together = ('employee', 'consent_type', 'consent_version')

    def __str__(self):
        return f"{self.employee.employee_id} - {self.get_consent_type_display()} ({self.status})"


# -------- STAY INTERVIEW --------

class StayInterview(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='stay_interviews')
    conducted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conducted_stay_interviews')
    interview_date = models.DateField()
    what_keeps_you = models.TextField(help_text="What keeps you at the company?")
    what_would_change = models.TextField(help_text="What would make you leave?")
    career_aspirations = models.TextField(blank=True, null=True)
    satisfaction_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    engagement_score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)], null=True, blank=True)
    identified_concerns = models.TextField(blank=True, null=True)
    action_items = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[
        ('SCHEDULED', 'Scheduled'), ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'), ('FOLLOW_UP', 'Follow-up Required'),
    ], default='SCHEDULED')
    retention_risk = models.CharField(max_length=20, choices=[
        ('LOW', 'Low Risk'), ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'), ('CRITICAL', 'Critical - Immediate Attention'),
    ], default='LOW')
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Stay Interview'
        verbose_name_plural = 'Stay Interviews'
        ordering = ['-interview_date']

    def __str__(self):
        return f"{self.employee.employee_id} - Stay Interview ({self.interview_date})"


# -------- SALARY FREEZE --------

class SalaryFreeze(Main):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_freezes')
    freeze_reason = models.CharField(max_length=50, choices=[
        ('NOTICE_PERIOD', 'Under Notice Period'), ('DISCIPLINARY', 'Disciplinary Proceedings'),
        ('DISPUTE', 'Salary Dispute'), ('LEGAL', 'Legal Proceedings'),
        ('ABSENCE', 'Extended Unauthorized Absence'), ('OTHER', 'Other'),
    ])
    description = models.TextField(help_text="Reason for salary freeze")
    frozen_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='salary_freezes_initiated')
    frozen_date = models.DateTimeField(auto_now_add=True)
    unfrozen_date = models.DateTimeField(blank=True, null=True)
    unfrozen_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='salary_freezes_released')
    unfrozen_reason = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Salary Freeze'
        verbose_name_plural = 'Salary Freezes'
        ordering = ['-frozen_date']

    def __str__(self):
        status = "Active" if self.is_active else "Released"
        return f"{self.employee.employee_id} - Salary Freeze ({status})"
