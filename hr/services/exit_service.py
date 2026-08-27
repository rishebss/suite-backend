"""
Exit Management & F&F Settlement Service — Complete Engine

Provides:
1. Resignation processing with notice period calculation
2. Exit clearance checklist management (IT, Admin, Finance, Projects, Library)
3. Exit interview with structured questionnaire
4. Full & Final Settlement (F&F) calculation
5. Experience letter and relieving letter generation
6. Alumni portal support
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List

from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q, F

from hr.models import (
    Employee, EmployeeSalary, Resignation, ExitClearance, ExitInterview,
    ExitInterviewResponse, FnFSettlement, FnFSettlementComponent,
    Payroll, LeaveApplication, EmployeeLeaveBalance, LeaveType,
    Attendance, EmployeeLoan, EmployeeReimbursement,
    GratuityConfiguration, GratuityCalculation,
    BonusConfiguration, BonusCalculation,
)


def get_financial_year(target_date: date = None) -> str:
    if target_date is None:
        target_date = date.today()
    if target_date.month >= 4:
        return f"{target_date.year}-{target_date.year + 1}"
    return f"{target_date.year - 1}-{target_date.year}"


class ExitManagementEngine:
    """
    Complete exit management and F&F settlement engine.
    """

    def __init__(self, employee: Employee):
        self.employee = employee

    # ------------------------------------------------------------------
    # 1. RESIGNATION PROCESSING
    # ------------------------------------------------------------------

    def calculate_last_working_day(self, submitted_date: date, notice_period_days: int = None) -> date:
        """Calculate last working day based on notice period or contract."""
        if notice_period_days is None:
            notice_period_days = self.employee.notice_period_days or 30
        
        last_day = submitted_date + timedelta(days=notice_period_days)
        return last_day

    def calculate_notice_buyout_amount(self, notice_period_days: int, monthly_gross: Decimal) -> Decimal:
        """Calculate amount if employee buys out notice period."""
        if notice_period_days <= 0:
            return Decimal('0')
        daily_rate = monthly_gross / Decimal('30')
        buyout = daily_rate * Decimal(str(notice_period_days))
        return buyout.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # ------------------------------------------------------------------
    # 2. EXIT CLEARANCE
    # ------------------------------------------------------------------

    CLEARANCE_DEPARTMENTS = [
        ('IT', 'Information Technology'),
        ('ADMIN', 'Administration'),
        ('FINANCE', 'Finance'),
        ('PROJECTS', 'Projects'),
        ('HR', 'Human Resources'),
        ('LIBRARY', 'Library'),
        ('SECURITY', 'Security'),
    ]

    def init_clearance_checklist(self, resignation: Resignation) -> list:
        """Initialize clearance checklists for all departments."""
        clearances = []
        for dept_code, dept_name in self.CLEARANCE_DEPARTMENTS:
            clearance, created = ExitClearance.objects.get_or_create(
                resignation=resignation,
                department_code=dept_code,
                defaults={
                    'department_name': dept_name,
                    'is_cleared': False,
                }
            )
            clearances.append(clearance)
        return clearances

    def get_clearance_status(self, resignation: Resignation) -> dict:
        """Get clearance status summary."""
        clearances = ExitClearance.objects.filter(resignation=resignation)
        total = clearances.count()
        cleared = clearances.filter(is_cleared=True).count()
        return {
            'total': total,
            'cleared': cleared,
            'pending': total - cleared,
            'all_cleared': total > 0 and total == cleared,
            'departments': [
                {
                    'code': c.department_code,
                    'name': c.department_name,
                    'cleared': c.is_cleared,
                    'comments': c.comments,
                    'cleared_by': c.cleared_by.get_full_name() if c.cleared_by else None,
                    'cleared_date': c.cleared_date,
                }
                for c in clearances
            ]
        }

    # ------------------------------------------------------------------
    # 3. EXIT INTERVIEW
    # ------------------------------------------------------------------

    EXIT_INTERVIEW_QUESTIONS = [
        {
            'code': 'REASON_LEAVING',
            'question': 'What is your primary reason for leaving?',
            'type': 'choice',
            'options': ['Compensation', 'Career Growth', 'Work Culture', 'Relocation',
                       'Personal Reasons', 'Retirement', 'Health', 'Other'],
        },
        {
            'code': 'SATISFACTION',
            'question': 'How satisfied were you working here?',
            'type': 'rating',
            'scale': 5,
        },
        {
            'code': 'MANAGEMENT',
            'question': 'How would you rate your manager/supervisor?',
            'type': 'rating',
            'scale': 5,
        },
        {
            'code': 'BEST_ASPECT',
            'question': 'What did you like most about working here?',
            'type': 'text',
        },
        {
            'code': 'IMPROVEMENT',
            'question': 'What could be improved?',
            'type': 'text',
        },
        {
            'code': 'RECOMMEND',
            'question': 'Would you recommend this company to others?',
            'type': 'choice',
            'options': ['Yes', 'No', 'Maybe'],
        },
        {
            'code': 'REHIRE',
            'question': 'Would you consider re-joining in the future?',
            'type': 'choice',
            'options': ['Yes', 'No', 'Maybe'],
        },
        {
            'code': 'FEEDBACK',
            'question': 'Any additional feedback or suggestions?',
            'type': 'text',
        },
    ]

    def create_exit_interview(self, resignation: Resignation, is_anonymous: bool = False) -> ExitInterview:
        """Create exit interview with structured questions."""
        interview = ExitInterview.objects.create(
            resignation=resignation,
            employee=self.employee,
            is_anonymous=is_anonymous,
            status='PENDING',
        )
        
        for q in self.EXIT_INTERVIEW_QUESTIONS:
            ExitInterviewResponse.objects.create(
                interview=interview,
                question_code=q['code'],
                question_text=q['question'],
                response_type=q.get('type', 'text'),
                options=q.get('options'),
                rating_scale=q.get('scale'),
            )
        
        return interview

    # ------------------------------------------------------------------
    # 4. FULL & FINAL SETTLEMENT (F&F) CALCULATION
    # ------------------------------------------------------------------

    @transaction.atomic
    def calculate_fn_f(self, resignation: Resignation, exit_date: date) -> dict:
        """
        Complete F&F settlement calculation.
        
        Components:
        - Last month salary (pro-rated)
        - Leave encashment
        - Gratuity (if eligible)
        - Bonus proration
        - Notice period recovery (if applicable)
        - Loan recovery (outstanding balance)
        - Asset recovery (damages)
        """
        
        # 1. Last month salary (pro-rated to exit date)
        last_month_salary = self._calculate_last_month_salary(exit_date)
        
        # 2. Leave encashment
        leave_encashment = self._calculate_leave_encashment(exit_date)
        
        # 3. Gratuity
        gratuity = self._calculate_gratuity(exit_date)
        
        # 4. Bonus proration
        bonus = self._calculate_bonus_proration(exit_date)
        
        # 5. Notice period
        notice_recovery = self._calculate_notice_recovery(resignation, exit_date)
        
        # 6. Loan recovery
        loan_recovery = self._calculate_loan_recovery()
        
        # 7. Other deductions
        other_deductions = self._calculate_other_deductions()
        
        # Calculate totals
        total_earnings = last_month_salary['net_amount'] + leave_encashment['amount'] + gratuity['amount'] + bonus['amount']
        total_deductions = notice_recovery['amount'] + loan_recovery['amount'] + other_deductions['amount']
        net_settlement = total_earnings - total_deductions
        
        # Create F&F record
        settlement = FnFSettlement.objects.create(
            employee=self.employee,
            resignation=resignation,
            exit_date=exit_date,
            last_month_salary=last_month_salary['net_amount'],
            leave_encashment=leave_encashment['amount'],
            gratuity_amount=gratuity['amount'],
            bonus_proration=bonus['amount'],
            notice_recovery=notice_recovery['amount'],
            loan_recovery=loan_recovery['amount'],
            other_deductions=other_deductions['amount'],
            total_earnings=total_earnings,
            total_deductions=total_deductions,
            net_settlement=net_settlement,
            status='DRAFT',
        )
        
        # Create component details
        components = {
            'LAST_MONTH_SALARY': {'label': 'Last Month Salary', 'amount': last_month_salary['net_amount'], 'type': 'EARNING'},
            'LEAVE_ENCASHMENT': {'label': 'Leave Encashment', 'amount': leave_encashment['amount'], 'type': 'EARNING'},
            'GRATUITY': {'label': 'Gratuity', 'amount': gratuity['amount'], 'type': 'EARNING'},
            'BONUS_PRORATION': {'label': 'Bonus Proration', 'amount': bonus['amount'], 'type': 'EARNING'},
            'NOTICE_RECOVERY': {'label': 'Notice Period Recovery', 'amount': notice_recovery['amount'], 'type': 'DEDUCTION'},
            'LOAN_RECOVERY': {'label': 'Loan Recovery', 'amount': loan_recovery['amount'], 'type': 'DEDUCTION'},
            'OTHER_DEDUCTIONS': {'label': 'Other Deductions', 'amount': other_deductions['amount'], 'type': 'DEDUCTION'},
        }
        
        for code, comp in components.items():
            if comp['amount'] > 0:
                FnFSettlementComponent.objects.create(
                    settlement=settlement,
                    component_code=code,
                    component_label=comp['label'],
                    amount=comp['amount'],
                    component_type=comp['type'],
                )
        
        return self._build_fn_f_response(settlement, last_month_salary, leave_encashment, gratuity, bonus)

    def _calculate_last_month_salary(self, exit_date: date) -> dict:
        """Pro-rate last month's salary to exit date."""
        salary = EmployeeSalary.objects.filter(
            employee=self.employee, is_active=True
        ).order_by('-effective_from').first()
        
        if not salary:
            return {'gross_amount': Decimal('0'), 'deductions': Decimal('0'), 'net_amount': Decimal('0')}
        
        # Pro-rate for days worked
        month_days = 30  # Standard
        days_worked = exit_date.day
        ratio = Decimal(str(days_worked)) / Decimal(str(month_days))
        
        gross = (salary.gross_salary * ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        net = (salary.net_salary * ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        deductions = gross - net
        
        return {'gross_amount': gross, 'deductions': deductions, 'net_amount': net}

    def _calculate_leave_encashment(self, exit_date: date) -> dict:
        """Calculate encashment for earned leave balance."""
        financial_year = get_financial_year(exit_date)
        
        # Get encashable leave balances
        encashable_types = LeaveType.objects.filter(is_encashable=True, is_active=True)
        
        total_encashment = Decimal('0')
        details = []
        
        salary = EmployeeSalary.objects.filter(
            employee=self.employee, is_active=True
        ).order_by('-effective_from').first()
        
        if not salary:
            return {'amount': Decimal('0'), 'details': []}
        
        per_day_salary = (salary.gross_salary / Decimal('30')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        for leave_type in encashable_types:
            balance = EmployeeLeaveBalance.objects.filter(
                employee=self.employee,
                leave_type=leave_type,
                financial_year=financial_year,
            ).first()
            
            if balance and balance.current_balance > 0:
                max_encashable = min(balance.current_balance, 
                    Decimal(str(leave_type.encashment_max_days)) if leave_type.encashment_max_days > 0 else balance.current_balance)
                amount = (per_day_salary * max_encashable).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                total_encashment += amount
                details.append({
                    'leave_type': leave_type.name,
                    'days': float(max_encashable),
                    'amount': float(amount),
                })
        
        return {'amount': total_encashment, 'details': details}

    def _calculate_gratuity(self, exit_date: date) -> dict:
        """Calculate gratuity based on service years."""
        from datetime import date as dt_date
        doj = self.employee.date_of_joining
        years_served = (exit_date - doj).days / 365.25
        
        config = GratuityConfiguration.objects.filter(is_active=True).first()
        if not config:
            return {'amount': Decimal('0'), 'is_eligible': False, 'years': years_served}
        
        if years_served < config.min_service_years:
            return {'amount': Decimal('0'), 'is_eligible': False, 'years': years_served}
        
        salary = EmployeeSalary.objects.filter(
            employee=self.employee, is_active=True
        ).order_by('-effective_from').first()
        
        if not salary:
            return {'amount': Decimal('0'), 'is_eligible': False, 'years': years_served}
        
        basic_da = salary.basic_salary
        gratuity = (basic_da * Decimal(str(config.formula_numerator)) / Decimal(str(config.formula_denominator))) * \
                   Decimal(str(round(years_served)))
        
        return {
            'amount': gratuity.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'is_eligible': True,
            'years': round(years_served, 2),
        }

    def _calculate_bonus_proration(self, exit_date: date) -> dict:
        """Calculate prorated bonus if applicable."""
        config = BonusConfiguration.objects.filter(
            financial_year=get_financial_year(exit_date),
            is_active=True,
        ).first()
        
        if not config:
            return {'amount': Decimal('0'), 'is_eligible': False}
        
        salary = EmployeeSalary.objects.filter(
            employee=self.employee, is_active=True
        ).order_by('-effective_from').first()
        
        if not salary:
            return {'amount': Decimal('0'), 'is_eligible': False}
        
        # Check eligibility (salary <= wage ceiling)
        if salary.gross_salary > config.wage_ceiling:
            return {'amount': Decimal('0'), 'is_eligible': False}
        
        # Prorate: months worked / 12
        fy_start = date(exit_date.year - 1, 4, 1) if exit_date.month < 4 else date(exit_date.year, 4, 1)
        months_worked = (exit_date.year - fy_start.year) * 12 + (exit_date.month - fy_start.month)
        months_worked = max(months_worked, 0)
        
        annual_bonus_pct = config.minimum_bonus_pct  # Use minimum as default
        annual_bonus = (salary.gross_salary * annual_bonus_pct / Decimal('100'))
        prorated_bonus = (annual_bonus * Decimal(str(months_worked)) / Decimal('12'))
        
        return {
            'amount': prorated_bonus.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'is_eligible': True,
            'months_worked': months_worked,
        }

    def _calculate_notice_recovery(self, resignation: Resignation, exit_date: date) -> dict:
        """Calculate notice period recovery if notice not served."""
        notice_days = self.employee.notice_period_days or 30
        
        if resignation.approved_last_working_day:
            # Calculate unserved notice days
            expected_last_day = self.calculate_last_working_day(resignation.submitted_on, notice_days)
            if resignation.approved_last_working_day < expected_last_day:
                unserved_days = (expected_last_day - resignation.approved_last_working_day).days
                salary = EmployeeSalary.objects.filter(
                    employee=self.employee, is_active=True
                ).order_by('-effective_from').first()
                if salary:
                    daily_rate = salary.gross_salary / Decimal('30')
                    recovery = (daily_rate * Decimal(str(unserved_days))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    return {'amount': recovery, 'days': unserved_days}
        
        return {'amount': Decimal('0'), 'days': 0}

    def _calculate_loan_recovery(self) -> dict:
        """Calculate outstanding loan amount to recover."""
        active_loans = EmployeeLoan.objects.filter(
            employee=self.employee,
            is_active=True,
            status__in=['APPROVED', 'ACTIVE'],
        )
        
        total_outstanding = Decimal('0')
        details = []
        
        for loan in active_loans:
            total_outstanding += loan.outstanding_amount
            details.append({
                'loan_type': loan.loan_type,
                'outstanding': float(loan.outstanding_amount),
            })
        
        return {'amount': total_outstanding, 'details': details}

    def _calculate_other_deductions(self) -> dict:
        """Calculate other deductions (assets not returned, etc.)."""
        # This would check for unreturned assets, pending advances, etc.
        return {'amount': Decimal('0'), 'details': []}

    def _build_fn_f_response(self, settlement, last_month_salary, leave_encashment, gratuity, bonus):
        """Build the F&F settlement response."""
        return {
            'settlement_id': str(settlement.id),
            'employee_id': self.employee.employee_id,
            'employee_name': self.employee.get_full_name(),
            'exit_date': settlement.exit_date,
            'status': settlement.status,
            'components': {
                'last_month_salary': {
                    'gross': float(last_month_salary['gross_amount']),
                    'net': float(last_month_salary['net_amount']),
                    'deductions': float(last_month_salary['deductions']),
                },
                'leave_encashment': {
                    'amount': float(leave_encashment['amount']),
                    'details': leave_encashment.get('details', []),
                },
                'gratuity': {
                    'amount': float(gratuity['amount']),
                    'eligible': gratuity.get('is_eligible', False),
                    'years_of_service': gratuity.get('years', 0),
                },
                'bonus_proration': {
                    'amount': float(bonus['amount']),
                    'eligible': bonus.get('is_eligible', False),
                },
            },
            'deductions': {
                'notice_recovery': float(self._calculate_notice_recovery(None, settlement.exit_date)['amount']),
                'loan_recovery': float(self._calculate_loan_recovery()['amount']),
                'other': float(self._calculate_other_deductions()['amount']),
            },
            'total_earnings': float(settlement.total_earnings),
            'total_deductions': float(settlement.total_deductions),
            'net_settlement': float(settlement.net_settlement),
        }

    # ------------------------------------------------------------------
    # 5. LETTER GENERATION
    # ------------------------------------------------------------------

    def generate_experience_letter_pdf(self, settlement: FnFSettlement) -> bytes:
        """Generate experience letter as PDF."""
        from hr.services.pdf_generation import LetterGenerator
        generator = LetterGenerator(settlement)
        return generator.generate_experience_letter()

    def generate_relieving_letter_pdf(self, settlement: FnFSettlement) -> bytes:
        """Generate relieving letter as PDF."""
        from hr.services.pdf_generation import LetterGenerator
        generator = LetterGenerator(settlement)
        return generator.generate_relieving_letter()

    def generate_experience_letter(self, settlement: FnFSettlement) -> str:
        """Generate experience letter text."""
        emp = self.employee
        doj = emp.date_of_joining
        doe = settlement.exit_date
        years = (doe - doj).days // 365
        months = ((doe - doj).days % 365) // 30
        
        letter = f"""
EXPERIENCE CERTIFICATE

Date: {date.today().strftime('%d %B %Y')}

This is to certify that Mr./Ms. {emp.get_full_name()} (Employee ID: {emp.employee_id}) 
was employed with our organization from {doj.strftime('%d %B %Y')} to {doe.strftime('%d %B %Y')}.

During their tenure of {years} year(s) and {months} month(s), they held the position of 
{emp.designation.name if emp.designation else 'Employee'} in the 
{emp.department.name if emp.department else 'organization'} department.

{emp.first_name} has been a sincere and dedicated employee. We found them to be 
honest, hardworking, and possessing good interpersonal skills.

We wish them all the best in their future endeavors.

Sincerely,

Authorized Signatory
Human Resources
"""
        return letter

    def generate_relieving_letter(self, settlement: FnFSettlement) -> str:
        """Generate relieving letter text."""
        emp = self.employee
        
        letter = f"""
RELIEVING LETTER

Date: {date.today().strftime('%d %B %Y')}

This is to certify that Mr./Ms. {emp.get_full_name()} (Employee ID: {emp.employee_id}) 
has been relieved from our services with effect from {settlement.exit_date.strftime('%d %B %Y')}.

We confirm that all dues and settlements have been cleared as per company policy.

We appreciate their contribution during their tenure and wish them success in their 
future professional endeavors.

Sincerely,

Authorized Signatory
Human Resources
"""
        return letter

    def generate_form_16(self, financial_year: str) -> str:
        """Generate Form 16 data for the exit year."""
        # This is a simplified version
        return f"""
FORM 16 (Part A & Part B)
Financial Year: {financial_year}

Employee: {self.employee.get_full_name()}
PAN: {self.employee.pan_number or 'N/A'}
Employee ID: {self.employee.employee_id}

[This would contain the full TDS certificate details]
"""


class AttritionAnalytics:
    """
    Attrition analysis and reporting.
    """
    
    @staticmethod
    def get_attrition_rate(company_id=None, start_date=None, end_date=None) -> dict:
        """Calculate attrition rate for a period."""
        from django.db.models import Count
        from datetime import date
        
        if not start_date:
            start_date = date.today() - timedelta(days=365)
        if not end_date:
            end_date = date.today()
        
        # Employees at start
        employees_at_start = Employee.objects.filter(
            date_of_joining__lt=start_date,
            is_active=True,
        ).count()
        
        # Separations during period
        separations = Employee.objects.filter(
            status='SEPARATED',
            separation_date__gte=start_date,
            separation_date__lte=end_date,
        )
        
        # Joinings during period
        joinings = Employee.objects.filter(
            date_of_joining__gte=start_date,
            date_of_joining__lte=end_date,
        )
        
        avg_employees = employees_at_start + (joinings.count() - separations.count()) / 2
        if avg_employees <= 0:
            return {'attrition_rate': 0, 'voluntary': 0, 'involuntary': 0}
        
        voluntary = separations.filter(separation_reason='RESIGNED').count()
        involuntary = separations.exclude(separation_reason='RESIGNED').count()
        
        attrition_rate = (separations.count() / avg_employees * 100) if avg_employees > 0 else 0
        
        # Department-wise breakdown
        dept_attrition = {}
        for dept in separations.values('department__name').annotate(count=Count('id')):
            name = dept['department__name'] or 'Unknown'
            dept_attrition[name] = dept['count']
        
        return {
            'period': f'{start_date} to {end_date}',
            'employees_at_start': employees_at_start,
            'separations': separations.count(),
            'joinings': joinings.count(),
            'attrition_rate': round(attrition_rate, 2),
            'voluntary_separations': voluntary,
            'involuntary_separations': involuntary,
            'regrettable_attrition': 0,  # Would need performance rating correlation
            'department_breakdown': dept_attrition,
        }
