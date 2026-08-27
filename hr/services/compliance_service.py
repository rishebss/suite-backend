"""
Statutory Compliance Service — PF ECR, ESI Returns, PT Challans, Gratuity, Bonus

Handles:
- PF ECR generation (EPFO ECR format)
- ESI return generation
- Professional Tax challan calculation per state
- LWF computation
- Bonus calculation under Payment of Bonus Act
- Gratuity calculation under Payment of Gratuity Act
- Compliance calendar auto-population with alerts
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Tuple

from django.db import transaction
from django.db.models import Sum, Q

from hr.models import (
    Employee, EmployeeSalary, Payroll, PayrollComponentDetail, SalaryComponent,
    PFConfiguration, PFContribution, ESIConfiguration, ESIContribution,
    ProfessionalTaxSlab, PTContribution,
    TDSConfiguration, TDSCalculation, InvestmentDeclaration,
    GratuityConfiguration, GratuityCalculation,
    BonusConfiguration, BonusCalculation,
    ComplianceCalendarEntry,
    LWFConfiguration, LWFContribution,
    Attendance
)


def get_financial_year(target_date: date = None) -> str:
    if target_date is None:
        target_date = date.today()
    if target_date.month >= 4:
        return f"{target_date.year}-{target_date.year + 1}"
    return f"{target_date.year - 1}-{target_date.year}"


class PFComplianceService:
    """Provident Fund compliance calculation and ECR generation."""

    def __init__(self, month: int, year: int):
        self.month = month
        self.year = year
        self.config = PFConfiguration.objects.filter(is_active=True).order_by('-effective_from').first()

    def calculate_pf(self, employee: Employee, basic_da: Decimal, gross_salary: Decimal) -> dict:
        """Calculate PF contributions for a single employee."""
        if not self.config:
            return self._zero_pf()

        # Check eligibility: basic+DA <= wage ceiling
        wage = min(basic_da, self.config.wage_ceiling)

        employee_pf = (wage * self.config.employee_contribution_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        employer_epf = (wage * self.config.employer_epf_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # EPS capped at pensionable salary
        eps_wage = min(wage, self.config.eps_max_pensionable_salary)
        employer_eps = (eps_wage * self.config.employer_eps_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        employer_edli = (wage * self.config.employer_edli_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        employer_admin = (wage * self.config.employer_admin_charges_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        edli_admin = (wage * self.config.edli_admin_charges_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Adjust EPF so that EPF + EPS + EDLI = employer total
        total_employer = employer_epf + employer_eps + employer_edli + employer_admin + edli_admin

        return {
            'employee_pf': employee_pf,
            'employer_epf': employer_epf,
            'employer_eps': employer_eps,
            'employer_edli': employer_edli,
            'employer_admin_charges': employer_admin,
            'edli_admin_charges': edli_admin,
            'total_employee': employee_pf,
            'total_employer': total_employer,
            'basic_da': wage,
            'uan': employee.pan_number or '',  # UAN would be stored on employee
        }

    def _zero_pf(self) -> dict:
        return {
            'employee_pf': Decimal('0'), 'employer_epf': Decimal('0'),
            'employer_eps': Decimal('0'), 'employer_edli': Decimal('0'),
            'employer_admin_charges': Decimal('0'), 'edli_admin_charges': Decimal('0'),
            'total_employee': Decimal('0'), 'total_employer': Decimal('0'),
            'basic_da': Decimal('0'), 'uan': '',
        }

    @transaction.atomic
    def process_all(self) -> dict:
        """Process PF for all eligible employees."""
        processed = 0
        errors = []

        payrolls = Payroll.objects.filter(month=self.month, year=self.year, status__in=['PROCESSED', 'APPROVED', 'PAID'])
        for payroll in payrolls.select_related('employee'):
            try:
                basic_da = PayrollComponentDetail.objects.filter(
                    payroll=payroll,
                    component__code__in=['BASIC', 'BASIC_DA', 'BASIC_SALARY']
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

                result = self.calculate_pf(payroll.employee, basic_da, payroll.gross_salary)

                PFContribution.objects.update_or_create(
                    employee=payroll.employee,
                    month=self.month,
                    year=self.year,
                    defaults={
                        'payroll': payroll,
                        'basic_da': result['basic_da'],
                        'gross_salary': payroll.gross_salary,
                        'employee_pf': result['employee_pf'],
                        'employer_epf': result['employer_epf'],
                        'employer_eps': result['employer_eps'],
                        'employer_edli': result['employer_edli'],
                        'employer_admin_charges': result['employer_admin_charges'],
                        'edli_admin_charges': result['edli_admin_charges'],
                        'total_employee_contribution': result['total_employee'],
                        'total_employer_contribution': result['total_employer'],
                    }
                )
                processed += 1
            except Exception as e:
                errors.append({'employee_id': str(payroll.employee.id), 'error': str(e)})

        return {'processed': processed, 'errors': errors, 'month': self.month, 'year': self.year}

    def generate_ecr_data(self) -> dict:
        """Generate ECR data in EPFO-compatible format."""
        contributions = PFContribution.objects.filter(month=self.month, year=self.year).select_related('employee')
        rows = []
        for c in contributions:
            emp = c.employee
            rows.append({
                'employee_id': emp.employee_id,
                'uan': c.uan or emp.aadhaar_number or '',
                'name': emp.get_full_name(),
                'basic_da': float(c.basic_da),
                'employee_pf': float(c.employee_pf),
                'employer_epf': float(c.employer_epf),
                'employer_eps': float(c.employer_eps),
                'employer_edli': float(c.employer_edli),
                'employer_admin': float(c.employer_admin_charges),
                'edli_admin': float(c.edli_admin_charges),
                'total_employee': float(c.total_employee_contribution),
                'total_employer': float(c.total_employer_contribution),
            })
        totals = contributions.aggregate(
            total_employee=Sum('total_employee_contribution'),
            total_employer=Sum('total_employer_contribution'),
            member_count=Sum('id'),
        )
        return {
            'month': self.month,
            'year': self.year,
            'establishment': {
                'est_code': 'YOUR_EST_CODE',
                'est_name': 'ByteHive Technologies',
            },
            'members': rows,
            'summary': {
                'total_members': contributions.count(),
                'total_employee_contribution': float(totals['total_employee'] or 0),
                'total_employer_contribution': float(totals['total_employer'] or 0),
                'grand_total': float((totals['total_employee'] or 0) + (totals['total_employer'] or 0)),
            }
        }


class ESIComplianceService:
    """ESI compliance calculation."""

    def __init__(self, month: int, year: int):
        self.month = month
        self.year = year
        self.config = ESIConfiguration.objects.filter(is_active=True).order_by('-effective_from').first()

    def calculate_esi(self, employee: Employee, gross_salary: Decimal) -> dict:
        """Calculate ESI contributions."""
        if not self.config or gross_salary > self.config.wage_ceiling:
            return {'employee_contribution': Decimal('0'), 'employer_contribution': Decimal('0'),
                    'total': Decimal('0'), 'is_eligible': False}

        emp_contrib = (gross_salary * self.config.employee_contribution_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        employer_contrib = (gross_salary * self.config.employer_contribution_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = emp_contrib + employer_contrib

        return {
            'employee_contribution': emp_contrib,
            'employer_contribution': employer_contrib,
            'total': total,
            'is_eligible': True,
        }

    @transaction.atomic
    def process_all(self) -> dict:
        """Process ESI for all eligible employees."""
        processed = 0
        errors = []
        payrolls = Payroll.objects.filter(month=self.month, year=self.year, status__in=['PROCESSED', 'APPROVED', 'PAID'])
        for payroll in payrolls.select_related('employee'):
            try:
                result = self.calculate_esi(payroll.employee, payroll.gross_salary)
                if result['is_eligible']:
                    ESIContribution.objects.update_or_create(
                        employee=payroll.employee,
                        month=self.month,
                        year=self.year,
                        defaults={
                            'payroll': payroll,
                            'gross_salary': payroll.gross_salary,
                            'employee_contribution': result['employee_contribution'],
                            'employer_contribution': result['employer_contribution'],
                            'total_contribution': result['total'],
                        }
                    )
                    processed += 1
            except Exception as e:
                errors.append({'employee_id': str(payroll.employee.id), 'error': str(e)})
        return {'processed': processed, 'errors': errors}


class PTComplianceService:
    """Professional Tax compliance per state."""

    def __init__(self, month: int, year: int):
        self.month = month
        self.year = year

    def calculate_pt(self, employee: Employee, gross_salary: Decimal) -> Decimal:
        """Calculate Professional Tax based on state slabs."""
        state = (employee.work_location.state if employee.work_location else 'Karnataka')

        slab = ProfessionalTaxSlab.objects.filter(
            state__iexact=state,
            salary_from__lte=gross_salary,
            is_active=True,
        ).filter(
            Q(salary_to__gte=gross_salary) | Q(salary_to__isnull=True)
        ).order_by('-salary_from').first()

        if slab:
            return slab.tax_amount
        return Decimal('0')

    @transaction.atomic
    def process_all(self) -> dict:
        """Process PT for all employees."""
        processed = 0
        payrolls = Payroll.objects.filter(month=self.month, year=self.year, status__in=['PROCESSED', 'APPROVED', 'PAID'])
        for payroll in payrolls.select_related('employee'):
            pt_amount = self.calculate_pt(payroll.employee, payroll.gross_salary)
            if pt_amount > 0:
                state = payroll.employee.work_location.state if payroll.employee.work_location else 'Karnataka'
                PTContribution.objects.update_or_create(
                    employee=payroll.employee,
                    month=self.month,
                    year=self.year,
                    defaults={
                        'payroll': payroll,
                        'gross_salary': payroll.gross_salary,
                        'pt_amount': pt_amount,
                        'state': state,
                    }
                )
                processed += 1
        return {'processed': processed}


class GratuityComplianceService:
    """Gratuity calculation and monthly provisioning."""

    def calculate_gratuity(self, employee: Employee, exit_date: date = None) -> dict:
        """Calculate gratuity for an employee."""
        config = GratuityConfiguration.objects.filter(is_active=True).order_by('-effective_from').first()
        if not config:
            return {'amount': Decimal('0'), 'eligible': False, 'years': 0}

        end_date = exit_date or date.today()
        doj = employee.date_of_joining
        years_served = (end_date - doj).days / 365.25

        if years_served < config.min_service_years:
            return {'amount': Decimal('0'), 'eligible': False, 'years': years_served}

        salary = EmployeeSalary.objects.filter(employee=employee, is_active=True).order_by('-effective_from').first()
        if not salary:
            return {'amount': Decimal('0'), 'eligible': False, 'years': years_served}

        # Gratuity = (Last drawn Basic+DA) * (15/26) * Years of service
        basic_da = salary.basic_salary
        amount = (basic_da * Decimal(str(config.formula_numerator)) / Decimal(str(config.formula_denominator))) * \
                 Decimal(str(round(years_served)))
        monthly_provision = amount / Decimal(str(round(years_served * 12))) if years_served > 0 else Decimal('0')

        return {
            'amount': amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'monthly_provision': monthly_provision.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'eligible': True,
            'years': round(years_served, 2),
        }

    def provision_all(self) -> dict:
        """Monthly gratuity provisioning for all eligible employees."""
        processed = 0
        active_employees = Employee.objects.filter(status__in=['ACTIVE', 'ONBOARDING', 'ON_LEAVE'])
        for emp in active_employees:
            result = self.calculate_gratuity(emp)
            if result['eligible']:
                GratuityCalculation.objects.update_or_create(
                    employee=emp,
                    defaults={
                        'date_of_joining': emp.date_of_joining,
                        'date_of_exit': date.today(),
                        'years_of_service': result['years'],
                        'is_eligible': True,
                        'last_drawn_basic_da': EmployeeSalary.objects.filter(
                            employee=emp, is_active=True
                        ).order_by('-effective_from').first().basic_salary,
                        'gratuity_amount': result['amount'],
                        'monthly_provision_amount': result['monthly_provision'],
                    }
                )
                processed += 1
        return {'provisioned': processed}


class BonusComplianceService:
    """Bonus calculation under Payment of Bonus Act."""

    def _compute_bonus_percentage(self, config: BonusConfiguration) -> Decimal:
        """
        Bonus % is allocable surplus / total eligible wage bill (Payment of
        Bonus Act formula), clamped to the configured [minimum, maximum] band.
        Falls back to the statutory minimum if there's no surplus or wage bill.
        """
        total_wage_bill = EmployeeSalary.objects.filter(
            employee__status='ACTIVE',
            is_active=True,
            gross_salary__lte=config.wage_ceiling,
        ).aggregate(total=Sum('gross_salary'))['total'] or Decimal('0')

        if total_wage_bill <= 0 or config.allocable_surplus <= 0:
            return config.minimum_bonus_pct

        computed_pct = (config.allocable_surplus / total_wage_bill * Decimal('100'))
        bonus_pct = max(config.minimum_bonus_pct, min(config.maximum_bonus_pct, computed_pct))
        return bonus_pct.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def calculate_bonus(self, employee: Employee, financial_year: str) -> dict:
        """Calculate annual bonus."""
        config = BonusConfiguration.objects.filter(financial_year=financial_year, is_active=True).first()
        if not config:
            return {'amount': Decimal('0'), 'eligible': False}

        salary = EmployeeSalary.objects.filter(employee=employee, is_active=True).order_by('-effective_from').first()
        if not salary or salary.gross_salary > config.wage_ceiling:
            return {'amount': Decimal('0'), 'eligible': False}

        bonus_pct = self._compute_bonus_percentage(config)
        bonus_amount = (salary.gross_salary * bonus_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return {
            'amount': bonus_amount,
            'percentage': bonus_pct,
            'eligible': True,
        }

    @transaction.atomic
    def process_all(self, financial_year: str) -> dict:
        """Process bonus for all eligible employees."""
        processed = 0
        active_employees = Employee.objects.filter(status='ACTIVE')
        for emp in active_employees:
            result = self.calculate_bonus(emp, financial_year)
            if result['eligible']:
                BonusCalculation.objects.update_or_create(
                    employee=emp,
                    financial_year=financial_year,
                    defaults={
                        'eligible_salary': EmployeeSalary.objects.filter(
                            employee=emp, is_active=True
                        ).order_by('-effective_from').first().gross_salary,
                        'bonus_percentage': result['percentage'],
                        'bonus_amount': result['amount'],
                    }
                )
                processed += 1
        return {'processed': processed}


class LWFComplianceService:
    """Labour Welfare Fund compliance calculation and challan generation."""

    def __init__(self, month: int, year: int):
        self.month = month
        self.year = year
        self.config = None

    def _get_period(self, month: int, year: int) -> str:
        """Determine LWF period based on month."""
        if month in [1, 2, 3, 4, 5, 6]:
            return 'JAN_JUN'
        elif month in [7, 8, 9, 10, 11, 12]:
            return 'JUL_DEC'
        return 'ANNUAL'

    def _get_lwf_config_for_employee(self, employee: Employee) -> Optional['LWFConfiguration']:
        """Get applicable LWF configuration for employee based on state."""
        state = (employee.work_location.state if employee.work_location else 'Unknown')
        today = date.today()

        config = LWFConfiguration.objects.filter(
            state__iexact=state,
            effective_from__lte=today,
            is_active=True
        ).order_by('-effective_from').first()

        if not config and state != 'Unknown':
            config = LWFConfiguration.objects.filter(
                state__iexact='All India',
                effective_from__lte=today,
                is_active=True
            ).order_by('-effective_from').first()

        return config

    def calculate_lwf(self, employee: Employee, gross_salary: Decimal) -> dict:
        """Calculate LWF contributions for an employee."""
        config = self._get_lwf_config_for_employee(employee)
        if not config or not (config.employee_contribution > 0 or config.employer_contribution > 0):
            return {'employee_amount': Decimal('0'), 'employer_amount': Decimal('0'), 'is_eligible': False}

        # LWF is typically calculated on basic salary, not gross
        employee_amount = (gross_salary * config.employee_contribution / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        employer_amount = (gross_salary * config.employer_contribution / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return {
            'employee_amount': employee_amount,
            'employer_amount': employer_amount,
            'total_amount': employee_amount + employer_amount,
            'config': config,
            'is_eligible': True,
        }

    @transaction.atomic
    def process_all(self) -> dict:
        """Process LWF for all eligible employees."""
        processed = 0
        errors = []

        period = self._get_period(self.month, self.year)
        payrolls = Payroll.objects.filter(month=self.month, year=self.year, status__in=['PROCESSED', 'APPROVED', 'PAID'])

        for payroll in payrolls.select_related('employee'):
            try:
                state = payroll.employee.work_location.state if payroll.employee.work_location else 'Unknown'
                config = self._get_lwf_config_for_employee(payroll.employee)

                if not config or not (config.employee_contribution > 0 or config.employer_contribution > 0):
                    continue

                result = self.calculate_lwf(payroll.employee, payroll.basic_salary)

                if result['is_eligible']:
                    LWFContribution.objects.update_or_create(
                        employee=payroll.employee,
                        period=period,
                        year=self.year,
                        defaults={
                            'payroll': payroll,
                            'config': config,
                            'state': state,
                            'employee_contribution': result['employee_amount'],
                            'employer_contribution': result['employer_amount'],
                            'total_contribution': result['total_amount'],
                            'is_challan_generated': False,
                        }
                    )
                    processed += 1

            except Exception as e:
                errors.append({'employee_id': str(payroll.employee.id), 'error': str(e)})

        return {'processed': processed, 'errors': errors, 'period': period}

    def generate_challans(self) -> dict:
        """Generate LWF challans for pending contributions."""
        contributions = LWFContribution.objects.filter(
            year=self.year,
            period=self._get_period(self.month, self.year),
            is_challan_generated=False
        ).select_related('employee', 'config')

        challans = []
        for contrib in contributions:
            state = contrib.state if contrib.state else 'Unknown'
            bank_name = f"State Bank of {state}" if state != 'Unknown' else "Main Bank"
            account_number = f"SB{contrib.employee.employee_id}"

            challan_data = {
                'employee_id': contrib.employee.employee_id,
                'employee_name': contrib.employee.get_full_name(),
                'state': state,
                'employee_amount': float(contrib.employee_contribution),
                'employer_amount': float(contrib.employer_contribution),
                'total_amount': float(contrib.total_contribution),
                'challan_date': date.today(),
                'bank_name': bank_name,
                'account_number': account_number,
                'reference': f"LWF-{contrib.period}-{contrib.year}-{contrib.employee.employee_id}",
            }

            challans.append(challan_data)

        return {'challans': challans, 'count': len(challans)}


class TDSComplianceService:
    """Tax Deducted at Source (TDS) compliance processing."""

    def __init__(self, month: int, year: int):
        self.month = month
        self.year = year
        self.financial_year = self._get_financial_year(date(year, month, 1))

    def _get_financial_year(self, target_date: date) -> str:
        """Get financial year string."""
        if target_date.month >= 4:
            return f"{target_date.year}-{target_date.year + 1}"
        return f"{target_date.year - 1}-{target_date.year}"

    def calculate_tds_monthly(self, employee: Employee, gross_salary: Decimal) -> dict:
        """Calculate monthly TDS for an employee."""
        config = TDSConfiguration.objects.filter(financial_year=self.financial_year, is_active=True).first()
        if not config:
            return {'current_tds': Decimal('0'), 'ytd_tax': Decimal('0'), 'is_eligible': False}

        # Get investment declarations for the financial year
        investment = InvestmentDeclaration.objects.filter(
            employee=employee,
            financial_year=self.financial_year,
            is_submitted=True
        ).first()

        # Determine tax regime
        tax_regime = 'OLD'
        if investment:
            tax_regime = investment.tax_regime

        # Calculate taxable income
        taxable_income = gross_salary

        if tax_regime == 'OLD':
            taxable_income -= config.standard_deduction_old

            if investment:
                taxable_income -= investment.section_80c_total
                taxable_income -= investment.section_80d_self_family
                taxable_income -= investment.section_80d_parents
                taxable_income -= investment.section_80g_total
                taxable_income -= investment.hra_rent_paid
                taxable_income -= investment.lta_claimed
                taxable_income -= investment.home_loan_interest
                taxable_income -= investment.nps_employee
                taxable_income -= investment.other_deductions

        else:  # NEW REGIME
            taxable_income -= config.standard_deduction_new
            taxable_income -= investment.section_80c_total if investment else Decimal('0')
            taxable_income -= investment.section_80d_self_family if investment else Decimal('0')
            taxable_income -= investment.section_80d_parents if investment else Decimal('0')
            taxable_income -= investment.section_80g_total if investment else Decimal('0')
            taxable_income -= investment.hra_rent_paid if investment else Decimal('0')
            taxable_income -= investment.lta_claimed if investment else Decimal('0')
            taxable_income -= investment.home_loan_interest if investment else Decimal('0')
            taxable_income -= investment.nps_employee if investment else Decimal('0')
            taxable_income -= investment.other_deductions if investment else Decimal('0')

        taxable_income = max(taxable_income, Decimal('0'))

        # Apply tax slabs (simplified - full implementation would need config)
        tax_rate = Decimal('0.05')  # Placeholder 5% for first slab
        if taxable_income > 1250000:
            tax_rate = Decimal('0.20')
        if taxable_income > 5000000:
            tax_rate = Decimal('0.30')

        tax = (taxable_income * tax_rate / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        cess = (tax * Decimal('0.04')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_tax = tax + cess

        return {
            'current_tds': total_tax,
            'ytd_tax': Decimal('0'),  # Would need YTD data
            'tax_regime': tax_regime,
            'taxable_income': taxable_income,
            'tax': tax,
            'cess': cess,
            'total_tax': total_tax,
            'is_eligible': taxable_income > 0,
        }

    @transaction.atomic
    def process_all(self) -> dict:
        """Process TDS for all eligible employees."""
        processed = 0
        errors = []

        # Get all payrolls for the month
        payrolls = Payroll.objects.filter(month=self.month, year=self.year, status__in=['PROCESSED', 'APPROVED', 'PAID'])

        for payroll in payrolls.select_related('employee'):
            try:
                result = self.calculate_tds_monthly(payroll.employee, payroll.gross_salary)

                if result['is_eligible']:
                    TDSCalculation.objects.update_or_create(
                        employee=payroll.employee,
                        payroll=payroll,
                        financial_year=self.financial_year,
                        month=self.month,
                        year=self.year,
                        defaults={
                            'tax_regime': result['tax_regime'],
                            'ytd_gross_salary': payroll.gross_salary,
                            'ytd_exemptions': Decimal('0'),  # Would need YTD aggregation
                            'ytd_standard_deduction': Decimal('0'),
                            'ytd_deductions_80c': Decimal('0'),
                            'ytd_other_deductions': Decimal('0'),
                            'ytd_taxable_income': result['taxable_income'],
                            'ytd_tax': result['current_tds'],
                            'ytd_cess': result['cess'],
                            'ytd_total_tax': result['total_tax'],
                            'ytd_tds_deducted': Decimal('0'),  # Would track actual TDS deposit
                            'current_month_tds': result['current_tds'],
                        }
                    )
                    processed += 1

            except Exception as e:
                errors.append({'employee_id': str(payroll.employee.id), 'error': str(e)})

        return {'processed': processed, 'errors': errors, 'financial_year': self.financial_year}

    def generate_quarterly_return(self) -> dict:
        """Generate quarterly TDS return in government format."""
        quarters = {
            'Q1': (7, 1, 1, 31),
            'Q2': (10, 1, 10, 31),
            'Q3': (1, 1, 1, 31),
            'Q4': (4, 1, 4, 30),
        }

        current_q = None
        for q, (m, d_start, m_end, d_end) in quarters.items():
            if self.month == m:
                current_q = q
                break

        if not current_q:
            return {'error': 'No applicable quarter for current month'}

        # Get TDS calculations for the quarter
        tds_records = TDSCalculation.objects.filter(
            year=self.year,
            month__in=[1, 2, 3] if current_q == 'Q1' else
            [4, 5, 6] if current_q == 'Q2' else
            [7, 8, 9] if current_q == 'Q3' else
            [10, 11, 12]
        )

        return_data = {
            'quarter': current_q,
            'financial_year': self.financial_year,
            'total_individuals': tds_records.count(),
            'total_tax_collected': sum(float(r.current_month_tds) for r in tds_records),
            'records': []
        }

        return return_data

    def generate_form_16(self) -> dict:
        """Generate Form 16 (TDS certificate) for employees."""
        tds_records = TDSCalculation.objects.filter(
            year=self.year,
            month=self.month
        ).select_related('employee')

        form_16_data = {
            'financial_year': self.financial_year,
            'employer_pan': 'PAN1234567A',
            'employer_name': 'BYTEHIVE TECHNOLOGIES',
            'employees': []
        }

        for record in tds_records:
            employee_data = {
                'employee_pan': record.employee.pan_number or 'PAN0000000A',
                'employee_name': record.employee.get_full_name(),
                'employee_id': record.employee.employee_id,
                'gross_salary': float(record.ytd_gross_salary),
                'standard_deduction': float(record.ytd_standard_deduction),
                'other_deductions': float(record.ytd_other_deductions),
                'taxable_income': float(record.ytd_taxable_income),
                'tax': float(record.ytd_tax),
                'cess': float(record.ytd_cess),
                'total_tds': float(record.ytd_total_tax),
                'tds_deducted': float(record.ytd_tds_deducted),
            }
            form_16_data['employees'].append(employee_data)

        return form_16_data


class ComplianceCalendarService:
    """Compliance calendar auto-population with alerts."""

    COMPLIANCE_EVENTS = {
        'PF': {
            'title': 'PF ECR Filing',
            'description': 'Monthly PF ECR filing - due date 15th of next month',
            'frequency': 'MONTHLY',
            'due_day': 15,
        },
        'PF_CHALLAN': {
            'title': 'PF Challan Payment',
            'description': 'Monthly PF contribution payment - due date 15th of next month',
            'frequency': 'MONTHLY',
            'due_day': 15,
        },
        'ESI': {
            'title': 'ESI Return Filing',
            'description': 'Half-yearly ESI return filing',
            'frequency': 'HALF_YEARLY',
            'months': [4, 10],  # April and October
        },
        'ESI_CHALLAN': {
            'title': 'ESI Challan Payment',
            'description': 'Monthly ESI contribution payment - due date 15th of next month',
            'frequency': 'MONTHLY',
            'due_day': 15,
        },
        'PT': {
            'title': 'Professional Tax Challan',
            'description': 'Monthly Professional Tax payment - due date 15th of next month',
            'frequency': 'MONTHLY',
            'due_day': 15,
        },
        'TDS': {
            'title': 'TDS Return Filing (Q1/Q2/Q3/Q4)',
            'description': 'Quarterly TDS return filing - Form 24Q',
            'frequency': 'QUARTERLY',
            'due_dates': {
                'Q1': (7, 31),  # Jul 31
                'Q2': (10, 31),  # Oct 31
                'Q3': (1, 31),   # Jan 31
                'Q4': (5, 31),   # May 31
            }
        },
        'LWF': {
            'title': 'Labour Welfare Fund',
            'description': 'LWF contribution filing - varies by state',
            'frequency': 'HALF_YEARLY',
            'months': [6, 12],
        },
        'FORM_16': {
            'title': 'Form 16 Issuance Deadline',
            'description': 'Issue Form 16 to all employees',
            'frequency': 'ANNUAL',
            'due_month': 6,  # June
            'due_day': 15,
        },
    }

    @transaction.atomic
    def populate_calendar(self, year: int) -> list:
        """Auto-populate compliance calendar for a given year."""
        entries = []
        for comp_type, config_data in self.COMPLIANCE_EVENTS.items():
            if config_data['frequency'] == 'MONTHLY':
                for month in range(1, 13):
                    due_date = date(year, month, config_data['due_day'])
                    month_end = date(year, month, 1) + timedelta(days=32)
                    month_end = month_end.replace(day=1) - timedelta(days=1)
                    self._create_entry(comp_type, f"{config_data['title']} - {date(year, month, 1).strftime('%B %Y')}",
                                       config_data['description'], due_date, 'MONTHLY', year)
            elif config_data['frequency'] == 'QUARTERLY':
                quarters = {'Q1': (7, 31), 'Q2': (10, 31), 'Q3': (1, 31), 'Q4': (5, 31)}
                for q, (m, d) in quarters.items():
                    due_date = date(year, m, d)
                    self._create_entry(comp_type, f"{config_data['title'].replace('Q1/Q2/Q3/Q4', q)} - {year}",
                                       config_data['description'], due_date, 'QUARTERLY', year)
            elif config_data['frequency'] == 'HALF_YEARLY':
                for month in config_data.get('months', []):
                    due_date = date(year, month, 15)
                    period = f"Jan-Jun {year}" if month == 6 else f"Jul-Dec {year}"
                    self._create_entry(comp_type, f"{config_data['title']} - {period}",
                                       config_data['description'], due_date, 'HALF_YEARLY', year)
            elif config_data['frequency'] == 'ANNUAL':
                due_date = date(year, config_data.get('due_month', 6), config_data.get('due_day', 15))
                self._create_entry(comp_type, f"{config_data['title']} - FY {year-1}-{year}",
                                   config_data['description'], due_date, 'ANNUAL', year)
            entries.append(comp_type)
        return entries


class GovernmentPortalIntegrationService:
    """Integration service for government statutory portals."""

    def __init__(self):
        pass

    def epfo_ecr_integration(self, month: int, year: int) -> dict:
        """Generate EPFO ECR data for submission."""
        pf_service = PFComplianceService(month, year)
        ecr_data = pf_service.generate_ecr_data()

        # Format for EPFO upload
        formatted_data = {
            'transaction_id': f"ECR-{year}{month:02d}-{ecr_data['summary']['total_members']}",
            'period': f"{year}-{month:02d}",
            'establishment_code': ecr_data['establishment']['est_code'],
            'establishment_name': ecr_data['establishment']['est_name'],
            'members': ecr_data['members'],
            'summary': ecr_data['summary'],
            'checksum': self._calculate_checksum(ecr_data),
            'timestamp': datetime.now().isoformat(),
        }

        return formatted_data

    def esic_integration(self, month: int, year: int) -> dict:
        """Generate ESI return data for ESIC portal submission."""
        esi_service = ESIComplianceService(month, year)
        esi_contributions = esi_service.process_all()['processed']

        # Get ESI contributions for the month
        esi_data = ESIContribution.objects.filter(
            month=month, year=year
        ).select_related('employee', 'payroll')

        # Format for ESIC upload
        formatted_data = {
            'transaction_id': f"ESI-{year}{month:02d}-{esi_data.count()}",
            'period': f"{month:02d}/{year}",
            'establishment_code': 'ESI1234567890',
            'establishment_name': 'BYTEHIVE TECHNOLOGIES',
            'total_members': esi_data.count(),
            'total_employment_contribution': esi_data.aggregate(
                total=Sum('total_contribution')
            )['total'] or Decimal('0'),
            'records': []
        }

        for esi in esi_data:
            emp = esi.employee
            formatted_data['records'].append({
                'employee_id': emp.employee_id,
                'ip_number': emp.ip_number or '',
                'gross_salary': float(esi.gross_salary),
                'employee_contribution': float(esi.employee_contribution),
                'employer_contribution': float(esi.employer_contribution),
                'total_contribution': float(esi.total_contribution),
            })

        return formatted_data

    def traces_integration(self, financial_year: str) -> dict:
        """Generate TDS data for TRACES portal (Form 24Q)."""
        tds_service = TDSComplianceService(1, 2026)  # Current month/year for testing
        return tds_service.generate_quarterly_return()

    def _calculate_checksum(self, data: dict) -> str:
        """Generate checksum for data integrity."""
        import hashlib
        import json

        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:32]

    def bulk_upload_ecr_to_epfo(self, month: int, year: int) -> dict:
        """Simulate bulk upload of ECR to EPFO portal."""
        try:
            ecr_data = self.epfo_ecr_integration(month, year)

            # In production, this would make an authenticated API call to EPFO
            # For now, we simulate the upload process
            upload_response = {
                'success': True,
                'reference_number': ecr_data['transaction_id'],
                'upload_datetime': datetime.now().isoformat(),
                'message': 'ECR data successfully uploaded to EPFO portal',
                'validation_status': 'VALID',
                'record_count': ecr_data['summary']['total_members'],
            }

            return upload_response

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to upload ECR to EPFO portal',
            }


class ComplianceAnalyticsService:
    """Analytics and reporting service for statutory compliance."""

    def __init__(self):
        pass

    def get_compliance_dashboard(self) -> dict:
        """Get compliance dashboard analytics."""
        today = date.today()
        current_year = today.year

        dashboard = {
            'summary': {},
            'recent_alerts': {},
            'compliance_trends': {},
            'overdue_items': {},
            'quarterly_summary': {},
        }

        # Get all compliance entries
        calendar_entries = ComplianceCalendarEntry.objects.all()

        # Summary statistics
        dashboard['summary'] = {
            'total_pending': calendar_entries.filter(status='PENDING').count(),
            'total_overdue': calendar_entries.filter(status='PENDING').filter(due_date__lt=today).count(),
            'total_complete': calendar_entries.filter(status='COMPLETED').count(),
            'due_this_month': calendar_entries.filter(
                due_date__month=today.month,
                due_date__year=today.year,
                status='PENDING'
            ).count(),
        }

        # Recent alerts (next 30 days)
        recent_events = calendar_entries.filter(
            due_date__gte=today,
            due_date__lte=today + timedelta(days=30),
            status='PENDING'
        ).order_by('due_date')

        dashboard['recent_alerts'] = {
            'count': recent_events.count(),
            'by_type': {}
        }

        # Group alerts by compliance type
        for event in recent_events:
            comp_type = event.compliance_type
            if comp_type not in dashboard['recent_alerts']['by_type']:
                dashboard['recent_alerts']['by_type'][comp_type] = []

            dashboard['recent_alerts']['by_type'][comp_type].append({
                'id': str(event.id),
                'title': event.title,
                'due_date': event.due_date,
                'days_remaining': (event.due_date - today).days,
                'description': event.description,
            })

        # Overdue items
        overdue_events = calendar_entries.filter(
            due_date__lt=today,
            status='PENDING'
        ).order_by('due_date')

        dashboard['overdue_items'] = {
            'count': overdue_events.count(),
            'items': []
        }

        for event in overdue_events:
            dashboard['overdue_items']['items'].append({
                'id': str(event.id),
                'type': event.compliance_type,
                'title': event.title,
                'due_date': event.due_date,
                'days_overdue': (today - event.due_date).days,
                'description': event.description,
            })

        # Quarterly summary for last 4 quarters
        from hr.services.compliance_service import ComplianceCalendarService
        calendar_service = ComplianceCalendarService()

        quarters = []
        for i in range(4):
            quarter_year = current_year - (i // 4)
            quarter_num = ((current_year - quarter_year) * 4) - (i % 4)

            quarter_events = calendar_entries.filter(
                period_year=quarter_year,
            )

            quarters.append({
                'quarter': f"Q{quarter_num} FY {quarter_year-1}-{quarter_year}",
                'total_events': quarter_events.count(),
                'pending_events': quarter_events.filter(status='PENDING').count(),
                'overdue_events': quarter_events.filter(
                    status='PENDING', due_date__lt=today
                ).count(),
            })

        dashboard['compliance_trends'] = {'quarters': quarters}

        # Statutory compliance specific trends
        statutory_trends = {
            'pf': {'filed': 0, 'pending': 0, 'overdue': 0},
            'esi': {'filed': 0, 'pending': 0, 'overdue': 0},
            'pt': {'filed': 0, 'pending': 0, 'overdue': 0},
            'tds': {'filed': 0, 'pending': 0, 'overdue': 0},
        }

        # Get actual compliance data from models
        today = date.today()

        statutory_trends['pf']['filed'] = PFContribution.objects.filter(
            month=today.month, year=today.year
        ).exclude(is_challan_generated=False).count()

        statutory_trends['esi']['filed'] = ESIContribution.objects.filter(
            month=today.month, year=today.year
        ).exclude(is_challan_generated=False).count()

        statutory_trends['pt']['filed'] = PTContribution.objects.filter(
            month=today.month, year=today.year
        ).exclude(is_challan_generated=False).count()

        dashboard['statutory_trends'] = statutory_trends

        return dashboard

    def get_statewise_pt_analytics(self, state: str = None) -> dict:
        """Get Professional Tax analytics state-wise."""
        state_filters = {}
        if state:
            state_filters = {'state__iexact': state}

        pt_contributions = PTContribution.objects.filter(**state_filters).select_related('employee', 'payroll')

        analytics = {
            'total_contributions': pt_contributions.count(),
            'total_amount': pt_contributions.aggregate(total=Sum('pt_amount'))['total'] or Decimal('0'),
            'by_employee': [],
            'by_grade': {},
            'wage_slabs': {
                'below_15000': pt_contributions.filter(pt_amount=0).count(),
                '15000_20000': pt_contributions.filter(pt_amount=150).count(),
                '20001_50000': pt_contributions.filter(pt_amount__in=[200, 300]).count(),
                'above_50000': pt_contributions.filter(pt_amount=300).count(),
            }
        }

        # Employee breakdown
        for pt in pt_contributions[:20]:  # Top 20 for performance
            employee = pt.employee
            grade = employee.designation.grade if employee.designation else 'UNASSIGNED'

            if grade not in analytics['by_grade']:
                analytics['by_grade'][grade] = {'count': 0, 'total': Decimal('0')}

            analytics['by_grade'][grade]['count'] += 1
            analytics['by_grade'][grade]['total'] += pt.pt_amount

            analytics['by_employee'].append({
                'employee_id': pt.employee.employee_id,
                'name': pt.employee.get_full_name(),
                'state': pt.state,
                'pt_amount': float(pt.pt_amount),
                'gross_salary': float(pt.gross_salary),
                'contribution_percentage': (float(pt.pt_amount) / float(pt.gross_salary) * 100) if pt.gross_salary > 0 else 0,
            })

        return analytics

    def get_compliance_health_score(self) -> dict:
        """Calculate overall compliance health score (0-100)."""
        today = date.today()

        # Base score
        score = 100

        # Deduct for overdue items
        calendar_entries = ComplianceCalendarEntry.objects.all()
        overdue_count = calendar_entries.filter(
            due_date__lt=today,
            status='PENDING'
        ).count()

        # Each overdue item reduces score by 2 points (max 20 points)
        overdue_penalty = min(overdue_count * 2, 20)
        score -= overdue_penalty

        # Apply progressive reduction for pending items
        pending_count = calendar_entries.filter(status='PENDING').count()
        pending_ratio = pending_count / max(calendar_entries.count(), 1)
        score -= int(pending_ratio * 10)  # Up to 10 points for pending items

        # Statutory compliance score
        statutory_score = self._calculate_statutory_compliance_score(today)
        weighted_statutory_score = statutory_score * 0.4  # 40% weight

        final_score = max(0, int(score + weighted_statutory_score))

        return {
            'health_score': final_score,
            'grade': self._get_grade_from_score(final_score),
            'components': {
                'calendar_compliance': max(0, 100 - overdue_penalty - int(pending_ratio * 10)),
                'statutory_compliance': statutory_score,
                'overall': final_score,
            },
            'recommendations': self._generate_compliance_recommendations(final_score),
        }

    def _calculate_statutory_compliance_score(self, today: date) -> int:
        """Calculate statutory compliance score for a given date."""
        base_score = 100
        deductions = 0

        # PF compliance
        pf_contributions = PFContribution.objects.filter(month=today.month, year=today.year)
        pf_total = pf_contributions.count()

        if pf_total > 0:
            pf_completed = pf_contributions.exclude(is_ecr_generated=False).count()
            pf_score = (pf_completed / pf_total) * 100 if pf_total > 0 else 0
            deductions += (100 - pf_score) * 0.3  # 30% weight for PF

        # ESI compliance
        esi_contributions = ESIContribution.objects.filter(month=today.month, year=today.year)
        esi_total = esi_contributions.count()

        if esi_total > 0:
            esi_completed = esi_contributions.exclude(is_challan_generated=False).count()
            esi_score = (esi_completed / esi_total) * 100 if esi_total > 0 else 0
            deductions += (100 - esi_score) * 0.3  # 30% weight for ESI

        # PT compliance
        pt_contributions = PTContribution.objects.filter(month=today.month, year=today.year)
        pt_total = pt_contributions.count()

        if pt_total > 0:
            pt_completed = pt_contributions.exclude(is_challan_generated=False).count()
            pt_score = (pt_completed / pt_total) * 100 if pt_total > 0 else 0
            deductions += (100 - pt_score) * 0.2  # 20% weight for PT

        # LWF compliance
        lwf_contributions = LWFContribution.objects.filter(year=today.year, period='JUL_DEC')
        lwf_total = lwf_contributions.count()

        if lwf_total > 0:
            lwf_completed = lwf_contributions.exclude(is_challan_generated=False).count()
            lwf_score = (lwf_completed / lwf_total) * 100 if lwf_total > 0 else 0
            deductions += (100 - lwf_score) * 0.2  # 20% weight for LWF

        statutory_score = max(0, 100 - deductions)
        return int(statutory_score)

    def _get_grade_from_score(self, score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def _generate_compliance_recommendations(self, score: int) -> list:
        """Generate compliance recommendations based on score."""
        recommendations = []

        if score < 60:
            recommendations.extend([
                "Immediate action required on overdue compliance items",
                "Prioritize statutory filings (PF, ESI, PT)",
                "Implement automated compliance calendar",
                "Set up government portal integration alerts",
            ])
        elif score < 80:
            recommendations.extend([
                "Focus on reducing pending compliance items",
                "Set up automatic reminders for upcoming deadlines",
                "Regularly update statutory configurations",
            ])

        if score >= 80:
            recommendations.extend([
                "Maintain current compliance practices",
                "Set up quarterly compliance reviews",
                "Consider compliance automation tools",
            ])

        return recommendations

    def generate_annual_compliance_report(self, year: int) -> dict:
        """Generate comprehensive annual compliance report."""
        report = {
            'year': year,
            'summary': {},
            'monthly_breakdown': {},
            'statutory_compliance': {},
            'penalties_assessment': {},
            'recommendations': [],
        }

        # Monthly compliance data
        for month in range(1, 13):
            month_data = {
                'pf_filed': PFContribution.objects.filter(month=month, year=year, is_ecr_generated=True).count(),
                'esi_filed': ESIContribution.objects.filter(month=month, year=year, is_challan_generated=True).count(),
                'pt_filed': PTContribution.objects.filter(month=month, year=year, is_challan_generated=True).count(),
                'lwf_filed': LWFContribution.objects.filter(month=month, year=year, is_challan_generated=True).count(),
                'total_pending': 0,
            }

            # Calculate pending items
            calendar_entries = ComplianceCalendarEntry.objects.filter(period_year=year)
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

            month_data['total_pending'] = calendar_entries.filter(
                due_date__gte=month_start,
                due_date__lte=month_end,
                status='PENDING'
            ).count()

            report['monthly_breakdown'][f"{month:02d}-{year}"] = month_data

        # Statutory compliance summary
        report['statutory_compliance'] = {
            'pf_total_filed': PFContribution.objects.filter(year=year, is_ecr_generated=True).count(),
            'pf_total_pending': PFContribution.objects.filter(year=year, is_ecr_generated=False).count(),
            'esi_total_filed': ESIContribution.objects.filter(year=year, is_challan_generated=True).count(),
            'esi_total_pending': ESIContribution.objects.filter(year=year, is_challan_generated=False).count(),
            'pt_total_filed': PTContribution.objects.filter(year=year, is_challan_generated=True).count(),
            'pt_total_pending': PTContribution.objects.filter(year=year, is_challan_generated=False).count(),
            'lwf_total_filed': LWFContribution.objects.filter(year=year, is_challan_generated=True).count(),
            'lwf_total_pending': LWFContribution.objects.filter(year=year, is_challan_generated=False).count(),
        }

        # Calculate compliance percentage
        total_items = sum([
            report['statutory_compliance']['pf_total_filed'] + report['statutory_compliance']['pf_total_pending'],
            report['statutory_compliance']['esi_total_filed'] + report['statutory_compliance']['esi_total_pending'],
            report['statutory_compliance']['pt_total_filed'] + report['statutory_compliance']['pt_total_pending'],
            report['statutory_compliance']['lwf_total_filed'] + report['statutory_compliance']['lwf_total_pending'],
        ])

        if total_items > 0:
            filed_items = sum([
                report['statutory_compliance']['pf_total_filed'],
                report['statutory_compliance']['esi_total_filed'],
                report['statutory_compliance']['pt_total_filed'],
                report['statutory_compliance']['lwf_total_filed'],
            ])

            report['compliance_percentage'] = (filed_items / total_items) * 100
        else:
            report['compliance_percentage'] = 0

        # Generate recommendations based on report data
        if report['compliance_percentage'] < 80:
            report['recommendations'].extend([
                "Implement automated compliance tracking system",
                "Set up government portal integration for automated filing",
                "Create compliance awareness training for HR team",
                "Establish penalty avoidance protocols for overdue filings",
            ])

        return report

    def validate_compliance(self) -> dict:
        """Validate and audit compliance status across all statutory requirements."""
        today = date.today()
        validation_report = {
            'timestamp': datetime.now().isoformat(),
            'validation_status': 'SUCCESS',
            'summary': {
                'total_checks': 0,
                'passed_checks': 0,
                'failed_checks': 0,
                'warnings': [],
            },
            'detailed_results': {},
            'recommendations': [],
        }

        # 1. Compliance Calendar Validation
        validation_report['summary']['total_checks'] += 1
        calendar_entries = ComplianceCalendarEntry.objects.all()
        overdue_entries = calendar_entries.filter(due_date__lt=today, status='PENDING')
        validation_report['summary']['failed_checks'] += overdue_entries.count()

        if overdue_entries.count() > 0:
            validation_report['summary']['warnings'].extend([
                f"{overdue_entries.count()} compliance items overdue",
            ])
            validation_report['validation_status'] = 'WARNING'
        else:
            validation_report['summary']['passed_checks'] += 1

        validation_report['detailed_results']['calendar'] = {
            'status': 'PASSED' if overdue_entries.count() == 0 else 'WARNING',
            'total_entries': calendar_entries.count(),
            'overdue_count': overdue_entries.count(),
            'last_check': today.isoformat(),
        }

        # 2. PF Compliance Validation
        validation_report['summary']['total_checks'] += 1
        pf_contributions = PFContribution.objects.filter(month=today.month, year=today.year)
        pf_total = pf_contributions.count()

        if pf_total > 0:
            pf_generated = pf_contributions.exclude(is_ecr_generated=False).count()
            pf_success_rate = (pf_generated / pf_total) * 100

            if pf_success_rate < 100:
                validation_report['summary']['failed_checks'] += pf_total - pf_generated
                validation_report['summary']['warnings'].append(f"PF ECR: {pf_total - pf_generated}/{pf_total} not generated")
                validation_report['validation_status'] = 'WARNING'
                validation_report['detailed_results']['pf'] = {
                    'status': 'WARNING',
                    'total_contributions': pf_total,
                    'generated_count': pf_generated,
                    'generation_rate': pf_success_rate,
                }
            else:
                validation_report['summary']['passed_checks'] += 1
                validation_report['detailed_results']['pf'] = {
                    'status': 'PASSED',
                    'total_contributions': pf_total,
                    'generated_count': pf_generated,
                    'generation_rate': pf_success_rate,
                }

        # 3. ESI Compliance Validation
        validation_report['summary']['total_checks'] += 1
        esi_contributions = ESIContribution.objects.filter(month=today.month, year=today.year)
        esi_total = esi_contributions.count()

        if esi_total > 0:
            esi_generated = esi_contributions.exclude(is_challan_generated=False).count()
            esi_success_rate = (esi_generated / esi_total) * 100

            if esi_success_rate < 100:
                validation_report['summary']['failed_checks'] += esi_total - esi_generated
                validation_report['summary']['warnings'].append(f"ESI Challan: {esi_total - esi_generated}/{esi_total} not generated")
                validation_report['validation_status'] = 'WARNING'
                validation_report['detailed_results']['esi'] = {
                    'status': 'WARNING',
                    'total_contributions': esi_total,
                    'generated_count': esi_generated,
                    'generation_rate': esi_success_rate,
                }
            else:
                validation_report['summary']['passed_checks'] += 1
                validation_report['detailed_results']['esi'] = {
                    'status': 'PASSED',
                    'total_contributions': esi_total,
                    'generated_count': esi_generated,
                    'generation_rate': esi_success_rate,
                }

        # 4. PT Compliance Validation
        validation_report['summary']['total_checks'] += 1
        pt_contributions = PTContribution.objects.filter(month=today.month, year=today.year)
        pt_total = pt_contributions.count()

        if pt_total > 0:
            pt_generated = pt_contributions.exclude(is_challan_generated=False).count()
            pt_success_rate = (pt_generated / pt_total) * 100

            if pt_success_rate < 100:
                validation_report['summary']['failed_checks'] += pt_total - pt_generated
                validation_report['summary']['warnings'].append(f"PT Challan: {pt_total - pt_generated}/{pt_total} not generated")
                validation_report['validation_status'] = 'WARNING'
                validation_report['detailed_results']['pt'] = {
                    'status': 'WARNING',
                    'total_contributions': pt_total,
                    'generated_count': pt_generated,
                    'generation_rate': pt_success_rate,
                }
            else:
                validation_report['summary']['passed_checks'] += 1
                validation_report['detailed_results']['pt'] = {
                    'status': 'PASSED',
                    'total_contributions': pt_total,
                    'generated_count': pt_generated,
                    'generation_rate': pt_success_rate,
                }

        # 5. LWF Compliance Validation
        validation_report['summary']['total_checks'] += 1
        lwf_contributions = LWFContribution.objects.filter(year=today.year, period='JUL_DEC')
        lwf_total = lwf_contributions.count()

        if lwf_total > 0:
            lwf_generated = lwf_contributions.exclude(is_challan_generated=False).count()
            lwf_success_rate = (lwf_generated / lwf_total) * 100

            if lwf_success_rate < 100:
                validation_report['summary']['failed_checks'] += lwf_total - lwf_generated
                validation_report['summary']['warnings'].append(f"LWF Challan: {lwf_total - lwf_generated}/{lwf_total} not generated")
                validation_report['validation_status'] = 'WARNING'
                validation_report['detailed_results']['lwf'] = {
                    'status': 'WARNING',
                    'total_contributions': lwf_total,
                    'generated_count': lwf_generated,
                    'generation_rate': lwf_success_rate,
                }
            else:
                validation_report['summary']['passed_checks'] += 1
                validation_report['detailed_results']['lwf'] = {
                    'status': 'PASSED',
                    'total_contributions': lwf_total,
                    'generated_count': lwf_generated,
                    'generation_rate': lwf_success_rate,
                }

        # 6. Configuration Validation
        validation_report['summary']['total_checks'] += 1
        pf_config = PFConfiguration.objects.filter(is_active=True).first()
        esi_config = ESIConfiguration.objects.filter(is_active=True).first()

        if pf_config and esi_config:
            validation_report['summary']['passed_checks'] += 1
            validation_report['detailed_results']['configuration'] = {
                'status': 'PASSED',
                'pf_configured': True,
                'esi_configured': True,
                'configurations_verified': True,
            }
        else:
            validation_report['summary']['failed_checks'] += 1
            validation_report['validation_status'] = 'FAILED'
            validation_report['detailed_results']['configuration'] = {
                'status': 'FAILED',
                'pf_configured': bool(pf_config),
                'esi_configured': bool(esi_config),
                'error': 'Missing critical statutory configurations',
            }

        # Generate recommendations based on validation results
        if validation_report['summary']['failed_checks'] > 0:
            validation_report['recommendations'].extend([
                "Immediately address all overdue compliance items",
                "Ensure proper challan generation for all statutory contributions",
                "Update and verify statutory configurations",
                "Implement automated compliance reminders",
            ])

        if validation_report['summary']['warnings']:
            validation_report['recommendations'].extend([
                "Set up alerts for compliance items close to deadline",
                "Create escalation procedures for non-compliance",
                "Conduct quarterly compliance health checks",
            ])

        if validation_report['summary']['failed_checks'] == 0:
            validation_report['recommendations'].extend([
                "Maintain current compliance practices",
                "Schedule regular compliance health checks",
                "Consider implementing compliance automation tools",
            ])

        return validation_report

    def _create_entry(self, comp_type, title, description, due_date, frequency, year):
        ComplianceCalendarEntry.objects.get_or_create(
            compliance_type=comp_type.split('_')[0] if '_' in comp_type else comp_type,
            title=title,
            due_date=due_date,
            defaults={
                'description': description,
                'frequency': frequency,
                'period_year': year,
                'status': 'PENDING',
            }
        )

    def get_upcoming_alerts(self, days: int = 15) -> list:
        """Get upcoming compliance alerts."""
        from datetime import date, timedelta
        today = date.today()
        cutoff = today + timedelta(days=days)
        events = ComplianceCalendarEntry.objects.filter(
            due_date__gte=today,
            due_date__lte=cutoff,
            status='PENDING',
        ).order_by('due_date')
        return [
            {
                'id': str(e.id),
                'type': e.compliance_type,
                'title': e.title,
                'due_date': e.due_date,
                'days_remaining': (e.due_date - today).days,
            }
            for e in events
        ]

    def get_overdue(self) -> list:
        """Get overdue compliance items."""
        today = date.today()
        events = ComplianceCalendarEntry.objects.filter(
            due_date__lt=today,
            status='PENDING',
        ).order_by('due_date')
        return [
            {
                'id': str(e.id),
                'type': e.compliance_type,
                'title': e.title,
                'due_date': e.due_date,
                'days_overdue': (today - e.due_date).days,
            }
            for e in events
        ]
