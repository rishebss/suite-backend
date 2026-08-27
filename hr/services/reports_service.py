"""
Comprehensive Reports & Analytics Service for HR Module.
Provides data aggregation for CEO/CHRO dashboards, attrition analysis,
headcount trends, recruitment analytics, attendance reports, payroll reports,
compliance calendar, and training analytics.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db.models import Q, Sum, Count, Avg, Min, Max
from django.db.models.functions import TruncMonth
from django.utils import timezone
from hr.models import (
    Employee, Attendance, LeaveApplication, LeaveType,
    Payroll, EmployeeSalary, SalaryRevision,
    EmployeeLoan, EmployeeReimbursement,
    Candidate, JobApplication, InterviewSchedule, OfferLetter,
    TrainingProgram, TrainingNomination,
    Resignation, ExitInterview, ComplianceCalendarEntry,
    PFContribution, ESIContribution, PTContribution,
)


class ReportDataAggregator:
    """Aggregates data for all HR reports and dashboards."""

    @staticmethod
    def get_ceo_dashboard(year=None):
        """CEO/CHRO Dashboard - comprehensive organizational overview."""
        if year is None:
            year = date.today().year

        today = date.today()
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        month_start = date(today.year, today.month, 1)
        
        # Total & Active employees
        total_employees = Employee.objects.filter(is_active=True).count()
        active_employees = Employee.objects.filter(
            status__in=['ACTIVE', 'ON_LEAVE'], is_active=True
        ).count()
        
        # New hires
        new_hires_ytd = Employee.objects.filter(
            date_of_joining__gte=year_start,
            date_of_joining__lte=year_end,
        ).count()
        
        new_hires_month = Employee.objects.filter(
            date_of_joining__gte=month_start,
        ).count()
        
        # Attrition
        separated_ytd = Employee.objects.filter(
            status='SEPARATED',
            separation_date__gte=year_start,
            separation_date__lte=year_end,
        ).count()
        
        # Average headcount for attrition rate calculation
        starting_headcount = total_employees - new_hires_ytd + separated_ytd
        avg_headcount = (starting_headcount + total_employees) / 2
        attrition_rate = round((separated_ytd / avg_headcount * 100), 2) if avg_headcount > 0 else 0
        
        # Payroll summary
        current_month_payroll = Payroll.objects.filter(
            month=today.month, year=today.year, status='PAID'
        ).aggregate(
            total_gross=Sum('gross_salary'),
            total_net=Sum('net_salary'),
            total_deductions=Sum('total_deductions'),
            count=Count('id'),
        )
        
        # Monthly payroll cost trend (last 6 months)
        six_months_ago = today.month - 6
        six_months_ago_year = today.year
        if six_months_ago <= 0:
            six_months_ago += 12
            six_months_ago_year -= 1
        
        payroll_trend = []
        for i in range(6):
            m = (today.month - i - 1) % 12 + 1
            y = today.year - (1 if (today.month - i - 1) < 0 else 0)
            month_data = Payroll.objects.filter(
                month=m, year=y, status__in=['APPROVED', 'PAID']
            ).aggregate(total=Sum('net_salary'), count=Count('id'))
            payroll_trend.append({
                'month': m, 'year': y,
                'total': float(month_data['total'] or 0),
                'count': month_data['count'] or 0,
            })
        
        # Department headcount
        dept_headcount = list(
            Employee.objects.filter(is_active=True)
            .values('department__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Grade distribution
        grade_distribution = list(
            Employee.objects.filter(is_active=True)
            .values('grade')
            .annotate(count=Count('id'))
            .order_by('grade')
        )
        
        # Location distribution
        location_distribution = list(
            Employee.objects.filter(is_active=True)
            .values('work_location__name', 'work_location__city')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Employment type breakdown
        emp_type_distribution = list(
            Employee.objects.filter(is_active=True)
            .values('employment_type')
            .annotate(count=Count('id'))
        )
        
        # Gender diversity
        gender_distribution = list(
            Employee.objects.filter(is_active=True)
            .values('gender')
            .annotate(count=Count('id'))
        )
        
        # Open positions (recruitment)
        open_positions = JobApplication.objects.filter(
            stage__in=['Applied', 'Screening', 'L1_Interview', 'L2_Interview', 'HR_Round']
        ).count()
        
        # Upcoming compliance due dates
        upcoming_compliance = ComplianceCalendarEntry.objects.filter(
            status='PENDING',
            due_date__gte=today,
        ).count()
        
        overdue_compliance = ComplianceCalendarEntry.objects.filter(
            status__in=['PENDING', 'OVERDUE'],
            due_date__lt=today,
        ).count()
        
        return {
            'year': year,
            'total_employees': total_employees,
            'active_employees': active_employees,
            'new_hires_ytd': new_hires_ytd,
            'new_hires_month': new_hires_month,
            'separated_ytd': separated_ytd,
            'attrition_rate': attrition_rate,
            'avg_headcount': round(avg_headcount, 0),
            'monthly_payroll_cost': float(current_month_payroll['total_net'] or 0),
            'monthly_gross_payroll': float(current_month_payroll['total_gross'] or 0),
            'monthly_deductions': float(current_month_payroll['total_deductions'] or 0),
            'payroll_employee_count': current_month_payroll['count'] or 0,
            'avg_cost_per_employee': round(float(current_month_payroll['total_gross'] or 0) / max(current_month_payroll['count'] or 1, 1), 0),
            'payroll_trend': payroll_trend,
            'department_headcount': dept_headcount,
            'grade_distribution': grade_distribution,
            'location_distribution': location_distribution,
            'employment_type_distribution': emp_type_distribution,
            'gender_distribution': gender_distribution,
            'open_positions': open_positions,
            'upcoming_compliance': upcoming_compliance,
            'overdue_compliance': overdue_compliance,
        }

    @staticmethod
    def get_attrition_analysis(year=None):
        """Comprehensive attrition analysis."""
        if year is None:
            year = date.today().year

        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        separated = Employee.objects.filter(
            status='SEPARATED',
            separation_date__gte=year_start,
            separation_date__lte=year_end,
        )

        total_separations = separated.count()

        # Voluntary vs Involuntary
        voluntary = separated.filter(separation_reason='RESIGNED').count()
        involuntary = separated.filter(
            separation_reason__in=['TERMINATED', 'ABSCONDED', 'DECEASED', 'RETIRED']
        ).count()

        # By department
        by_department = list(
            separated.values('department__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # By reason
        by_reason = list(
            separated.values('separation_reason')
            .annotate(count=Count('id'))
        )

        # By tenure (years of service)
        from django.db.models import F, ExpressionWrapper, IntegerField
        tenure_data = []
        for emp in separated:
            if emp.date_of_joining and emp.separation_date:
                tenure = (emp.separation_date - emp.date_of_joining).days // 365
                tenure_data.append(tenure)
        
        tenure_buckets = {
            '0-1 Year': sum(1 for t in tenure_data if t < 1),
            '1-2 Years': sum(1 for t in tenure_data if 1 <= t < 2),
            '2-5 Years': sum(1 for t in tenure_data if 2 <= t < 5),
            '5-10 Years': sum(1 for t in tenure_data if 5 <= t < 10),
            '10+ Years': sum(1 for t in tenure_data if t >= 10),
        }

        # By grade
        by_grade = list(
            separated.values('grade')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Monthly trend
        monthly_trend = list(
            separated.annotate(month=TruncMonth('separation_date'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # Exit interview insights
        exit_reasons = list(
            ExitInterviewResponse.objects.filter(
                interview__resignation__employee__in=separated,
                question_code='REASON_FOR_LEAVING',
            ).values('choice_response')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return {
            'year': year,
            'total_separations': total_separations,
            'voluntary': voluntary,
            'involuntary': involuntary,
            'by_department': by_department,
            'by_reason': by_reason,
            'by_tenure': tenure_buckets,
            'by_grade': by_grade,
            'monthly_trend': [
                {'month': m['month'].strftime('%Y-%m') if m['month'] else '', 'count': m['count']}
                for m in monthly_trend
            ],
            'exit_reasons': exit_reasons,
        }

    @staticmethod
    def get_headcount_report(date_filter=None):
        """Headcount analysis by various dimensions."""
        if date_filter is None:
            date_filter = date.today()

        active = Employee.objects.filter(is_active=True)

        # Total
        total = active.count()

        # By department
        by_department = list(
            active.values('department__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # By location
        by_location = list(
            active.values('work_location__name', 'work_location__city')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # By designation
        by_designation = list(
            active.values('designation__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # By grade/band
        by_grade = list(
            active.values('grade')
            .annotate(count=Count('id'))
            .order_by('grade')
        )

        # Monthly joining trend (last 12 months)
        twelve_months_ago = date_filter - timedelta(days=365)
        joining_trend = list(
            Employee.objects.filter(
                date_of_joining__gte=twelve_months_ago,
            )
            .annotate(month=TruncMonth('date_of_joining'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # Headcount by manager
        by_manager = list(
            active.values('reporting_manager__first_name', 'reporting_manager__last_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )

        return {
            'total': total,
            'by_department': by_department,
            'by_location': by_location,
            'by_designation': by_designation,
            'by_grade': by_grade,
            'joining_trend': [
                {'month': m['month'].strftime('%Y-%m') if m['month'] else '', 'count': m['count']}
                for m in joining_trend
            ],
            'by_manager': by_manager,
        }

    @staticmethod
    def get_recruitment_analytics(year=None):
        """Recruitment funnel analytics and KPIs."""
        if year is None:
            year = date.today().year

        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        # Total applications
        applications = JobApplication.objects.filter(
            applied_on__date__gte=year_start,
            applied_on__date__lte=year_end,
        )
        total_apps = applications.count()

        # Pipeline breakdown
        pipeline = list(
            applications.values('stage')
            .annotate(count=Count('id'))
            .order_by('stage')
        )

        # Candidates by source
        candidates = Candidate.objects.filter(
            created_at__date__gte=year_start,
            created_at__date__lte=year_end,
        )
        by_source = list(
            candidates.values('source')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Interviews scheduled
        interviews = InterviewSchedule.objects.filter(
            scheduled_date__date__gte=year_start,
            scheduled_date__date__lte=year_end,
        )
        total_interviews = interviews.count()
        completed_interviews = interviews.filter(status='COMPLETED').count()

        # Offers
        offers = OfferLetter.objects.filter(
            offer_date__gte=year_start,
            offer_date__lte=year_end,
        )
        total_offers = offers.count()
        accepted_offers = offers.filter(status='ACCEPTED').count()
        rejected_offers = offers.filter(status__in=['REJECTED', 'EXPIRED']).count()
        offer_acceptance_rate = round(
            (accepted_offers / total_offers * 100), 1
        ) if total_offers > 0 else 0

        # Time to fill (average days from application to offer)
        avg_days_to_fill = 0
        filled_positions = JobApplication.objects.filter(
            stage__in=['Accepted', 'Offered'],
            applied_on__date__gte=year_start,
        )
        if filled_positions.exists():
            total_days = 0
            count = 0
            for app in filled_positions:
                # Get the latest offer for this application
                offer = OfferLetter.objects.filter(
                    application=app,
                    status__in=['ACCEPTED', 'SENT']
                ).first()
                if offer and offer.offer_date:
                    days = (offer.offer_date - app.applied_on.date()).days
                    total_days += days
                    count += 1
            avg_days_to_fill = round(total_days / max(count, 1), 0)

        # Requisitions
        from hr.models import JobRequisition
        open_reqs = JobRequisition.objects.filter(status='Approved').count()
        filled_reqs = JobRequisition.objects.filter(status='Closed').count()

        return {
            'year': year,
            'total_applications': total_apps,
            'pipeline': pipeline,
            'candidates_by_source': by_source,
            'total_candidates': candidates.count(),
            'total_interviews': total_interviews,
            'completed_interviews': completed_interviews,
            'interview_completion_rate': round(
                (completed_interviews / max(total_interviews, 1) * 100), 1
            ),
            'total_offers': total_offers,
            'accepted_offers': accepted_offers,
            'rejected_offers': rejected_offers,
            'offer_acceptance_rate': offer_acceptance_rate,
            'avg_days_to_fill': avg_days_to_fill,
            'open_requisitions': open_reqs,
            'filled_requisitions': filled_reqs,
        }

    @staticmethod
    def get_attendance_report(month=None, year=None):
        """Attendance analysis for a given period."""
        today = date.today()
        if month is None:
            month = today.month
        if year is None:
            year = today.year

        attendance = Attendance.objects.filter(date__month=month, date__year=year)

        total_records = attendance.count()
        present = attendance.filter(status='PRESENT').count()
        absent = attendance.filter(status='ABSENT').count()
        half_day = attendance.filter(status='HALF_DAY').count()
        wfh = attendance.filter(status='WFH').count()
        late_marks = attendance.filter(is_late=True).count()

        # Late by department
        late_by_dept = list(
            attendance.filter(is_late=True)
            .values('employee__department__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Absenteeism rate
        absenteeism_rate = round(
            (absent / max(total_records, 1) * 100), 2
        )

        # Department-wise attendance
        dept_attendance = list(
            attendance.values('employee__department__name')
            .annotate(
                total=Count('id'),
                present_count=Count('id', filter=Q(status='PRESENT')),
                absent_count=Count('id', filter=Q(status='ABSENT')),
            )
            .order_by('-total')
        )

        return {
            'month': month,
            'year': year,
            'total_records': total_records,
            'present': present,
            'absent': absent,
            'half_day': half_day,
            'wfh': wfh,
            'late_marks': late_marks,
            'absenteeism_rate': absenteeism_rate,
            'attendance_rate': round((present / max(total_records, 1) * 100), 2),
            'late_by_department': late_by_dept,
            'department_attendance': dept_attendance,
        }

    @staticmethod
    def get_leave_report(month=None, year=None):
        """Leave utilization analysis."""
        today = date.today()
        if month is None:
            month = today.month
        if year is None:
            year = today.year

        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year, 12, 31)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        leave_applications = LeaveApplication.objects.filter(
            date_from__lte=month_end,
            date_to__gte=month_start,
            approval_status='APPROVED',
        )

        total_leaves = leave_applications.count()
        total_days = leave_applications.aggregate(total=Sum('number_of_days'))['total'] or 0

        # By leave type
        by_type = list(
            leave_applications.values('leave_type__name')
            .annotate(
                count=Count('id'),
                days=Sum('number_of_days'),
            )
            .order_by('-days')
        )

        # Top absentees by department
        by_department = list(
            leave_applications.values('employee__department__name')
            .annotate(
                count=Count('id'),
                days=Sum('number_of_days'),
                employees=Count('employee', distinct=True),
            )
            .order_by('-days')
        )

        # Leave balance utilization
        from hr.models import EmployeeLeaveBalance
        balance_utilization = list(
            EmployeeLeaveBalance.objects.filter(financial_year__contains=str(year))
            .values('leave_type__name')
            .annotate(
                total_balance=Sum('current_balance'),
                total_used=Sum('used_days'),
                total_accrued=Sum('accrued_days'),
            )
        )

        return {
            'month': month,
            'year': year,
            'total_applications': total_leaves,
            'total_days_taken': float(total_days),
            'avg_days_per_employee': round(float(total_days) / max(leave_applications.values('employee').distinct().count(), 1), 1),
            'by_leave_type': by_type,
            'by_department': by_department,
            'balance_utilization': balance_utilization,
        }

    @staticmethod
    def get_payroll_report(month=None, year=None):
        """Payroll cost analysis and trends."""
        today = date.today()
        if month is None:
            month = today.month
        if year is None:
            year = today.year

        # Current month payroll
        payroll = Payroll.objects.filter(month=month, year=year)
        total_gross = payroll.aggregate(total=Sum('gross_salary'))['total'] or 0
        total_net = payroll.aggregate(total=Sum('net_salary'))['total'] or 0
        total_deductions = payroll.aggregate(total=Sum('total_deductions'))['total'] or 0
        total_arrears = payroll.aggregate(total=Sum('arrears'))['total'] or 0
        employee_count = payroll.count()

        # Department cost breakdown
        dept_cost = list(
            payroll.values('employee__department__name')
            .annotate(
                gross=Sum('gross_salary'),
                net=Sum('net_salary'),
                deductions=Sum('total_deductions'),
                count=Count('id'),
            )
            .order_by('-gross')
        )

        # Monthly trend (last 12 months)
        trend = []
        for i in range(12):
            m = month - i
            y = year
            if m <= 0:
                m += 12
                y -= 1
            p = Payroll.objects.filter(month=m, year=y).aggregate(
                gross=Sum('gross_salary'),
                net=Sum('net_salary'),
                deductions=Sum('total_deductions'),
                count=Count('id'),
            )
            trend.append({
                'month': m, 'year': y,
                'gross': float(p['gross'] or 0),
                'net': float(p['net'] or 0),
                'deductions': float(p['deductions'] or 0),
                'employees': p['count'] or 0,
            })
        trend.reverse()

        # Salary revisions this year
        revisions = SalaryRevision.objects.filter(
            effective_year=year,
            status='APPROVED',
        )
        avg_increment = revisions.aggregate(avg=Avg('percentage_increase'))['avg'] or 0
        total_revisions = revisions.count()

        # Loans outstanding
        loans_outstanding = EmployeeLoan.objects.filter(
            status__in=['APPROVED', 'ACTIVE']
        ).aggregate(
            total=Sum('outstanding_amount'),
            count=Count('id'),
        )

        # Reimbursements pending
        reimbursements_pending = EmployeeReimbursement.objects.filter(
            status='PENDING'
        ).aggregate(
            total=Sum('amount'),
            count=Count('id'),
        )

        return {
            'month': month,
            'year': year,
            'employee_count': employee_count,
            'total_gross': float(total_gross),
            'total_net': float(total_net),
            'total_deductions': float(total_deductions),
            'total_arrears': float(total_arrears),
            'deduction_pct': round(float(total_deductions) / max(float(total_gross), 1) * 100, 2),
            'avg_gross_per_employee': round(float(total_gross) / max(employee_count, 1), 0),
            'avg_net_per_employee': round(float(total_net) / max(employee_count, 1), 0),
            'department_cost': dept_cost,
            'monthly_trend': trend,
            'total_salary_revisions': total_revisions,
            'avg_increment_pct': round(float(avg_increment), 2),
            'outstanding_loans': float(loans_outstanding['total'] or 0),
            'outstanding_loan_count': loans_outstanding['count'] or 0,
            'pending_reimbursements': float(reimbursements_pending['total'] or 0),
            'pending_reimbursement_count': reimbursements_pending['count'] or 0,
        }

    @staticmethod
    def get_compliance_calendar_report(year=None):
        """Compliance calendar status and risk assessment."""
        if year is None:
            year = date.today().year

        today = date.today()
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        entries = ComplianceCalendarEntry.objects.filter(
            due_date__gte=year_start,
            due_date__lte=year_end,
        )

        total = entries.count()
        completed = entries.filter(status='COMPLETED').count()
        pending = entries.filter(status='PENDING').count()
        overdue = entries.filter(status='OVERDUE').count()

        # Upcoming (next 30 days)
        upcoming = list(
            entries.filter(
                status__in=['PENDING', 'OVERDUE'],
                due_date__gte=today,
                due_date__lte=today + timedelta(days=30),
            ).values('compliance_type', 'title', 'due_date', 'reference_number')
            .order_by('due_date')
        )

        # By compliance type
        by_type = list(
            entries.values('compliance_type')
            .annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='COMPLETED')),
                pending=Count('id', filter=Q(status__in=['PENDING', 'OVERDUE'])),
            )
            .order_by('compliance_type')
        )

        # Penalty risk (overdue items past due date by more than 7 days)
        penalty_risk = entries.filter(
            status__in=['PENDING', 'OVERDUE'],
            due_date__lt=today - timedelta(days=7),
        ).count()

        compliance_rate = round((completed / max(total, 1) * 100), 1)

        return {
            'year': year,
            'total_entries': total,
            'completed': completed,
            'pending': pending,
            'overdue': overdue,
            'compliance_rate': compliance_rate,
            'penalty_risk_items': penalty_risk,
            'upcoming_30_days': list(upcoming),
            'by_compliance_type': by_type,
        }

    @staticmethod
    def get_training_report(year=None):
        """Training & development analytics."""
        if year is None:
            year = date.today().year

        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        programs = TrainingProgram.objects.filter(
            start_date__gte=year_start,
            start_date__lte=year_end,
        )
        total_programs = programs.count()
        completed_programs = programs.filter(end_date__lt=date.today()).count()

        nominations = TrainingNomination.objects.filter(
            program__in=programs,
        )

        total_nominations = nominations.count()
        completed_nominations = nominations.filter(status='Completed').count()
        completion_rate = round(
            (completed_nominations / max(total_nominations, 1) * 100), 1
        )

        # Avg scores
        avg_score = nominations.filter(
            completion_score__isnull=False
        ).aggregate(avg=Avg('completion_score'))['avg'] or 0

        # By program type
        by_type = list(
            programs.values('training_type')
            .annotate(count=Count('id'))
        )

        return {
            'year': year,
            'total_programs': total_programs,
            'completed_programs': completed_programs,
            'total_nominations': total_nominations,
            'completed_nominations': completed_nominations,
            'completion_rate': completion_rate,
            'avg_score': round(float(avg_score), 1),
            'by_type': by_type,
        }

    @staticmethod
    def get_payroll_variance_report(month, year, prev_month=None, prev_year=None):
        """Month-over-month payroll variance analysis."""
        today = date.today()
        if prev_month is None:
            prev_month = month - 1 if month > 1 else 12
        if prev_year is None:
            prev_year = year if month > 1 else year - 1

        current = Payroll.objects.filter(month=month, year=year)
        previous = Payroll.objects.filter(month=prev_month, year=prev_year)

        def get_stats(qs, label):
            agg = qs.aggregate(
                gross=Sum('gross_salary'),
                net=Sum('net_salary'),
                ded=Sum('total_deductions'),
                count=Count('id'),
            )
            return {
                'label': label,
                'gross': float(agg['gross'] or 0),
                'net': float(agg['net'] or 0),
                'deductions': float(agg['ded'] or 0),
                'employee_count': agg['count'] or 0,
            }

        current_stats = get_stats(current, f'{month}/{year}')
        prev_stats = get_stats(previous, f'{prev_month}/{prev_year}')

        def calc_variance(curr, prev):
            if prev == 0:
                return 100 if curr > 0 else 0
            return round((curr - prev) / prev * 100, 2)

        return {
            'current': current_stats,
            'previous': prev_stats,
            'variance': {
                'gross_pct': calc_variance(current_stats['gross'], prev_stats['gross']),
                'net_pct': calc_variance(current_stats['net'], prev_stats['net']),
                'deductions_pct': calc_variance(current_stats['deductions'], prev_stats['deductions']),
                'employee_count_pct': calc_variance(current_stats['employee_count'], prev_stats['employee_count']),
            },
        }
