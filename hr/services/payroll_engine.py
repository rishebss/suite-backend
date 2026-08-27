"""
Payroll Engine — Core Salary Calculation & Processing Service

Provides:
1. Attendance-based salary pro-ration
2. Statutory deduction computation (PF, ESI, PT, TDS)
3. Salary revision processing
4. Loan/advance deduction
5. Arrears calculation
6. Bank file generation
7. Parallel (test mode) payroll run
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple

from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q, F, Count



from hr.models import (
    Employee, EmployeeSalary, Payroll, PayrollComponentDetail,
    SalaryComponent, SalaryStructureDetail, Attendance, Holiday,
    LeaveApplication, CompensatoryOff, Shift,
    PFConfiguration, PFContribution,
    ESIConfiguration, ESIContribution,
    ProfessionalTaxSlab, PTContribution,
    TDSConfiguration, TDSCalculation, InvestmentDeclaration,
    GratuityConfiguration, GratuityCalculation,
    BonusConfiguration, BonusCalculation,
    ComplianceCalendarEntry,
    EmployeeLoan, LoanRepayment,
    SalaryRevision,
    LWFConfiguration, LWFContribution,
    OvertimeRequest,
)

STANDARD_HOURS_PER_DAY = Decimal('8')


# ============================================================================
# FINANCIAL YEAR UTILITIES
# ============================================================================

def get_financial_year(target_date: date = None) -> str:
    """Get financial year string (e.g., '2025-2026') for a given date."""
    if target_date is None:
        target_date = date.today()
    if target_date.month >= 4:
        return f"{target_date.year}-{target_date.year + 1}"
    return f"{target_date.year - 1}-{target_date.year}"


def get_financial_year_start(target_date: date = None) -> date:
    """Get first date of the financial year."""
    if target_date is None:
        target_date = date.today()
    year = target_date.year
    if target_date.month >= 4:
        return date(year, 4, 1)
    return date(year - 1, 4, 1)


def get_financial_year_end(target_date: date = None) -> date:
    """Get last date of the financial year."""
    if target_date is None:
        target_date = date.today()
    year = target_date.year
    if target_date.month >= 4:
        return date(year + 1, 3, 31)
    return date(year, 3, 31)


def get_calendar_days_in_month(month: int, year: int) -> int:
    """Get total calendar days in a month."""
    if month == 12:
        return (date(year + 1, 1, 1) - date(year, month, 1)).days
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def get_working_days_in_month(month: int, year: int, holidays: list = None) -> int:
    """Calculate working days (excluding Sundays and holidays)."""
    total_days = get_calendar_days_in_month(month, year)
    working_days = 0
    holiday_dates = set()
    if holidays:
        for h in holidays:
            if hasattr(h, 'holiday_date'):
                holiday_dates.add(h.holiday_date)
    
    for day in range(1, total_days + 1):
        d = date(year, month, day)
        if d.weekday() == 6:  # Sunday
            continue
        if d in holiday_dates:
            continue
        working_days += 1
    
    return working_days


# ============================================================================
# CORE CALCULATION ENGINE
# ============================================================================

class PayrollEngine:
    """
    Core payroll calculation engine.
    
    Features:
    - Calculates monthly salary from EmployeeSalary (CTC, gross, basic)
    - Pro-rates salary based on attendance (present/absent/leave)
    - Computes all statutory deductions (PF, ESI, PT, TDS)
    - Handles arrears, loans, and reimbursements
    - Supports test mode (parallel run) vs live processing
    """

    def __init__(self, employee: Employee, month: int, year: int):
        self.employee = employee
        self.month = month
        self.year = year
        self.salary = EmployeeSalary.objects.filter(
            employee=employee, is_active=True
        ).order_by('-effective_from').first()
        
        if not self.salary:
            raise ValueError(f"No active salary found for employee {employee.employee_id}")
        
        self.financial_year = get_financial_year(date(year, month, 1))
        self.total_calendar_days = get_calendar_days_in_month(month, year)
        self.holidays = list(Holiday.objects.filter(
            holiday_date__month=month, holiday_date__year=year
        ))
        self.working_days = get_working_days_in_month(month, year, self.holidays)

        # Cache for configurations
        self._pf_config = None
        self._esi_config = None
        self._tds_config = None
        self._gratuity_config = None

    def _ytd_filter_in_fy(self) -> Q:
        """Q filter for prior months within the current financial year (excludes this month)."""
        fy_start = get_financial_year_start(date(self.year, self.month, 1))
        if fy_start.year == self.year:
            return Q(year=self.year, month__gte=fy_start.month, month__lt=self.month)
        return Q(year=fy_start.year, month__gte=fy_start.month) | Q(year=self.year, month__lt=self.month)

    # ------------------------------------------------------------------
    # 1. ATTENDANCE-BASED SALARY COMPUTATION
    # ------------------------------------------------------------------

    def get_night_shift_allowance(self) -> Decimal:
        """
        Detect night shifts for the employee in the current month and
        return the applicable night shift allowance amount.

        Checks:
        1. Employee's permanent shift setting (work_shift == 'NIGHT')
        2. Attendance records with NIGHT shift type for the current month

        The allowance rate is fetched from the Shift model configuration.
        """
        # Get night shift configuration from Shift model
        night_shift_config = Shift.objects.filter(
            shift_type='NIGHT',
            is_active=True,
        ).first()

        if not night_shift_config or night_shift_config.night_shift_allowance <= 0:
            return Decimal('0')

        monthly_allowance = night_shift_config.night_shift_allowance

        # Determine the number of night-shift days this month
        night_shift_days = 0

        # 1. If employee is on permanent night shift, apply full allowance
        if self.employee.work_shift == 'NIGHT':
            night_shift_days = self.working_days
        else:
            # 2. Count attendance records with NIGHT shift
            night_shift_days = Attendance.objects.filter(
                employee=self.employee,
                date__month=self.month,
                date__year=self.year,
                shift='NIGHT',
                status__in=['PRESENT', 'WFH'],
            ).count()

        if night_shift_days <= 0:
            return Decimal('0')

        # Pro-rate allowance based on night shift days / total working days
        if self.working_days > 0 and night_shift_days < self.working_days:
            ratio = Decimal(str(night_shift_days)) / Decimal(str(self.working_days))
            allowance = (monthly_allowance * ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            allowance = monthly_allowance

        return allowance

    def get_attendance_summary(self) -> dict:
        """
        Compute attendance summary for the month.
        
        Returns:
            dict with present_days, absent_days, half_day_count, 
            leave_days, wfh_days, working_hours
        """
        attendance_records = Attendance.objects.filter(
            employee=self.employee,
            date__month=self.month,
            date__year=self.year,
        )
        
        present = attendance_records.filter(status='PRESENT').count()
        absent = attendance_records.filter(status='ABSENT').count()
        half_day = attendance_records.filter(status='HALF_DAY').count()
        wfh = attendance_records.filter(status='WFH').count()
        on_leave = attendance_records.filter(status='ON_LEAVE').count()
        
        # If no attendance records exist, count as absent
        total_records = present + absent + half_day + wfh + on_leave
        if total_records == 0:
            absent = self.working_days
        
        return {
            'present_days': Decimal(str(present + wfh + half_day * 0.5)),
            'absent_days': Decimal(str(absent + half_day * 0.5)),
            'half_day_count': half_day,
            'leave_days': Decimal(str(on_leave)),
            'wfh_days': wfh,
        }

    def get_attendance_ratio(self, attendance_summary: dict = None) -> Decimal:
        """Fraction of the monthly salary payable based on attendance (1 = full month)."""
        if attendance_summary is None:
            attendance_summary = self.get_attendance_summary()

        base_days = self.working_days if self.working_days > 0 else 30
        present_weight = attendance_summary['present_days']

        if present_weight < base_days:
            return present_weight / Decimal(str(base_days))
        return Decimal('1')

    def calculate_gross_for_month(self, attendance_summary: dict = None) -> Decimal:
        """Calculate gross salary for the month based on attendance."""
        monthly_gross = self.salary.gross_salary
        ratio = self.get_attendance_ratio(attendance_summary)

        if ratio < Decimal('1'):
            return (monthly_gross * ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal(str(monthly_gross))

    # ------------------------------------------------------------------
    # 1b. NIGHT SHIFT ALLOWANCE AUTO-PUSH
    # ------------------------------------------------------------------

    def _add_night_shift_allowance(self, computed_gross: Decimal) -> tuple:
        """
        Auto-detect night shifts and add the night shift allowance
        to the gross salary if applicable.

        Returns:
            tuple: (adjusted_gross, night_shift_allowance_amount)
        """
        allowance = self.get_night_shift_allowance()
        if allowance > 0:
            return (computed_gross + allowance, allowance)
        return (computed_gross, Decimal('0'))

    # ------------------------------------------------------------------
    # 2. STATUTORY DEDUCTION CALCULATIONS
    # ------------------------------------------------------------------

    def get_pf_config(self) -> Optional[PFConfiguration]:
        """Get active PF configuration."""
        if self._pf_config is None:
            self._pf_config = PFConfiguration.objects.filter(
                effective_from__lte=date(self.year, self.month, 1),
                is_active=True
            ).order_by('-effective_from').first()
        return self._pf_config

    def calculate_pf(self, basic_da: Decimal) -> dict:
        """
        Calculate PF contributions for the month.
        
        Returns:
            dict with employee_pf, employer_epf, employer_eps, 
            employer_edli, admin_charges, total_employee, total_employer
        """
        config = self.get_pf_config()
        if not config:
            return {
                'employee_pf': Decimal('0'),
                'employer_epf': Decimal('0'),
                'employer_eps': Decimal('0'),
                'employer_edli': Decimal('0'),
                'employer_admin_charges': Decimal('0'),
                'edli_admin_charges': Decimal('0'),
                'total_employee_contribution': Decimal('0'),
                'total_employer_contribution': Decimal('0'),
            }
        
        # PF is capped at wage ceiling
        pensionable_wages = min(basic_da, config.wage_ceiling)
        eps_wages = min(basic_da, config.eps_max_pensionable_salary)
        
        employee_pf = (pensionable_wages * config.employee_contribution_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        employer_epf = (pensionable_wages * config.employer_epf_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        employer_eps = (eps_wages * config.employer_eps_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # EPS is capped at ₹1,250/month
        eps_max = Decimal('1250.00')
        employer_eps = min(employer_eps, eps_max)
        
        employer_edli = (pensionable_wages * config.employer_edli_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        employer_admin = (pensionable_wages * config.employer_admin_charges_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        edli_admin = (pensionable_wages * config.edli_admin_charges_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            'employee_pf': employee_pf,
            'employer_epf': employer_epf,
            'employer_eps': employer_eps,
            'employer_edli': employer_edli,
            'employer_admin_charges': employer_admin,
            'edli_admin_charges': edli_admin,
            'total_employee_contribution': employee_pf,
            'total_employer_contribution': employer_epf + employer_eps + employer_edli + employer_admin + edli_admin,
        }

    def get_esi_config(self) -> Optional[ESIConfiguration]:
        """Get active ESI configuration."""
        if self._esi_config is None:
            self._esi_config = ESIConfiguration.objects.filter(
                effective_from__lte=date(self.year, self.month, 1),
                is_active=True
            ).order_by('-effective_from').first()
        return self._esi_config

    def calculate_esi(self, gross_salary: Decimal) -> dict:
        """
        Calculate ESI contributions for the month.
        
        Returns:
            dict with employee_contribution, employer_contribution, total, is_eligible
        """
        config = self.get_esi_config()
        if not config or gross_salary > config.wage_ceiling:
            return {
                'employee_contribution': Decimal('0'),
                'employer_contribution': Decimal('0'),
                'total_contribution': Decimal('0'),
                'is_eligible': False,
            }
        
        employee_esi = (gross_salary * config.employee_contribution_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        employer_esi = (gross_salary * config.employer_contribution_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            'employee_contribution': employee_esi,
            'employer_contribution': employer_esi,
            'total_contribution': employee_esi + employer_esi,
            'is_eligible': True,
        }

    def calculate_pt(self, gross_salary: Decimal) -> dict:
        """
        Calculate Professional Tax based on employee's work location state.
        
        Returns:
            dict with pt_amount and state
        """
        state = None
        if self.employee.work_location:
            state = self.employee.work_location.state
        
        if not state:
            return {'pt_amount': Decimal('0'), 'state': 'Unknown'}
        
        slab = ProfessionalTaxSlab.objects.filter(
            state=state,
            salary_from__lte=gross_salary,
            effective_from__lte=date(self.year, self.month, 1),
            is_active=True,
        ).filter(
            Q(salary_to__gte=gross_salary) | Q(salary_to__isnull=True)
        ).order_by('-effective_from').first()
        
        if not slab:
            return {'pt_amount': Decimal('0'), 'state': state}
        
        return {'pt_amount': slab.tax_amount, 'state': state}

    def get_tds_config(self) -> Optional[TDSConfiguration]:
        """Get active TDS configuration for the financial year."""
        if self._tds_config is None:
            self._tds_config = TDSConfiguration.objects.filter(
                financial_year=self.financial_year,
                is_active=True
            ).first()
        return self._tds_config

    def calculate_tds(self, projected_annual_gross: Decimal, investment_declaration: InvestmentDeclaration = None) -> dict:
        """
        Calculate TDS/income tax for the month.
        
        Supports both Old and New tax regimes.
        Uses YTD data to compute this month's TDS.
        """
        config = self.get_tds_config()
        if not config:
            return {'current_month_tds': Decimal('0')}
        
        # Get YTD data (prior months within this financial year)
        ytd_payroll = Payroll.objects.filter(
            self._ytd_filter_in_fy(),
            employee=self.employee,
            status__in=['PROCESSED', 'APPROVED', 'PAID'],
        ).aggregate(
            gross=Sum('gross_salary'),
        )
        ytd_gross = ytd_payroll.get('gross') or Decimal('0')
        
        # Include this month's gross
        annual_gross = ytd_gross + projected_annual_gross
        
        # Get investment declaration
        if not investment_declaration:
            investment_declaration = InvestmentDeclaration.objects.filter(
                employee=self.employee,
                financial_year=self.financial_year,
            ).first()
        
        # Determine tax regime
        regime = 'NEW'
        declaration_80c = Decimal('0')
        hra_exemption = Decimal('0')
        lta_claimed = Decimal('0')
        home_loan_interest = Decimal('0')
        
        if investment_declaration:
            regime = investment_declaration.tax_regime
            declaration_80c = investment_declaration.section_80c_total or Decimal('0')
            hra_exemption = investment_declaration.hra_rent_paid or Decimal('0')
            lta_claimed = investment_declaration.lta_claimed or Decimal('0')
            home_loan_interest = investment_declaration.home_loan_interest or Decimal('0')
        
        # Standard deduction
        if regime == 'OLD':
            standard_deduction = config.standard_deduction_old
        else:
            standard_deduction = config.standard_deduction_new
            
        # Annual projections (extrapolate from YTD + this month), based on the
        # financial year (Apr-Mar), not the calendar year
        fy_start = get_financial_year_start(date(self.year, self.month, 1))
        months_elapsed_in_fy = (self.year - fy_start.year) * 12 + (self.month - fy_start.month) + 1
        remaining_months = 12 - months_elapsed_in_fy
        projected_annual = annual_gross + (projected_annual_gross * Decimal(str(remaining_months)))
        
        # Taxable income calculation
        if regime == 'OLD':
            # Old regime allows deductions
            section_80c = min(declaration_80c, Decimal('150000'))
            section_80d = (investment_declaration.section_80d_self_family or Decimal('0')) + \
                          (investment_declaration.section_80d_parents or Decimal('0'))
            section_80d = min(section_80d, Decimal('50000'))  # Max deduction for senior citizens
            nps_deduction = min(investment_declaration.nps_employee or Decimal('0'), Decimal('50000'))
            total_deductions = section_80c + section_80d + nps_deduction
            
            taxable_income = projected_annual - standard_deduction - total_deductions
            taxable_income = max(taxable_income, Decimal('0'))
            
            # Old regime tax slabs (FY 2025-26)
            tax = Decimal('0')
            slabs = [
                (Decimal('300000'), Decimal('0')),
                (Decimal('600000'), Decimal('0.05')),
                (Decimal('900000'), Decimal('0.10')),
                (Decimal('1200000'), Decimal('0.15')),
                (Decimal('1500000'), Decimal('0.20')),
            ]
            remaining = taxable_income
            prev_limit = Decimal('0')
            for limit, rate in slabs:
                if remaining > limit:
                    taxable_at_slab = limit - prev_limit
                    tax += taxable_at_slab * rate
                    remaining -= taxable_at_slab
                    prev_limit = limit
                else:
                    tax += remaining * rate
                    remaining = Decimal('0')
                    break
            if remaining > 0:
                tax += remaining * Decimal('0.30')
                
        else:
            # New regime — only standard deduction
            taxable_income = projected_annual - standard_deduction
            taxable_income = max(taxable_income, Decimal('0'))
            
            # New regime tax slabs (Budget 2025)
            tax = Decimal('0')
            slabs = [
                (Decimal('400000'), Decimal('0')),
                (Decimal('800000'), Decimal('0.05')),
                (Decimal('1200000'), Decimal('0.10')),
                (Decimal('1600000'), Decimal('0.15')),
                (Decimal('2000000'), Decimal('0.20')),
                (Decimal('2400000'), Decimal('0.25')),
            ]
            remaining = taxable_income
            prev_limit = Decimal('0')
            for limit, rate in slabs:
                if remaining > limit:
                    taxable_at_slab = limit - prev_limit
                    tax += taxable_at_slab * rate
                    remaining -= taxable_at_slab
                    prev_limit = limit
                else:
                    tax += remaining * rate
                    remaining = Decimal('0')
                    break
            if remaining > 0:
                tax += remaining * Decimal('0.30')
        
        # Education Cess
        cess = (tax * config.education_cess_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_annual_tax = tax + cess
        
        # Calculate this month's TDS
        ytd_tax = TDSCalculation.objects.filter(
            self._ytd_filter_in_fy(),
            employee=self.employee,
            financial_year=self.financial_year,
        ).aggregate(total=Sum('current_month_tds'))
        ytd_tds_deducted = ytd_tax.get('total') or Decimal('0')
        
        remaining_months_tax = total_annual_tax - ytd_tds_deducted
        months_left = max(12 - months_elapsed_in_fy + 1, 1)
        current_month_tds = max(
            (remaining_months_tax / Decimal(str(months_left))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            Decimal('0')
        )
        
        return {'current_month_tds': current_month_tds}

    def calculate_gratuity(self) -> dict:
        """Calculate gratuity provision for the month."""
        config = GratuityConfiguration.objects.filter(is_active=True).first()
        if not config:
            return {'provision_amount': Decimal('0'), 'is_eligible': False}
        
        from datetime import date
        doj = self.employee.date_of_joining
        today = date(self.year, self.month, 1)
        years_served = (today - doj).days / 365.25
        
        if years_served < 5:
            return {'provision_amount': Decimal('0'), 'is_eligible': False}
        
        basic_da = self.salary.basic_salary
        gratuity_per_year = (basic_da * Decimal(str(config.formula_numerator)) / Decimal(str(config.formula_denominator)))
        monthly_provision = gratuity_per_year / Decimal('12')
        
        return {
            'monthly_provision_amount': monthly_provision.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'is_eligible': True,
            'years_of_service': Decimal(str(round(years_served, 2))),
            'gratuity_amount': (gratuity_per_year * Decimal(str(years_served))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        }

    def calculate_lwf(self) -> dict:
        """
        Calculate Labour Welfare Fund contribution for the month.

        LWF is deducted in a lump sum on the last month of its period
        (June for Jan-Jun, December for Jul-Dec, March FY-end for annual
        configs), not spread across every month.
        """
        not_applicable = {
            'is_applicable': False,
            'employee_contribution': Decimal('0'),
            'employer_contribution': Decimal('0'),
            'period': None,
            'state': None,
            'config_id': None,
        }

        state = self.employee.work_location.state if self.employee.work_location else None
        if not state:
            return not_applicable

        config = LWFConfiguration.objects.filter(
            state=state,
            effective_from__lte=date(self.year, self.month, 1),
            is_active=True,
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=date(self.year, self.month, 1))
        ).order_by('-effective_from').first()

        if not config:
            return not_applicable

        if config.frequency == 'ANNUAL':
            period = 'ANNUAL'
            deduction_month = 3  # financial year end
        else:  # HALF_YEARLY (and MONTHLY, which this schema doesn't distinctly support)
            period = 'JAN_JUN' if self.month <= 6 else 'JUL_DEC'
            deduction_month = 6 if period == 'JAN_JUN' else 12

        if self.month != deduction_month:
            return not_applicable

        return {
            'is_applicable': True,
            'employee_contribution': config.employee_contribution,
            'employer_contribution': config.employer_contribution,
            'period': period,
            'state': state,
            'config_id': config.id,
        }

    # ------------------------------------------------------------------
    # 3. LOAN & ADVANCE DEDUCTIONS
    # ------------------------------------------------------------------

    def calculate_loan_deductions(self) -> list:
        """
        Get outstanding loan EMIs to deduct this month.
        
        Returns:
            list of dicts with loan_id, loan_type, emi_amount, outstanding
        """
        active_loans = EmployeeLoan.objects.filter(
            employee=self.employee,
            status__in=['APPROVED', 'ACTIVE'],
            is_active=True,
            outstanding_amount__gt=0,
        )
        deductions = []
        for loan in active_loans:
            if loan.emi_amount > 0:
                # Check if this month's repayment already exists
                repayment_exists = LoanRepayment.objects.filter(
                    loan=loan,
                    month=self.month,
                    year=self.year,
                ).exists()
                if not repayment_exists:
                    # Cap the final EMI to whatever balance remains
                    emi_amount = min(loan.emi_amount, loan.outstanding_amount)
                    deductions.append({
                        'loan_id': str(loan.id),
                        'loan_type': loan.loan_type,
                        'emi_amount': emi_amount,
                        'outstanding': loan.outstanding_amount,
                    })
        return deductions

    # ------------------------------------------------------------------
    # 4. FULL PAYROLL CALCULATION
    # ------------------------------------------------------------------

    @transaction.atomic
    def process(self, processed_by, is_test_mode: bool = False, force: bool = False) -> dict:
        """
        Execute the full payroll calculation for an employee.
        
        Args:
            processed_by: User processing the payroll
            is_test_mode: If True, creates payroll as DRAFT for review
            force: If True, overwrites existing payroll for the period
            
        Returns:
            dict with calculation results
        """
        existing = Payroll.objects.filter(
            employee=self.employee,
            month=self.month,
            year=self.year,
        ).first()
        
        if existing and existing.status != 'DRAFT' and not force:
            return {
                'status': 'skipped',
                'message': f'Payroll already {existing.status} for {self.month}/{self.year}',
                'payroll_id': str(existing.id),
            }
        
        # 1. Attendance summary
        attendance = self.get_attendance_summary()
        attendance_ratio = self.get_attendance_ratio(attendance)

        # 2. Calculate gross salary (attendance-pro-rated, before night shift)
        pro_rated_gross = self.calculate_gross_for_month(attendance)

        # 2b. Auto-push night shift allowance (additive, not part of the pro-ration base)
        computed_gross, night_shift_allowance = self._add_night_shift_allowance(pro_rated_gross)

        # 2c. Overtime pay for approved, unprocessed OT requests this month
        ot_requests, ot_amount = self._get_overtime_pay()
        computed_gross += ot_amount

        # 3. Calculate earnings components (pro-rated against attendance only, not OT/night-shift)
        component_earnings = self._compute_component_breakdown(pro_rated_gross)

        # 4. Calculate statutory deductions
        basic_da = (self.salary.basic_salary * attendance_ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) \
            if attendance_ratio < Decimal('1') else self.salary.basic_salary
        pf = self.calculate_pf(basic_da)
        esi = self.calculate_esi(computed_gross)
        pt = self.calculate_pt(computed_gross)
        lwf = self.calculate_lwf()

        # 5. Calculate TDS
        tds = self.calculate_tds(computed_gross)

        # 6. Calculate loan deductions
        loan_deductions = self.calculate_loan_deductions()
        total_loan_emi = sum(d['emi_amount'] for d in loan_deductions)

        # 7. Calculate gratuity provision
        gratuity = self.calculate_gratuity()

        # 8. Total deductions
        total_statutory = (
            pf['employee_pf'] +
            esi['employee_contribution'] +
            pt['pt_amount'] +
            tds['current_month_tds'] +
            lwf['employee_contribution']
        )
        total_deductions = total_statutory + total_loan_emi

        # 9. Net salary
        net_salary = max(computed_gross - total_deductions, Decimal('0'))

        # 10. Arrears (check for pending salary revisions, including backdated multi-month ones)
        arrears = Decimal('0')
        pending_revisions = SalaryRevision.objects.filter(
            employee=self.employee,
            status='APPROVED',
            is_processed=False,
        ).filter(
            Q(effective_year__lt=self.year) |
            Q(effective_year=self.year, effective_month__lte=self.month)
        )
        revision_arrears = {}
        for rev in pending_revisions:
            months_pending = (self.year - rev.effective_year) * 12 + (self.month - rev.effective_month) + 1
            monthly_delta = (rev.revised_gross - rev.previous_gross) or Decimal('0')
            rev_arrears = (monthly_delta * months_pending).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            revision_arrears[rev.id] = rev_arrears
            arrears += rev_arrears

        final_salary = net_salary + arrears
        
        status = 'DRAFT' if is_test_mode else 'PROCESSED'
        
        # Create or update payroll
        status_default = 'DRAFT'
        if existing:
            payroll = existing
            status_default = existing.status
        else:
            payroll = Payroll(employee=self.employee, month=self.month, year=self.year)
        
        working_days = self.working_days
        
        payroll.payroll_period = f"{self.year}-{self.month:02d}"
        payroll.working_days = Decimal(str(working_days))
        payroll.present_days = attendance['present_days']
        payroll.absent_days = attendance['absent_days']
        payroll.half_day_count = attendance['half_day_count']
        payroll.leave_days = attendance['leave_days']
        payroll.gross_salary = computed_gross
        payroll.total_deductions = total_deductions
        payroll.net_salary = net_salary
        payroll.arrears = arrears
        payroll.final_salary = final_salary
        payroll.status = 'DRAFT' if is_test_mode else 'PROCESSED'
        payroll.processed_by = processed_by
        payroll.processed_date = timezone.now()
        payroll.save()
        
        # Save component details
        PayrollComponentDetail.objects.filter(payroll=payroll).delete()
        
        component_order = 0
        for comp_name, comp_amount in component_earnings.items():
            component = SalaryComponent.objects.filter(code=comp_name).first()
            if not component:
                continue
            PayrollComponentDetail.objects.create(
                payroll=payroll,
                component=component,
                amount=comp_amount,
            )
            component_order += 1
        
        # Save night shift allowance as a separate component if present
        if night_shift_allowance > 0:
            ns_component, _ = SalaryComponent.objects.get_or_create(
                code='NIGHT_SHIFT_ALLOWANCE',
                defaults={
                    'name': 'Night Shift Allowance',
                    'component_type': 'EARNINGS',
                    'is_fixed': False,
                    'is_taxable': True,
                    'is_statutory': False,
                    'order': 999,
                }
            )
            PayrollComponentDetail.objects.create(
                payroll=payroll,
                component=ns_component,
                amount=night_shift_allowance,
            )
        
        # Save PF contribution
        PFContribution.objects.update_or_create(
            employee=self.employee,
            month=self.month,
            year=self.year,
            defaults={
                'payroll': payroll,
                'basic_da': basic_da,
                'gross_salary': computed_gross,
                'employee_pf': pf['employee_pf'],
                'employer_epf': pf['employer_epf'],
                'employer_eps': pf['employer_eps'],
                'employer_edli': pf['employer_edli'],
                'employer_admin_charges': pf['employer_admin_charges'],
                'edli_admin_charges': pf['edli_admin_charges'],
                'total_employee_contribution': pf['total_employee_contribution'],
                'total_employer_contribution': pf['total_employer_contribution'],
            }
        )
        
        # Save ESI contribution
        if esi['is_eligible']:
            ESIContribution.objects.update_or_create(
                employee=self.employee,
                month=self.month,
                year=self.year,
                defaults={
                    'payroll': payroll,
                    'gross_salary': computed_gross,
                    'employee_contribution': esi['employee_contribution'],
                    'employer_contribution': esi['employer_contribution'],
                    'total_contribution': esi['total_contribution'],
                }
            )
        
        # Save PT deduction
        PTContribution.objects.update_or_create(
            employee=self.employee,
            month=self.month,
            year=self.year,
            defaults={
                'payroll': payroll,
                'gross_salary': computed_gross,
                'pt_amount': pt['pt_amount'],
                'state': pt['state'],
            }
        )
        
        # Save TDS calculation
        TDSCalculation.objects.update_or_create(
            employee=self.employee,
            financial_year=self.financial_year,
            month=self.month,
            year=self.year,
            defaults={
                'payroll': payroll,
                'tax_regime': 'NEW',
                'ytd_gross_salary': self._get_ytd_gross(),
                'current_month_tds': tds['current_month_tds'],
            }
        )
        
        # Save LWF contribution (only non-zero on the deduction month for the period)
        if lwf['is_applicable']:
            LWFContribution.objects.update_or_create(
                employee=self.employee,
                period=lwf['period'],
                year=self.year,
                defaults={
                    'payroll': payroll,
                    'config_id': lwf['config_id'],
                    'state': lwf['state'],
                    'employee_contribution': lwf['employee_contribution'],
                    'employer_contribution': lwf['employer_contribution'],
                }
            )

        # Create loan repayments and close loans that are fully paid off
        for loan_ded in loan_deductions:
            LoanRepayment.objects.create(
                loan_id=loan_ded['loan_id'],
                amount=loan_ded['emi_amount'],
                month=self.month,
                year=self.year,
                payroll=payroll,
            )
            loan = EmployeeLoan.objects.filter(id=loan_ded['loan_id']).first()
            loan.paid_amount = loan.paid_amount + loan_ded['emi_amount']
            loan.outstanding_amount = loan.outstanding_amount - loan_ded['emi_amount']
            loan.paid_emis = F('paid_emis') + 1
            if loan.outstanding_amount <= 0:
                loan.outstanding_amount = Decimal('0')
                loan.status = 'CLOSED'
                loan.closure_date = date(self.year, self.month, 1)
            loan.save()

        # Mark OT requests as processed in this payroll
        for ot in ot_requests:
            ot.status = 'PROCESSED'
            ot.payroll = payroll
            ot.save()

        # Mark salary revisions as processed and persist their computed arrears
        for rev in pending_revisions:
            rev.is_processed = True
            rev.arrears_amount = revision_arrears.get(rev.id, Decimal('0'))
            rev.processed_in_payroll = payroll
            rev.save()

        return {
            'status': status,
            'payroll_id': str(payroll.id),
            'employee_id': self.employee.employee_id,
            'employee_name': self.employee.get_full_name(),
            'gross_salary': float(computed_gross),
            'total_deductions': float(total_deductions),
            'pf_employee': float(pf['employee_pf']),
            'esi_employee': float(esi['employee_contribution']),
            'pt': float(pt['pt_amount']),
            'tds': float(tds['current_month_tds']),
            'lwf': float(lwf['employee_contribution']),
            'loan_deductions': float(total_loan_emi),
            'overtime_pay': float(ot_amount),
            'net_salary': float(net_salary),
            'arrears': float(arrears),
            'final_salary': float(final_salary),
            'present_days': float(attendance['present_days']),
            'absent_days': float(attendance['absent_days']),
            'working_days': working_days,
        }

    def _compute_component_breakdown(self, computed_gross: Decimal) -> dict:
        """Compute individual salary component amounts."""
        # Get the salary structure components
        components = {}
        if self.salary.salary_structure:
            details = SalaryStructureDetail.objects.filter(
                salary_structure=self.salary.salary_structure
            ).select_related('component').order_by('order')
            
            for detail in details:
                comp = detail.component
                if detail.is_percentage and self.salary.basic_salary:
                    amount = (self.salary.basic_salary * detail.amount / Decimal('100')).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                else:
                    amount = detail.amount
                
                # Pro-rate the amount based on attendance ratio
                if self.working_days > 0:
                    ratio = computed_gross / self.salary.gross_salary if self.salary.gross_salary > 0 else Decimal('1')
                    amount = (amount * ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                components[comp.code] = amount
        
        # If no structure, use basic components
        if not components:
            basic_ratio = self.salary.basic_salary / self.salary.gross_salary if self.salary.gross_salary > 0 else Decimal('0.5')
            components = {
                'BASIC': (computed_gross * basic_ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'HRA': (computed_gross * Decimal('0.4')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'OTHER': (computed_gross * Decimal('0.1')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            }
        
        return components

    def _get_overtime_pay(self) -> tuple:
        """
        Fetch approved, unprocessed overtime requests for this month and
        compute their pay amount.

        Returns:
            tuple: (list of OvertimeRequest instances, total ot_amount)
        """
        requests = list(OvertimeRequest.objects.filter(
            employee=self.employee,
            date__month=self.month,
            date__year=self.year,
            status='APPROVED',
        ))
        if not requests:
            return [], Decimal('0')

        per_day_rate = self.salary.basic_salary / Decimal(str(self.working_days)) \
            if self.working_days > 0 else Decimal('0')
        hourly_rate = per_day_rate / STANDARD_HOURS_PER_DAY

        total = Decimal('0')
        for req in requests:
            amount = (Decimal(str(req.ot_hours)) * hourly_rate * req.ot_rate_multiplier).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            req.ot_amount = amount
            total += amount

        return requests, total

    def _get_ytd_gross(self) -> Decimal:
        """Get YTD gross salary for TDS calculation (prior months within this financial year)."""
        ytd = Payroll.objects.filter(
            self._ytd_filter_in_fy(),
            employee=self.employee,
            status__in=['PROCESSED', 'APPROVED', 'PAID'],
        ).aggregate(total=Sum('gross_salary'))
        return ytd.get('total') or Decimal('0')


# ============================================================================
# BATCH PROCESSING
# ============================================================================

class BatchPayrollProcessor:
    """
    Process payroll for multiple employees at once.
    """
    
    def __init__(self, month: int, year: int, filters: dict = None):
        self.month = month
        self.year = year
        self.filters = filters or {}
    
    def get_eligible_employees(self):
        """Get employees eligible for payroll processing."""
        queryset = Employee.objects.filter(
            status__in=['ACTIVE', 'ON_LEAVE', 'NOTICE_PERIOD'],
            is_active=True,
        )
        if self.filters.get('department'):
            queryset = queryset.filter(department_id=self.filters['department'])
        if self.filters.get('location'):
            queryset = queryset.filter(work_location_id=self.filters['location'])
        if self.filters.get('employment_type'):
            queryset = queryset.filter(employment_type=self.filters['employment_type'])
        return queryset
    
    def process_all(self, processed_by, is_test_mode: bool = False) -> dict:
        """Process payroll for all eligible employees."""
        employees = self.get_eligible_employees()
        results = {
            'total': employees.count(),
            'success': 0,
            'skipped': 0,
            'errors': 0,
            'details': [],
        }
        
        for employee in employees:
            try:
                engine = PayrollEngine(employee, self.month, self.year)
                result = engine.process(processed_by, is_test_mode=is_test_mode)
                if result.get('status') == 'skipped':
                    results['skipped'] += 1
                else:
                    results['success'] += 1
                results['details'].append(result)
            except Exception as e:
                results['errors'] += 1
                results['details'].append({
                    'status': 'error',
                    'employee_id': employee.employee_id,
                    'employee_name': employee.get_full_name(),
                    'error': str(e),
                })
        
        return results


# ============================================================================
# BANK FILE GENERATION
# ============================================================================

class BankFileGenerator:
    """
    Generate bank transfer files in NEFT/RTGS format.
    """
    
    def __init__(self, month: int, year: int):
        self.month = month
        self.year = year
    
    def get_approved_payrolls(self):
        """Get approved payroll records for the period."""
        return Payroll.objects.filter(
            month=self.month,
            year=self.year,
            status='APPROVED',
        ).select_related('employee')
    
    def generate_neft_file(self) -> str:
        """
        Generate NEFT bulk transfer file format.
        
        Format: EmployeeID|AccountNumber|IFSC|Amount|Name|Remarks
        """
        payrolls = self.get_approved_payrolls()
        lines = []
        total_amount = Decimal('0')
        
        for payroll in payrolls:
            emp = payroll.employee
            if not emp.bank_account_number or not emp.ifsc_code:
                continue
            
            name = emp.get_full_name().upper().replace(' ', '')
            line = (
                f"{emp.employee_id}|"
                f"{emp.bank_account_number}|"
                f"{emp.ifsc_code}|"
                f"{payroll.final_salary:.2f}|"
                f"{name}|"
                f"Salary {self.month:02d}/{self.year}"
            )
            lines.append(line)
            total_amount += payroll.final_salary
        
        header = f"HDR|{self.month:02d}{self.year}|{len(lines)}|{total_amount:.2f}"
        footer = f"FTR|{len(lines)}|{total_amount:.2f}"
        return '\n'.join([header] + lines + [footer])
    
    def generate_rtgs_file(self) -> str:
        """Generate RTGS format file (similar to NEFT but with IBAN/compat fields)."""
        return self.generate_neft_file()


# ============================================================================
# PAYROLL REPORTS
# ============================================================================

class PayrollReportGenerator:
    """Generate payroll reports."""
    
    def __init__(self, month: int, year: int):
        self.month = month
        self.year = year
    
    def salary_register(self, status: str = None) -> list:
        """Generate detailed salary register."""
        payrolls = Payroll.objects.filter(month=self.month, year=self.year)
        if status:
            payrolls = payrolls.filter(status=status)
        else:
            payrolls = payrolls.filter(status__in=['PROCESSED', 'APPROVED', 'PAID'])
        payrolls = payrolls.select_related('employee', 'processed_by', 'approved_by').prefetch_related('components')
        
        register = []
        for payroll in payrolls:
            emp = payroll.employee
            entry = {
                'employee_id': emp.employee_id,
                'employee_name': emp.get_full_name(),
                'department': emp.department.name if emp.department else '',
                'designation': emp.designation.name if emp.designation else '',
                'bank_account': emp.bank_account_number or '',
                'ifsc': emp.ifsc_code or '',
                'working_days': float(payroll.working_days),
                'present_days': float(payroll.present_days),
                'absent_days': float(payroll.absent_days),
                'gross_salary': float(payroll.gross_salary),
                'total_deductions': float(payroll.total_deductions),
                'net_salary': float(payroll.net_salary),
                'arrears': float(payroll.arrears),
                'final_salary': float(payroll.final_salary),
                'status': payroll.status,
            }
            
            # Add component details
            components = payroll.components.all()
            for comp in components:
                entry[f'comp_{comp.component.code}'] = float(comp.amount)
            
            register.append(entry)
        
        return register
    
    def department_wise_summary(self) -> list:
        """Generate department-wise payroll cost summary."""
        payrolls = Payroll.objects.filter(
            month=self.month,
            year=self.year,
            status__in=['PROCESSED', 'APPROVED', 'PAID'],
        ).select_related('employee__department')
        
        summary = {}
        for payroll in payrolls:
            dept_name = payroll.employee.department.name if payroll.employee.department else 'Unassigned'
            if dept_name not in summary:
                summary[dept_name] = {
                    'department': dept_name,
                    'employee_count': 0,
                    'total_gross': Decimal('0'),
                    'total_deductions': Decimal('0'),
                    'total_net': Decimal('0'),
                }
            summary[dept_name]['employee_count'] += 1
            summary[dept_name]['total_gross'] += payroll.gross_salary
            summary[dept_name]['total_deductions'] += payroll.total_deductions
            summary[dept_name]['total_net'] += payroll.net_salary
        
        return [
            {
                'department': v['department'],
                'employee_count': v['employee_count'],
                'total_gross': float(v['total_gross']),
                'total_deductions': float(v['total_deductions']),
                'total_net': float(v['total_net']),
            }
            for v in summary.values()
        ]
    
    def variance_report(self, previous_month: int = None, previous_year: int = None) -> dict:
        """Compare current month payroll with previous month."""
        if not previous_month or not previous_year:
            if self.month == 1:
                previous_month = 12
                previous_year = self.year - 1
            else:
                previous_month = self.month - 1
                previous_year = self.year
        
        current = Payroll.objects.filter(
            month=self.month, year=self.year, status__in=['PROCESSED', 'APPROVED', 'PAID']
        ).aggregate(
            gross=Sum('gross_salary'),
            deductions=Sum('total_deductions'),
            net=Sum('net_salary'),
            count=Count('id'),
        )
        
        previous = Payroll.objects.filter(
            month=previous_month, year=previous_year, status__in=['PROCESSED', 'APPROVED', 'PAID']
        ).aggregate(
            gross=Sum('gross_salary'),
            deductions=Sum('total_deductions'),
            net=Sum('net_salary'),
            count=Count('id'),
        )
        
        def safe_subtract(curr, prev):
            c = curr or Decimal('0')
            p = prev or Decimal('0')
            if p > 0:
                return float(((c - p) / p * Decimal('100')).quantize(Decimal('0.01')))
            return 0
        
        return {
            'current_period': f"{self.month}/{self.year}",
            'previous_period': f"{previous_month}/{previous_year}",
            'total_gross_current': float(current.get('gross') or 0),
            'total_gross_previous': float(previous.get('gross') or 0),
            'gross_variance_pct': safe_subtract(current.get('gross'), previous.get('gross')),
            'total_deductions_current': float(current.get('deductions') or 0),
            'total_deductions_previous': float(previous.get('deductions') or 0),
            'deductions_variance_pct': safe_subtract(current.get('deductions'), previous.get('deductions')),
            'total_net_current': float(current.get('net') or 0),
            'total_net_previous': float(previous.get('net') or 0),
            'net_variance_pct': safe_subtract(current.get('net'), previous.get('net')),
            'employee_count_current': current.get('count') or 0,
            'employee_count_previous': previous.get('count') or 0,
        }
