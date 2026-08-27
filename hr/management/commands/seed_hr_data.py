"""
Management command to seed the HR module with comprehensive sample data.

Usage:
    python manage.py seed_hr_data              # Seed default sample data
    python manage.py seed_hr_data --employees 50  # Seed 50 employees
    python manage.py seed_hr_data --clear      # Clear existing data first
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import date, timedelta, datetime
from decimal import Decimal
import random
import uuid

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed HR module with comprehensive sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--employees',
            type=int,
            default=15,
            help='Number of employees to create (default: 15)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing HR data before seeding'
        )
        parser.add_argument(
            '--months',
            type=int,
            default=3,
            help='Number of past months of attendance/payroll data (default: 3)'
        )

    def handle(self, *args, **options):
        employee_count = options['employees']
        should_clear = options['clear']
        months_back = options['months']

        if should_clear:
            self._clear_data()

        self.stdout.write(self.style.NOTICE('🚀 Starting HR data seeding...'))
        
        self._seed_master_data()
        self._seed_users_and_employees(employee_count)
        self._seed_leave_types_and_balances()
        self._seed_payroll_components()
        self._seed_salary_structures()
        self._seed_employee_salaries()
        self._seed_attendance(months_back)
        self._seed_leave_applications()
        self._seed_payroll(months_back)
        self._seed_statutory_configs()
        self._seed_recruitment()
        self._seed_exit_data()
        self._seed_training()
        self._seed_hr_tickets()
        self._seed_compliance_calendar()

        total_employees = Employee.objects.count() if 'Employee' in globals() or 'Employee' in locals() else 0
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ HR data seeding complete!\n'
            f'   • Employees created: {total_employees}\n'
            f'   • Attendance records: {Attendance.objects.count() if "Attendance" in dir() else 0}\n'
            f'   • Leave applications: {LeaveApplication.objects.count() if "LeaveApplication" in dir() else 0}\n'
            f'   • Payroll records: {Payroll.objects.count() if "Payroll" in dir() else 0}\n'
        ))

    def _clear_data(self):
        """Clear all HR-related data."""
        self.stdout.write('🧹 Clearing existing HR data...')
        
        # Order matters due to foreign keys
        from hr.models import (
            PayrollComponentDetail, Payroll, EmployeeSalary,
            SalaryStructureDetail, SalaryStructure, Attendance,
            LeaveApplication, EmployeeLeaveBalance, EmployeeDocument,
            CompensatoryOff, Holiday,
            SalaryRevision, EmployeeLoan, LoanRepayment, EmployeeReimbursement,
            PFContribution, ESIContribution, PTContribution, TDSCalculation,
            InvestmentDeclaration, GratuityCalculation, BonusCalculation,
            ComplianceCalendarEntry, LWFContribution, OvertimeRequest,
            ShiftSwapRequest, AttendanceRegularizationRequest,
            EmployeeFamily, EmployeeEmergencyContact, EmployeeBankAccount,
            EmployeeDocumentVersion, JobRequisition, JobApplication, Candidate,
            InterviewSchedule, OfferLetter, BGVCheck, OnboardingTask,
            Resignation, ExitClearance, ExitInterview, ExitInterviewResponse,
            FnFSettlement, FnFSettlementComponent, AlumniRecord,
            HRTicket, HRTicketConversation, AssetRequest,
            PerformanceGoal, PerformanceReview, OKR, Feedback360,
            PIPlan, TrainingNomination, TrainingNeed, TrainingAssessment,
            TrainingCost, EmployeeSkill, Employee
        )
        
        # Clear in dependency order
        models_to_clear = [
            PayrollComponentDetail, Payroll, EmployeeSalary,
            SalaryStructureDetail, Attendance, LeaveApplication,
            EmployeeLeaveBalance, EmployeeDocument, CompensatoryOff,
            SalaryRevision, EmployeeLoan, LoanRepayment, EmployeeReimbursement,
            PFContribution, ESIContribution, PTContribution, TDSCalculation,
            InvestmentDeclaration, GratuityCalculation, BonusCalculation,
            ComplianceCalendarEntry, LWFContribution, OvertimeRequest,
            ShiftSwapRequest, AttendanceRegularizationRequest,
            EmployeeFamily, EmployeeEmergencyContact, EmployeeBankAccount,
            EmployeeDocumentVersion,
            OnboardingTask, BGVCheck, OfferLetter, InterviewSchedule,
            JobApplication, Candidate, JobRequisition,
            Resignation, ExitClearance, ExitInterviewResponse, ExitInterview,
            FnFSettlementComponent, FnFSettlement, AlumniRecord,
            HRTicketConversation, HRTicket, AssetRequest,
            PerformanceGoal, PerformanceReview, OKR, Feedback360,
            PIPlan, TrainingNomination, TrainingNeed, TrainingAssessment,
            TrainingCost, EmployeeSkill, Employee,
        ]
        
        for model in models_to_clear:
            model.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('   ✅ Data cleared'))

    def _seed_master_data(self):
        """Seed master data: designations, locations, shifts, skills."""
        from hr.models import Designation, WorkLocation, CostCenter, Shift, Skill

        self.stdout.write('📋 Seeding master data...')

        # Designations
        designations = [
            {'code': 'CEO', 'name': 'Chief Executive Officer', 'grade': 'E5', 'band': 'IC5'},
            {'code': 'CTO', 'name': 'Chief Technology Officer', 'grade': 'E5', 'band': 'IC5'},
            {'code': 'HR_HEAD', 'name': 'HR Head', 'grade': 'E4', 'band': 'IC4'},
            {'code': 'SR_ENG', 'name': 'Senior Engineer', 'grade': 'E3', 'band': 'IC3'},
            {'code': 'JR_ENG', 'name': 'Junior Engineer', 'grade': 'E2', 'band': 'IC2'},
            {'code': 'PM', 'name': 'Project Manager', 'grade': 'E4', 'band': 'M1'},
            {'code': 'HR_MGR', 'name': 'HR Manager', 'grade': 'E4', 'band': 'M1'},
            {'code': 'HR_EXEC', 'name': 'HR Executive', 'grade': 'E2', 'band': 'IC2'},
            {'code': 'ACCT_MGR', 'name': 'Accounts Manager', 'grade': 'E4', 'band': 'M1'},
            {'code': 'ACCT_EXEC', 'name': 'Accounts Executive', 'grade': 'E2', 'band': 'IC2'},
            {'code': 'DESIGNER', 'name': 'UI/UX Designer', 'grade': 'E3', 'band': 'IC3'},
            {'code': 'TRAINEE', 'name': 'Graduate Trainee', 'grade': 'E1', 'band': 'IC1'},
        ]
        for d in designations:
            Designation.objects.get_or_create(code=d['code'], defaults=d)

        # Work Locations
        locations = [
            {'code': 'BLR', 'name': 'Bangalore HQ', 'city': 'Bangalore', 'state': 'Karnataka', 'country': 'India', 'pin_code': '560001', 'address': '123 Tech Park, Whitefield'},
            {'code': 'MUM', 'name': 'Mumbai Office', 'city': 'Mumbai', 'state': 'Maharashtra', 'country': 'India', 'pin_code': '400001', 'address': '456 Business Bay, Andheri'},
            {'code': 'DEL', 'name': 'Delhi Office', 'city': 'Delhi', 'state': 'Delhi', 'country': 'India', 'pin_code': '110001', 'address': '789 Corporate Hub, Connaught Place'},
            {'code': 'HYD', 'name': 'Hyderabad Office', 'city': 'Hyderabad', 'state': 'Telangana', 'country': 'India', 'pin_code': '500001', 'address': '321 IT Corridor, Hitech City'},
        ]
        for loc in locations:
            WorkLocation.objects.get_or_create(code=loc['code'], defaults=loc)

        # Shifts
        shifts = [
            {'code': 'GEN', 'name': 'General Shift', 'shift_type': 'GENERAL', 'start_time': '09:00:00', 'end_time': '18:00:00', 'break_duration_minutes': 60},
            {'code': 'NIGHT', 'name': 'Night Shift', 'shift_type': 'NIGHT', 'start_time': '21:00:00', 'end_time': '06:00:00', 'break_duration_minutes': 45},
            {'code': 'FLEX', 'name': 'Flexible Shift', 'shift_type': 'FLEXIBLE', 'start_time': '08:00:00', 'end_time': '17:00:00', 'break_duration_minutes': 60},
        ]
        for s in shifts:
            Shift.objects.get_or_create(code=s['code'], defaults=s)

        # Skills
        skills = [
            {'name': 'Python', 'category': 'TECHNICAL'},
            {'name': 'JavaScript', 'category': 'TECHNICAL'},
            {'name': 'Django', 'category': 'TECHNICAL'},
            {'name': 'React', 'category': 'TECHNICAL'},
            {'name': 'PostgreSQL', 'category': 'TECHNICAL'},
            {'name': 'Project Management', 'category': 'MANAGEMENT'},
            {'name': 'Leadership', 'category': 'MANAGEMENT'},
            {'name': 'Communication', 'category': 'SOFT_SKILL'},
            {'name': 'Teamwork', 'category': 'SOFT_SKILL'},
            {'name': 'UI/UX Design', 'category': 'TECHNICAL'},
            {'name': 'AWS', 'category': 'TECHNICAL'},
            {'name': 'Docker', 'category': 'TECHNICAL'},
            {'name': 'HR Management', 'category': 'DOMAIN'},
            {'name': 'Payroll Processing', 'category': 'DOMAIN'},
            {'name': 'Statutory Compliance', 'category': 'DOMAIN'},
        ]
        for skill in skills:
            Skill.objects.get_or_create(name=skill['name'], defaults=skill)

        # Cost Centers
        cost_centers = [
            {'code': 'CC-ENG', 'name': 'Engineering', 'is_active': True},
            {'code': 'CC-HR', 'name': 'Human Resources', 'is_active': True},
            {'code': 'CC-FIN', 'name': 'Finance & Accounts', 'is_active': True},
            {'code': 'CC-DES', 'name': 'Design', 'is_active': True},
            {'code': 'CC-MGT', 'name': 'Management', 'is_active': True},
        ]
        for cc in cost_centers:
            CostCenter.objects.get_or_create(code=cc['code'], defaults=cc)

        self.stdout.write(self.style.SUCCESS('   ✅ Master data seeded'))

    def _seed_users_and_employees(self, count):
        """Seed users and employees."""
        from hr.models import Employee, Designation, WorkLocation, Shift
        from authentication.models import Department

        self.stdout.write(f'👤 Creating {count} employees...')

        # Create departments first
        departments_data = ['Engineering', 'Human Resources', 'Finance', 'Design', 'Management']
        departments = {}
        for dept_name in departments_data:
            dept, _ = Department.objects.get_or_create(name=dept_name)
            departments[dept_name] = dept

        employees_data = [
            # (first_name, last_name, email_prefix, gender, dept, desig_code, location, employment_type, manager_idx, salary_gross)
            ('Arun', 'Kumar', 'arun.kumar', 'MALE', 'Management', 'CEO', 'BLR', 'PERMANENT', None, 3000000),
            ('Priya', 'Sharma', 'priya.sharma', 'FEMALE', 'Management', 'CTO', 'BLR', 'PERMANENT', 0, 2500000),
            ('Rajesh', 'Patel', 'rajesh.patel', 'MALE', 'Human Resources', 'HR_HEAD', 'BLR', 'PERMANENT', 0, 1800000),
            ('Sneha', 'Reddy', 'sneha.reddy', 'FEMALE', 'Engineering', 'SR_ENG', 'BLR', 'PERMANENT', 1, 1200000),
            ('Vikram', 'Singh', 'vikram.singh', 'MALE', 'Engineering', 'SR_ENG', 'BLR', 'PERMANENT', 1, 1100000),
            ('Anita', 'Verma', 'anita.verma', 'FEMALE', 'Engineering', 'JR_ENG', 'HYD', 'PERMANENT', 3, 600000),
            ('Ravi', 'Joshi', 'ravi.joshi', 'MALE', 'Engineering', 'JR_ENG', 'BLR', 'PERMANENT', 4, 650000),
            ('Deepa', 'Nair', 'deepa.nair', 'FEMALE', 'Engineering', 'TRAINEE', 'HYD', 'TRAINEE', 3, 400000),
            ('Karthik', 'Iyengar', 'karthik.iyengar', 'MALE', 'Design', 'DESIGNER', 'MUM', 'PERMANENT', 1, 900000),
            ('Meera', 'Chopra', 'meera.chopra', 'FEMALE', 'Human Resources', 'HR_MGR', 'BLR', 'PERMANENT', 2, 1000000),
            ('Suresh', 'Babu', 'suresh.babu', 'MALE', 'Finance', 'ACCT_MGR', 'BLR', 'PERMANENT', 0, 950000),
            ('Lakshmi', 'Devi', 'lakshmi.devi', 'FEMALE', 'Finance', 'ACCT_EXEC', 'MUM', 'PERMANENT', 10, 550000),
            ('Ajay', 'Mehta', 'ajay.mehta', 'MALE', 'Engineering', 'PM', 'DEL', 'PERMANENT', 0, 1500000),
            ('Neha', 'Pillai', 'neha.pillai', 'FEMALE', 'Human Resources', 'HR_EXEC', 'DEL', 'PERMANENT', 2, 500000),
            ('Manish', 'Agarwal', 'manish.agarwal', 'MALE', 'Design', 'DESIGNER', 'MUM', 'PERMANENT', 8, 850000),
        ]

        # Add more random employees if count > len(employees_data)
        first_names_male = ['Amit', 'Raj', 'Sanjay', 'Vivek', 'Prakash']
        first_names_female = ['Kavita', 'Sunita', 'Rekha', 'Anjali', 'Pooja']
        last_names = ['Gupta', 'Shah', 'Das', 'Sen', 'Bose', 'Mukherjee', 'Desai', 'Pandey', 'Yadav', 'Saxena']

        while len(employees_data) < count:
            gender = random.choice(['MALE', 'FEMALE'])
            first = random.choice(first_names_male if gender == 'MALE' else first_names_female)
            last = random.choice(last_names)
            dept = random.choice(departments_data)
            emp_data = {
                'first_name': first,
                'last_name': last,
                'email_prefix': f"{first.lower()}.{last.lower()}{random.randint(1,99)}",
                'gender': gender,
                'dept': dept,
                'desig_code': random.choice(['JR_ENG', 'HR_EXEC', 'DESIGNER', 'TRAINEE']),
                'location': random.choice(['BLR', 'MUM', 'HYD']),
                'employment_type': random.choice(['PERMANENT', 'CONTRACT', 'TRAINEE']),
                'manager_idx': random.randint(0, min(len(employees_data) - 1, 4)),
                'salary_gross': random.choice([350000, 450000, 550000, 650000, 750000]),
            }
            employees_data.append((
                emp_data['first_name'],
                emp_data['last_name'],
                emp_data['email_prefix'],
                emp_data['gender'],
                emp_data['dept'],
                emp_data['desig_code'],
                emp_data['location'],
                emp_data['employment_type'],
                emp_data['manager_idx'],
                emp_data['salary_gross'],
            ))

        # Cache lookups
        designations = {d.code: d for d in Designation.objects.all()}
        locations = {l.code: l for l in WorkLocation.objects.all()}
        shifts = {s.code: s for s in Shift.objects.all()}

        created_employees = []

        for i, (first, last, email_prefix, gender, dept_name, desig_code, loc_code, emp_type, mgr_idx, gross) in enumerate(employees_data):
            email = f"{email_prefix}@bytehive.com"
            
            # Create or get user
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': 'Employee' if emp_type != 'TRAINEE' else 'Employee',
                    'is_active': True,
                }
            )
            if not user.password:
                user.set_password('password123')
                user.save()

            # Create employee
            designation = designations.get(desig_code)
            location = locations.get(loc_code)
            dept = departments.get(dept_name)

            # Probation = 6 months
            doj = date.today() - timedelta(days=random.randint(90, 730))
            prob_end = doj + timedelta(days=180)
            status = 'ACTIVE' if doj + timedelta(days=180) < date.today() else 'ONBOARDING'

            # Set manager (skip for CEO index 0)
            manager = None
            if mgr_idx is not None and mgr_idx < len(created_employees):
                manager = created_employees[mgr_idx]

            employee, created = Employee.objects.get_or_create(
                user=user,
                defaults={
                    'employee_id': f"EMP-{date.today().year}-{i+1:04d}",
                    'first_name': first,
                    'last_name': last,
                    'date_of_birth': date(random.randint(1980, 2000), random.randint(1, 12), random.randint(1, 28)),
                    'gender': gender,
                    'marital_status': random.choice(['SINGLE', 'MARRIED', 'MARRIED', 'SINGLE']),
                    'nationality': 'Indian',
                    'personal_email': email,
                    'personal_mobile': f"9{random.randint(7000000000, 9999999999)}",
                    'current_address': f"{random.randint(1, 999)}, {random.choice(['MG Road', 'Brigade Road', 'Church Street', 'Indiranagar', 'Koramangala'])}",
                    'current_city': location.city if location else 'Bangalore',
                    'current_state': location.state if location else 'Karnataka',
                    'current_country': 'India',
                    'current_pin_code': location.pin_code if location else '560001',
                    'permanent_address': f"{random.randint(1, 999)}, {random.choice(['Main Road', 'Tank Street', 'Temple Road', 'Market Road'])}",
                    'permanent_city': random.choice(['Bangalore', 'Mumbai', 'Delhi', 'Chennai', 'Hyderabad']),
                    'permanent_state': random.choice(['Karnataka', 'Maharashtra', 'Delhi', 'Tamil Nadu', 'Telangana']),
                    'permanent_country': 'India',
                    'permanent_pin_code': str(random.randint(500000, 999999)),
                    'employment_type': emp_type,
                    'date_of_joining': doj,
                    'probation_end_date': prob_end,
                    'confirmation_date': prob_end + timedelta(days=1) if status == 'ACTIVE' else None,
                    'notice_period_days': 30,
                    'status': status,
                    'department': dept,
                    'designation': designation,
                    'work_location': location,
                    'grade': designation.grade if designation else None,
                    'band': designation.band if designation else None,
                    'reporting_manager': manager,
                    'work_shift': 'GENERAL',
                    'is_active': True,
                }
            )

            if created:
                # Generate Aadhaar/PAN if applicable
                employee.aadhaar_number = f"{random.randint(100000000000, 999999999999)}"
                employee.pan_number = f"{random.choice('ABCDEFGHIJ')}{random.choice('ABCDEFGHIJ')}{random.choice('ABCDEFGHIJ')}{random.choice('ABCDEFGHIJ')}{random.choice('ABCDEFGHIJ')}{random.randint(1000, 9999)}{random.choice('ABCDEFGHIJ')}"
                employee.bank_account_number = f"{random.randint(10000000000, 99999999999)}"
                employee.bank_name = random.choice(['HDFC Bank', 'ICICI Bank', 'SBI', 'Axis Bank'])
                employee.ifsc_code = f"{random.choice(['HDFC', 'ICICI', 'SBIN', 'UTIB'])}0{random.randint(10000, 99999)}"
                employee.account_holder_name = f"{first} {last}"
                employee.save()

            created_employees.append(employee)

        self.stdout.write(self.style.SUCCESS(f'   ✅ {len(created_employees)} employees created'))

    def _seed_leave_types_and_balances(self):
        """Seed leave types and create balances for all employees."""
        from hr.models import LeaveType, Employee, EmployeeLeaveBalance

        self.stdout.write('🏖️ Seeding leave types and balances...')

        leave_types_data = [
            {'code': 'CL', 'name': 'Casual Leave', 'leave_type': 'CASUAL', 'default_annual_allocation': 12,
             'accrual_frequency': 'MONTHLY', 'max_carry_forward': 5, 'can_go_negative': False,
             'min_balance_required': 0, 'max_continuous_days': 7, 'is_encashable': True, 'encashment_max_days': 3},
            {'code': 'SL', 'name': 'Sick Leave', 'leave_type': 'SICK', 'default_annual_allocation': 10,
             'accrual_frequency': 'MONTHLY', 'max_carry_forward': 3, 'can_go_negative': True,
             'min_balance_required': 0, 'max_continuous_days': 15, 'is_encashable': False},
            {'code': 'EL', 'name': 'Earned Leave', 'leave_type': 'EARNED', 'default_annual_allocation': 20,
             'accrual_frequency': 'MONTHLY', 'max_carry_forward': 15, 'can_go_negative': False,
             'min_balance_required': 0, 'max_continuous_days': 30, 'is_encashable': True, 'encashment_max_days': 10},
            {'code': 'ML', 'name': 'Maternity Leave', 'leave_type': 'MATERNITY', 'default_annual_allocation': 182,
             'accrual_frequency': 'ANNUAL', 'max_carry_forward': 0, 'can_go_negative': True,
             'min_balance_required': 0, 'max_continuous_days': 182, 'is_encashable': False},
            {'code': 'PAT', 'name': 'Paternity Leave', 'leave_type': 'PATERNITY', 'default_annual_allocation': 5,
             'accrual_frequency': 'ANNUAL', 'max_carry_forward': 0, 'can_go_negative': False,
             'min_balance_required': 0, 'max_continuous_days': 5, 'is_encashable': False},
            {'code': 'COFF', 'name': 'Compensatory Off', 'leave_type': 'COMP_OFF', 'default_annual_allocation': 0,
             'accrual_frequency': 'MONTHLY', 'max_carry_forward': 3, 'can_go_negative': False,
             'min_balance_required': 0, 'max_continuous_days': 3, 'is_encashable': False},
        ]

        created_types = []
        for lt in leave_types_data:
            leave_type, _ = LeaveType.objects.get_or_create(code=lt['code'], defaults=lt)
            created_types.append(leave_type)

        # Create balances for employees
        current_fy = f"{date.today().year - 1}-{date.today().year}" if date.today().month >= 4 else f"{date.today().year - 2}-{date.today().year - 1}"
        
        employees = Employee.objects.all()
        for emp in employees:
            for lt in created_types[:3]:  # CL, SL, EL for everyone
                if lt.default_annual_allocation > 0:
                    used = random.randint(0, max(lt.default_annual_allocation // 3, 1))
                    pending = random.randint(0, min(2, lt.default_annual_allocation - used))
                    balance = EmployeeLeaveBalance.objects.get_or_create(
                        employee=emp,
                        leave_type=lt,
                        financial_year=current_fy,
                        defaults={
                            'opening_balance': lt.default_annual_allocation,
                            'accrued_days': 0,
                            'used_days': used,
                            'pending_days': pending,
                            'current_balance': lt.default_annual_allocation - used - pending,
                        }
                    )

        self.stdout.write(self.style.SUCCESS(f'   ✅ {len(created_types)} leave types seeded'))

    def _seed_payroll_components(self):
        """Seed salary components."""
        from hr.models import SalaryComponent

        self.stdout.write('💰 Seeding payroll components...')

        components = [
            {'code': 'BASIC', 'name': 'Basic Salary', 'component_type': 'EARNINGS', 'is_fixed': True, 'is_taxable': True, 'order': 1},
            {'code': 'HRA', 'name': 'House Rent Allowance', 'component_type': 'EARNINGS', 'is_fixed': True, 'is_taxable': False, 'depends_on_basic': True, 'percentage_of_basic': 40, 'order': 2},
            {'code': 'CONVEYANCE', 'name': 'Conveyance Allowance', 'component_type': 'EARNINGS', 'is_fixed': True, 'is_taxable': False, 'exemption_limit': 1600, 'order': 3},
            {'code': 'MEDICAL', 'name': 'Medical Allowance', 'component_type': 'EARNINGS', 'is_fixed': True, 'is_taxable': False, 'exemption_limit': 15000, 'order': 4},
            {'code': 'SPECIAL', 'name': 'Special Allowance', 'component_type': 'EARNINGS', 'is_fixed': True, 'is_taxable': True, 'order': 5},
            {'code': 'PF_EMPLOYEE', 'name': 'Employee PF', 'component_type': 'DEDUCTIONS', 'is_fixed': False, 'is_statutory': True, 'order': 6},
            {'code': 'ESI_EMPLOYEE', 'name': 'Employee ESI', 'component_type': 'DEDUCTIONS', 'is_fixed': False, 'is_statutory': True, 'order': 7},
            {'code': 'PT', 'name': 'Professional Tax', 'component_type': 'DEDUCTIONS', 'is_fixed': False, 'is_statutory': True, 'order': 8},
            {'code': 'TDS', 'name': 'Tax Deducted at Source', 'component_type': 'DEDUCTIONS', 'is_fixed': False, 'is_statutory': True, 'order': 9},
            {'code': 'PERF_BONUS', 'name': 'Performance Bonus', 'component_type': 'VARIABLE', 'is_fixed': False, 'is_taxable': True, 'order': 10},
            {'code': 'GRATUITY', 'name': 'Gratuity', 'component_type': 'FIXED', 'is_fixed': True, 'is_statutory': True, 'order': 11},
        ]

        for comp in components:
            SalaryComponent.objects.get_or_create(code=comp['code'], defaults=comp)

        self.stdout.write(self.style.SUCCESS(f'   ✅ {len(components)} salary components seeded'))

    def _seed_salary_structures(self):
        """Seed salary structure templates."""
        from hr.models import SalaryStructure, SalaryStructureDetail, SalaryComponent

        self.stdout.write('📊 Seeding salary structures...')

        structures = {
            'MGT-2026': {'name': 'Management Salary Structure 2026', 'grade': 'E5'},
            'SR-2026': {'name': 'Senior Staff Salary 2026', 'grade': 'E3'},
            'JR-2026': {'name': 'Junior Staff Salary 2026', 'grade': 'E2'},
            'TRAINEE-2026': {'name': 'Trainee Stipend 2026', 'grade': 'E1'},
        }

        components = {c.code: c for c in SalaryComponent.objects.all()}

        for code, data in structures.items():
            struct, _ = SalaryStructure.objects.get_or_create(
                code=code, defaults={
                    'name': data['name'],
                    'grade': data['grade'],
                    'effective_from': date(date.today().year, 1, 1),
                    'is_active': True,
                }
            )

            # Add component details
            if 'BASIC' in components:
                SalaryStructureDetail.objects.get_or_create(
                    salary_structure=struct,
                    component=components['BASIC'],
                    defaults={'amount': 50, 'is_percentage': True, 'order': 1}
                )
            if 'HRA' in components:
                SalaryStructureDetail.objects.get_or_create(
                    salary_structure=struct,
                    component=components['HRA'],
                    defaults={'amount': 40, 'is_percentage': True, 'order': 2}
                )

        self.stdout.write(self.style.SUCCESS(f'   ✅ {len(structures)} salary structures seeded'))

    def _seed_employee_salaries(self):
        """Seed employee salaries."""
        from hr.models import Employee, EmployeeSalary, SalaryStructure, SalaryComponent, SalaryStructureDetail

        self.stdout.write('💵 Seeding employee salaries...')

        employees = Employee.objects.all()
        salary_structures = {s.grade: s for s in SalaryStructure.objects.all()}

        for emp in employees:
            if emp.designation and emp.designation.grade in salary_structures:
                structure = salary_structures[emp.designation.grade]
            else:
                structure = SalaryStructure.objects.filter(is_active=True).first()

            # Determine CTC based on designation
            grade_ctc_map = {
                'E5': 3000000, 'E4': 1800000, 'E3': 1200000,
                'E2': 650000, 'E1': 400000, 'M1': 1400000,
                'IC5': 3000000, 'IC4': 1800000, 'IC3': 1200000,
                'IC2': 650000, 'IC1': 400000,
            }
            grade = emp.designation.grade if emp.designation else 'E2'
            ctc = Decimal(str(grade_ctc_map.get(grade, 600000)))

            gross = (ctc * Decimal('0.85')).quantize(Decimal('0.01'))
            basic = gross * Decimal('0.50')
            net = gross - basic * Decimal('0.12') - Decimal('200')

            EmployeeSalary.objects.get_or_create(
                employee=emp,
                effective_from=emp.date_of_joining,
                defaults={
                    'salary_structure': structure,
                    'ctc': ctc,
                    'gross_salary': gross,
                    'net_salary': net,
                    'basic_salary': basic,
                    'is_active': True,
                }
            )

        self.stdout.write(self.style.SUCCESS(f'   ✅ Salaries seeded for {employees.count()} employees'))

    def _seed_attendance(self, months_back):
        """Seed attendance records for past months."""
        from hr.models import Employee, Attendance, Holiday

        self.stdout.write(f'📅 Seeding attendance for {months_back} months...')

        employees = Employee.objects.filter(status='ACTIVE')
        today = date.today()

        # Create some holidays for current year
        holidays_data = [
            {'name': 'Republic Day', 'holiday_date': date(today.year, 1, 26), 'is_national': True},
            {'name': 'Holi', 'holiday_date': date(today.year, 3, 14), 'is_national': False},
            {'name': 'Independence Day', 'holiday_date': date(today.year, 8, 15), 'is_national': True},
            {'name': 'Gandhi Jayanti', 'holiday_date': date(today.year, 10, 2), 'is_national': True},
            {'name': 'Diwali', 'holiday_date': date(today.year, 11, 1), 'is_national': False},
            {'name': 'Christmas', 'holiday_date': date(today.year, 12, 25), 'is_national': True},
        ]
        for h in holidays_data:
            if h['holiday_date'] >= date(today.year, 1, 1):
                Holiday.objects.get_or_create(name=h['name'], holiday_date=h['holiday_date'], defaults=h)

        holiday_dates = set(Holiday.objects.filter(holiday_date__year=today.year).values_list('holiday_date', flat=True))

        count = 0
        for emp in employees:
            for m in range(months_back, 0, -1):
                month = today.month - m
                year = today.year
                if month <= 0:
                    month += 12
                    year -= 1

                for day in range(1, 29):  # Up to 28th to avoid month boundary issues
                    d = date(year, month, day)
                    if d.weekday() == 6:  # Sunday
                        continue
                    if d in holiday_dates:
                        continue
                    if d > today:
                        continue

                    # 80% present, 10% WFH, 5% half-day, 5% absent
                    rand = random.random()
                    if rand < 0.80:
                        status = 'PRESENT'
                        check_in = f"{random.randint(8, 10):02d}:{random.randint(0, 59):02d}:00"
                        check_out = f"{random.randint(17, 19):02d}:{random.randint(0, 59):02d}:00"
                    elif rand < 0.90:
                        status = 'WFH'
                        check_in = f"{random.randint(8, 10):02d}:{random.randint(0, 59):02d}:00"
                        check_out = f"{random.randint(17, 19):02d}:{random.randint(0, 59):02d}:00"
                    elif rand < 0.95:
                        status = 'HALF_DAY'
                        check_in = f"{random.randint(8, 10):02d}:{random.randint(0, 59):02d}:00"
                        check_out = f"{random.randint(13, 14):02d}:{random.randint(0, 59):02d}:00"
                    else:
                        status = 'ABSENT'
                        check_in = None
                        check_out = None

                    Attendance.objects.get_or_create(
                        employee=emp,
                        date=d,
                        defaults={
                            'check_in_time': check_in,
                            'check_out_time': check_out,
                            'status': status,
                            'shift': 'GENERAL',
                            'working_hours': random.randint(8, 10) if status in ['PRESENT', 'WFH'] else (4 if status == 'HALF_DAY' else 0),
                        }
                    )
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'   ✅ {count} attendance records created'))

    def _seed_leave_applications(self):
        """Seed sample leave applications."""
        from hr.models import Employee, LeaveType, LeaveApplication

        self.stdout.write('📝 Seeding leave applications...')

        employees = Employee.objects.filter(status='ACTIVE')
        leave_types = list(LeaveType.objects.filter(code__in=['CL', 'SL', 'EL']))

        count = 0
        for emp in employees:
            # Each employee gets 1-3 leave applications in the past
            num_leaves = random.randint(0, 3)
            for _ in range(num_leaves):
                lt = random.choice(leave_types)
                start_day = random.randint(1, 20)
                duration = random.randint(1, 3)
                d_from = date(date.today().year, date.today().month - random.randint(1, 3), start_day)
                if d_from.month < 1:
                    continue
                d_to = d_from + timedelta(days=duration - 1)

                status = random.choice(['PENDING', 'APPROVED', 'REJECTED', 'APPROVED', 'APPROVED'])
                LeaveApplication.objects.get_or_create(
                    employee=emp,
                    leave_type=lt,
                    date_from=d_from,
                    date_to=d_to,
                    defaults={
                        'number_of_days': duration,
                        'reason': random.choice([
                            'Family function', 'Not feeling well', 'Personal work',
                            'Vacation', 'Medical appointment', 'Family emergency'
                        ]),
                        'approval_status': status,
                        'applied_date': d_from - timedelta(days=random.randint(1, 7)),
                        'is_backdated': random.choice([True, False]),
                    }
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'   ✅ {count} leave applications created'))

    def _seed_payroll(self, months_back):
        """Seed payroll records for past months."""
        from hr.models import Employee, EmployeeSalary, Payroll, PayrollComponentDetail, SalaryComponent

        self.stdout.write(f'💳 Seeding payroll for {months_back} months...')

        employees = Employee.objects.filter(status='ACTIVE')
        components = {c.code: c for c in SalaryComponent.objects.all()}
        today = date.today()

        count = 0
        for emp in employees:
            salary = EmployeeSalary.objects.filter(employee=emp, is_active=True).first()
            if not salary:
                continue

            for m in range(months_back, 0, -1):
                month = today.month - m
                year = today.year
                if month <= 0:
                    month += 12
                    year -= 1

                gross = salary.gross_salary
                basic = salary.basic_salary
                pf_amount = (basic * Decimal('0.12')).quantize(Decimal('0.01'))
                pt_amount = Decimal('200')
                net = gross - pf_amount - pt_amount

                payroll, _ = Payroll.objects.get_or_create(
                    employee=emp,
                    month=month,
                    year=year,
                    defaults={
                        'payroll_period': f"{year}-{month:02d}",
                        'working_days': 22,
                        'present_days': Decimal(str(random.randint(18, 22))),
                        'absent_days': Decimal(str(random.randint(0, 2))),
                        'gross_salary': gross,
                        'total_deductions': pf_amount + pt_amount,
                        'net_salary': net,
                        'final_salary': net,
                        'status': 'PAID' if random.random() < 0.8 else 'PROCESSED',
                        'processed_date': date(year, month, min(25, 28)) if month <= today.month or year < today.year else None,
                    }
                )

                # Add component details
                if 'BASIC' in components:
                    PayrollComponentDetail.objects.get_or_create(
                        payroll=payroll,
                        component=components['BASIC'],
                        defaults={'amount': basic}
                    )
                if 'HRA' in components:
                    PayrollComponentDetail.objects.get_or_create(
                        payroll=payroll,
                        component=components['HRA'],
                        defaults={'amount': basic * Decimal('0.4')}
                    )

                count += 1

        self.stdout.write(self.style.SUCCESS(f'   ✅ {count} payroll records created'))

    def _seed_statutory_configs(self):
        """Seed statutory compliance configurations."""
        from hr.models import (
            PFConfiguration, ESIConfiguration, ProfessionalTaxSlab,
            TDSConfiguration, GratuityConfiguration, BonusConfiguration,
            ComplianceCalendarEntry
        )

        self.stdout.write('⚖️ Seeding statutory compliance configs...')

        # PF Configuration
        PFConfiguration.objects.get_or_create(
            effective_from=date(date.today().year, 1, 1),
            defaults={
                'employee_contribution_pct': Decimal('12.00'),
                'employer_epf_pct': Decimal('3.67'),
                'employer_eps_pct': Decimal('8.33'),
                'employer_edli_pct': Decimal('0.50'),
                'employer_admin_charges_pct': Decimal('0.50'),
                'edli_admin_charges_pct': Decimal('0.01'),
                'wage_ceiling': Decimal('15000.00'),
                'eps_max_pensionable_salary': Decimal('15000.00'),
                'is_active': True,
            }
        )

        # ESI Configuration
        ESIConfiguration.objects.get_or_create(
            effective_from=date(date.today().year, 1, 1),
            defaults={
                'employee_contribution_pct': Decimal('0.75'),
                'employer_contribution_pct': Decimal('3.25'),
                'wage_ceiling': Decimal('21000.00'),
                'is_active': True,
            }
        )

        # Professional Tax Slabs (Karnataka)
        pt_slabs = [
            {'state': 'Karnataka', 'salary_from': 0, 'salary_to': 15000, 'tax_amount': 0, 'frequency': 'MONTHLY'},
            {'state': 'Karnataka', 'salary_from': 15001, 'salary_to': 20000, 'tax_amount': 150, 'frequency': 'MONTHLY'},
            {'state': 'Karnataka', 'salary_from': 20001, 'salary_to': 50000, 'tax_amount': 200, 'frequency': 'MONTHLY'},
            {'state': 'Karnataka', 'salary_from': 50001, 'salary_to': None, 'tax_amount': 300, 'frequency': 'MONTHLY'},
            {'state': 'Maharashtra', 'salary_from': 0, 'salary_to': 10000, 'tax_amount': 0, 'frequency': 'MONTHLY'},
            {'state': 'Maharashtra', 'salary_from': 10001, 'salary_to': 25000, 'tax_amount': 175, 'frequency': 'MONTHLY'},
            {'state': 'Maharashtra', 'salary_from': 25001, 'salary_to': 75000, 'tax_amount': 250, 'frequency': 'MONTHLY'},
            {'state': 'Maharashtra', 'salary_from': 75001, 'salary_to': None, 'tax_amount': 300, 'frequency': 'MONTHLY'},
            {'state': 'Delhi', 'salary_from': 0, 'salary_to': None, 'tax_amount': 208, 'frequency': 'MONTHLY'},
            {'state': 'Telangana', 'salary_from': 0, 'salary_to': 15000, 'tax_amount': 0, 'frequency': 'MONTHLY'},
            {'state': 'Telangana', 'salary_from': 15001, 'salary_to': 20000, 'tax_amount': 150, 'frequency': 'MONTHLY'},
            {'state': 'Telangana', 'salary_from': 20001, 'salary_to': None, 'tax_amount': 200, 'frequency': 'MONTHLY'},
        ]
        for slab in pt_slabs:
            ProfessionalTaxSlab.objects.get_or_create(
                state=slab['state'],
                salary_from=Decimal(str(slab['salary_from'])),
                salary_to=Decimal(str(slab['salary_to'])) if slab['salary_to'] else None,
                defaults={
                    'tax_amount': Decimal(str(slab['tax_amount'])),
                    'frequency': slab['frequency'],
                    'effective_from': date(date.today().year, 1, 1),
                    'is_active': True,
                }
            )

        # TDS Configuration
        TDSConfiguration.objects.get_or_create(
            financial_year=f"{date.today().year - 1}-{date.today().year}",
            defaults={
                'enable_old_regime': True,
                'enable_new_regime': True,
                'standard_deduction_old': Decimal('50000.00'),
                'standard_deduction_new': Decimal('75000.00'),
                'education_cess_pct': Decimal('4.00'),
                'is_active': True,
            }
        )

        # Gratuity Configuration
        GratuityConfiguration.objects.get_or_create(
            is_active=True,
            defaults={
                'formula_numerator': 15,
                'formula_denominator': 26,
                'min_service_years': 5,
            }
        )

        # Bonus Configuration
        fy = f"{date.today().year - 1}-{date.today().year}" if date.today().month >= 4 else f"{date.today().year - 2}-{date.today().year - 1}"
        BonusConfiguration.objects.get_or_create(
            financial_year=fy,
            defaults={
                'minimum_bonus_pct': Decimal('8.33'),
                'maximum_bonus_pct': Decimal('20.00'),
                'wage_ceiling': Decimal('21000.00'),
                'is_active': True,
            }
        )

        self.stdout.write(self.style.SUCCESS('   ✅ Statutory configs seeded'))

    def _seed_recruitment(self):
        """Seed recruitment data."""
        from hr.models import (
            Candidate, JobRequisition, JobApplication,
            Designation, Employee
        )
        from authentication.models import Department

        self.stdout.write('🎯 Seeding recruitment data...')

        hr_employee = Employee.objects.filter(department__name='Human Resources').first()
        if not hr_employee:
            return

        designations = list(Designation.objects.all()[:3])
        departments = list(Department.objects.all()[:3])

        # Job Requisitions
        requisitions = []
        for i in range(3):
            req, _ = JobRequisition.objects.get_or_create(
                department=departments[i] if i < len(departments) else departments[0],
                designation=designations[i] if i < len(designations) else designations[0],
                requested_by=hr_employee,
                defaults={
                    'vacancies': random.randint(1, 3),
                    'priority': random.choice(['High', 'Medium', 'Critical']),
                    'status': 'Approved' if i < 2 else 'Pending',
                    'justification': f'Need {random.choice(["senior", "junior", "experienced"])} engineer for {random.choice(["scaling team", "new project", "replacement"])}',
                    'budget_allocated': Decimal(str(random.randint(500000, 2000000))),
                }
            )
            requisitions.append(req)

        # Candidates
        candidate_data = [
            ('Rahul', 'Dravid', 'rahul.dravid@email.com', '7'),
            ('Sachin', 'Tendulkar', 'sachin.t@email.com', '5'),
            ('Virat', 'Kohli', 'virat.k@email.com', '3'),
            ('MS', 'Dhoni', 'ms.dhoni@email.com', '8'),
            ('Yuvraj', 'Singh', 'yuvraj.s@email.com', '4'),
            ('Rohit', 'Sharma', 'rohit.s@email.com', '6'),
            ('Jasprit', 'Bumrah', 'jasprit.b@email.com', '2'),
            ('KL', 'Rahul', 'kl.rahul@email.com', '1'),
        ]

        candidates = []
        for first, last, email, exp in candidate_data:
            cand, _ = Candidate.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'phone': f"9{random.randint(7000000000, 9999999999)}",
                    'source': random.choice(['LinkedIn', 'Naukri', 'Referral', 'Company Website']),
                    'skills': random.sample(['Python', 'JavaScript', 'Django', 'React', 'AWS', 'Docker', 'SQL'], k=3),
                    'experience_years': Decimal(exp),
                }
            )
            candidates.append(cand)

        # Job Applications
        for cand in candidates[:5]:
            req = random.choice(requisitions) if requisitions else None
            if req:
                JobApplication.objects.get_or_create(
                    candidate=cand,
                    requisition=req,
                    defaults={
                        'stage': random.choice(['Applied', 'Screening', 'L1_Interview', 'L2_Interview']),
                    }
                )

        self.stdout.write(self.style.SUCCESS(f'   ✅ {len(candidates)} candidates, {len(requisitions)} requisitions seeded'))

    def _seed_exit_data(self):
        """Seed exit management data for separated employees."""
        from hr.models import Employee, Resignation, ExitClearance

        self.stdout.write('🚪 Seeding exit management data...')

        # Find separated employees or create one
        separated_emp = Employee.objects.filter(status='SEPARATED').first()
        if not separated_emp:
            # Use a random employee and mark as separated for demo
            separated_emp = Employee.objects.filter(status='ACTIVE').exclude(
                designation__code='CEO'
            ).first()
            if separated_emp:
                separated_emp.status = 'SEPARATED'
                separated_emp.separation_date = date.today() - timedelta(days=30)
                separated_emp.separation_reason = 'RESIGNED'
                separated_emp.save()

        if separated_emp:
            # Create resignation
            resignation, _ = Resignation.objects.get_or_create(
                employee=separated_emp,
                defaults={
                    'reason': 'Relocation to another city',
                    'requested_last_working_day': date.today() - timedelta(days=7),
                    'approved_last_working_day': date.today() - timedelta(days=5),
                    'status': 'Approved',
                }
            )

            # Create exit clearances
            for dept_code, dept_name in [('IT', 'IT'), ('ADMIN', 'Admin'), ('FINANCE', 'Finance'), ('HR', 'HR')]:
                ExitClearance.objects.get_or_create(
                    resignation=resignation,
                    department_code=dept_code,
                    defaults={
                        'department_name': dept_name,
                        'is_cleared': True,
                    }
                )

        self.stdout.write(self.style.SUCCESS('   ✅ Exit data seeded'))

    def _seed_training(self):
        """Seed training and skill data."""
        from hr.models import (
            TrainingProgram, TrainingNomination, Employee,
            Skill, EmployeeSkill
        )

        self.stdout.write('🎓 Seeding training data...')

        # Training Programs
        programs = [
            {'name': 'AWS Cloud Computing', 'description': 'Comprehensive AWS cloud training with hands-on labs', 'training_type': 'External', 'trainer_name': 'AWS Academy'},
            {'name': 'Advanced Django Workshop', 'description': 'Deep dive into Django ORM, signals, and performance', 'training_type': 'Internal', 'trainer_name': 'Senior Dev Team'},
            {'name': 'Leadership Excellence', 'description': 'Management and leadership skills for team leads', 'training_type': 'External', 'trainer_name': 'XLRI Faculty'},
            {'name': 'React Masterclass', 'description': 'Modern React with Hooks, Context, and Performance', 'training_type': 'Online', 'trainer_name': 'Udemy'},
            {'name': 'Statutory Compliance', 'description': 'PF, ESI, TDS, and labor law compliance training', 'training_type': 'Internal', 'trainer_name': 'HR Team'},
        ]

        created_programs = []
        for p in programs:
            prog, _ = TrainingProgram.objects.get_or_create(
                name=p['name'],
                defaults={
                    'description': p['description'],
                    'training_type': p['training_type'],
                    'start_date': date.today() + timedelta(days=random.randint(-30, 60)),
                    'end_date': date.today() + timedelta(days=random.randint(1, 90)),
                    'trainer_name': p['trainer_name'],
                }
            )
            created_programs.append(prog)

        # Assign skills to employees
        skills = list(Skill.objects.all())
        employees = Employee.objects.all()[:10]
        for emp in employees:
            for skill in random.sample(skills, k=min(3, len(skills))):
                EmployeeSkill.objects.get_or_create(
                    employee=emp,
                    skill=skill,
                    defaults={
                        'proficiency': random.randint(2, 5),
                        'is_verified': random.choice([True, False]),
                    }
                )

        # Training Nominations
        for emp in employees[:5]:
            for prog in created_programs[:2]:
                TrainingNomination.objects.get_or_create(
                    program=prog,
                    employee=emp,
                    defaults={
                        'status': random.choice(['Nominated', 'Approved', 'Completed']),
                    }
                )

        self.stdout.write(self.style.SUCCESS(f'   ✅ {len(created_programs)} programs, training data seeded'))

    def _seed_hr_tickets(self):
        """Seed HR helpdesk tickets."""
        from hr.models import Employee, HRTicket

        self.stdout.write('🎫 Seeding HR tickets...')

        employees = Employee.objects.all()[:5]
        ticket_types = ['PAYROLL_QUERY', 'CERTIFICATE_REQUEST', 'IT_ACCESS', 'POLICY_CLARIFICATION', 'BENEFITS']

        count = 0
        for emp in employees:
            num_tickets = random.randint(0, 2)
            for _ in range(num_tickets):
                ttype = random.choice(ticket_types)
                HRTicket.objects.get_or_create(
                    employee=emp,
                    ticket_type=ttype,
                    subject=f'{dict(HRTicket._meta.get_field("ticket_type").choices).get(ttype, "Query")} - {random.choice(["Need help", "Urgent", "Follow up", "Information needed"])}',
                    defaults={
                        'description': f'This is a sample {ttype.lower()} ticket for testing purposes.',
                        'priority': random.choice(['LOW', 'MEDIUM', 'HIGH']),
                        'status': random.choice(['OPEN', 'IN_PROGRESS', 'RESOLVED']),
                    }
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'   ✅ {count} HR tickets created'))

    def _seed_compliance_calendar(self):
        """Seed compliance calendar entries."""
        from hr.models import ComplianceCalendarEntry

        self.stdout.write('📅 Seeding compliance calendar...')

        # Populate from compliance service
        try:
            from hr.services.compliance_service import ComplianceCalendarService
            service = ComplianceCalendarService()
            service.populate_calendar(date.today().year)
            self.stdout.write(self.style.SUCCESS('   ✅ Compliance calendar populated'))
        except Exception as e:
            # Manual fallback
            year = date.today().year
            entries = [
                {'type': 'PF', 'title': f'PF ECR Filing - {date(year, 1, 1).strftime("%B %Y")}', 'due': date(year, 1, 15)},
                {'type': 'PF', 'title': f'PF Challan Payment - {date(year, 1, 1).strftime("%B %Y")}', 'due': date(year, 1, 15)},
                {'type': 'ESI', 'title': f'ESI Challan Payment - {date(year, 1, 1).strftime("%B %Y")}', 'due': date(year, 1, 15)},
                {'type': 'TDS', 'title': 'TDS Return Filing Q3', 'due': date(year, 1, 31)},
            ]
            for e in entries:
                ComplianceCalendarEntry.objects.get_or_create(
                    compliance_type=e['type'],
                    title=e['title'],
                    due_date=e['due'],
                    defaults={
                        'frequency': 'MONTHLY' if e['type'] in ['PF', 'ESI'] else 'QUARTERLY',
                        'period_year': year,
                        'status': 'PENDING',
                    }
                )
            self.stdout.write(self.style.SUCCESS('   ✅ Compliance calendar seeded with fallback'))
