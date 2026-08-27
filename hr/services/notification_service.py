"""
HR Email Notification Service — Automated Email Notifications

Handles automated email notifications for HR workflows:
1. Leave application submitted → Notify manager
2. Leave approved/rejected → Notify employee
3. Payroll processed/approved → Notify employee (payslip link)
4. Ticket created/resolved → Notify relevant parties
5. Birthday/work anniversary wishes
6. Pending compliance reminders
"""

import logging
from datetime import date
from typing import Optional, List
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


class HREmailNotification:
    """
    Base class for HR email notifications with rich HTML templates.
    """

    FROM_EMAIL = settings.DEFAULT_FROM_EMAIL or 'noreply@bytehive.com'
    COMPANY_NAME = "ByteHive Technologies"

    @classmethod
    def _send_html_email(cls, subject: str, html_content: str, to_emails: List[str],
                         bcc_emails: List[str] = None, reply_to: str = None) -> bool:
        """
        Send HTML email with plain text fallback.

        Args:
            subject: Email subject line
            html_content: HTML body content
            to_emails: List of recipient email addresses
            bcc_emails: Optional BCC recipients
            reply_to: Optional reply-to address

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not to_emails:
            logger.warning("No recipients provided for email: %s", subject)
            return False

        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=cls.FROM_EMAIL,
            to=to_emails,
            bcc=bcc_emails or [],
            reply_to=[reply_to] if reply_to else [],
        )
        msg.attach_alternative(html_content, "text/html")

        try:
            msg.send(fail_silently=False)
            logger.info(f"Email sent: {subject} to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email '{subject}': {str(e)}")
            # In development, log the email content instead
            if settings.DEBUG:
                logger.debug(f"Email content (would send in production):\nSubject: {subject}\nTo: {to_emails}\n\n{text_content[:500]}...")
            return False

    @classmethod
    def _build_base_template(cls, content_html: str, footer_text: str = None) -> str:
        """
        Build standard HTML email template with ByteHive branding.

        Args:
            content_html: Main email body content (HTML)
            footer_text: Optional footer message

        Returns:
            str: Complete HTML email
        """
        year = date.today().year
        portal_link = "https://bytehive.com"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9; }}
                .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #1a237e 0%, #283593 100%); padding: 30px; text-align: center; }}
                .header h1 {{ color: #ffffff; margin: 0; font-size: 24px; }}
                .header p {{ color: #c5cae9; margin: 5px 0 0; font-size: 14px; }}
                .content {{ padding: 30px; color: #333; line-height: 1.6; }}
                .content h2 {{ color: #1a237e; font-size: 20px; margin-top: 0; }}
                .button {{ display: inline-block; padding: 12px 24px; margin: 20px 0; 
                          background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);
                          color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: 600; }}
                .button:hover {{ background: linear-gradient(135deg, #283593 0%, #5c6bc0 100%); }}
                .details {{ background: #f5f5f5; border-radius: 8px; padding: 20px; margin: 15px 0; }}
                .details table {{ width: 100%; border-collapse: collapse; }}
                .details td {{ padding: 8px 12px; border-bottom: 1px solid #e0e0e0; font-size: 14px; }}
                .details td:first-child {{ color: #666; font-weight: 600; width: 40%; }}
                .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
                .status-approved {{ background: #e8f5e9; color: #2e7d32; }}
                .status-rejected {{ background: #ffebee; color: #c62828; }}
                .status-pending {{ background: #fff3e0; color: #ef6c00; }}
                .footer {{ background: #f8f9fa; padding: 20px 30px; text-align: center; font-size: 12px; color: #999; }}
                .footer a {{ color: #3949ab; text-decoration: none; }}
                @media only screen and (max-width: 480px) {{ .container {{ margin: 10px; }} .content {{ padding: 20px; }} }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{cls.COMPANY_NAME}</h1>
                    <p>Human Resource Management System</p>
                </div>
                <div class="content">
                    {content_html}
                </div>
                <div class="footer">
                    <p><b>{cls.COMPANY_NAME}</b> — HRMS Portal</p>
                    <p>This is an automated notification. Please do not reply directly to this email.</p>
                    <p>© {year} {cls.COMPANY_NAME}. All rights reserved.</p>
                    <p><a href="{portal_link}">Visit Portal</a></p>
                </div>
            </div>
        </body>
        </html>
        """


class LeaveNotification(HREmailNotification):
    """
    Email notifications for leave management workflows.
    """

    @classmethod
    def notify_manager_new_application(cls, leave_app) -> bool:
        """
        Notify manager when employee applies for leave.

        Args:
            leave_app: LeaveApplication instance

        Returns:
            bool: Success status
        """
        employee = leave_app.employee
        manager = employee.reporting_manager
        if not manager or not manager.user or not manager.user.email:
            logger.warning(f"No manager email found for {employee.employee_id}")
            return False

        subject = f"Leave Request: {employee.get_full_name()} - {leave_app.leave_type.name} ({leave_app.date_from} to {leave_app.date_to})"

        content = f"""
        <h2>New Leave Application</h2>
        <p>Hi <b>{manager.get_full_name()}</b>,</p>
        <p><b>{employee.get_full_name()}</b> (ID: {employee.employee_id}) has submitted a leave request for your approval.</p>
        <div class="details">
            <table>
                <tr><td>Leave Type</td><td>{leave_app.leave_type.name if leave_app.leave_type else 'N/A'}</td></tr>
                <tr><td>From</td><td>{leave_app.date_from}</td></tr>
                <tr><td>To</td><td>{leave_app.date_to}</td></tr>
                <tr><td>Days</td><td>{leave_app.number_of_days}</td></tr>
                <tr><td>Reason</td><td>{leave_app.reason}</td></tr>
                <tr><td>Status</td><td><span class="status-badge status-pending">Pending Your Approval</span></td></tr>
            </table>
        </div>
        <p>Please log in to the HR portal to approve or decline this request.</p>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, [manager.user.email])

    @classmethod
    def notify_employee_status_change(cls, leave_app) -> bool:
        """
        Notify employee when their leave is approved/rejected/cancelled.

        Args:
            leave_app: LeaveApplication instance

        Returns:
            bool: Success status
        """
        employee = leave_app.employee
        if not employee.user or not employee.user.email:
            logger.warning(f"No user email for {employee.employee_id}")
            return False

        status = leave_app.approval_status
        status_label = status.lower()
        status_color = "status-approved" if status == "APPROVED" else "status-rejected" if status == "REJECTED" else "status-pending"

        subject = f"Leave {status_label.title()}: {leave_app.leave_type.name} ({leave_app.date_from} to {leave_app.date_to})"

        content = f"""
        <h2>Leave Application {status_label.title()}</h2>
        <p>Hi <b>{employee.get_full_name()}</b>,</p>
        <p>Your leave application has been <b>{status_label}</b>.</p>
        <div class="details">
            <table>
                <tr><td>Leave Type</td><td>{leave_app.leave_type.name if leave_app.leave_type else 'N/A'}</td></tr>
                <tr><td>From</td><td>{leave_app.date_from}</td></tr>
                <tr><td>To</td><td>{leave_app.date_to}</td></tr>
                <tr><td>Days</td><td>{leave_app.number_of_days}</td></tr>
                <tr><td>Status</td><td><span class="status-badge {status_color}">{status}</span></td></tr>
        """

        if leave_app.approval_comment:
            content += f'<tr><td>Manager Comment</td><td>{leave_app.approval_comment}</td></tr>'

        content += """
            </table>
        </div>
        <p>Please log in to the HR portal to view the details.</p>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, [employee.user.email])


class PayrollNotification(HREmailNotification):
    """
    Email notifications for payroll processing.
    """

    @classmethod
    def notify_payroll_processed(cls, payroll) -> bool:
        """
        Notify employee when payroll is processed and payslip is available.

        Args:
            payroll: Payroll instance

        Returns:
            bool: Success status
        """
        employee = payroll.employee
        if not employee.user or not employee.user.email:
            return False

        subject = f"Payslip Available: {payroll.payroll_period}"

        content = f"""
        <h2>Salary Credited - {payroll.payroll_period}</h2>
        <p>Hi <b>{employee.get_full_name()}</b>,</p>
        <p>Your salary for the period <b>{payroll.payroll_period}</b> has been processed.</p>
        <div class="details">
            <table>
                <tr><td>Gross Salary</td><td>₹ {payroll.gross_salary:,.2f}</td></tr>
                <tr><td>Total Deductions</td><td>₹ {payroll.total_deductions:,.2f}</td></tr>
                <tr><td><b>Net Salary</b></td><td><b>₹ {payroll.final_salary:,.2f}</b></td></tr>
                <tr><td>Status</td><td><span class="status-badge status-approved">{payroll.status}</span></td></tr>
            </table>
        </div>
        <p>You can download your payslip from the HRMS portal.</p>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, [employee.user.email])

    @classmethod
    def notify_payroll_approved(cls, payroll) -> bool:
        """
        Notify when payroll has been approved (for HR/admin awareness).

        Args:
            payroll: Payroll instance
        """
        employee = payroll.employee
        if not employee.user or not employee.user.email:
            return False

        subject = f"Payroll Approved: {employee.get_full_name()} - {payroll.payroll_period}"

        content = f"""
        <h2>Payroll Approved</h2>
        <p>Hi <b>{employee.get_full_name()}</b>,</p>
        <p>Your payroll for <b>{payroll.payroll_period}</b> has been approved.</p>
        <div class="details">
            <table>
                <tr><td>Net Salary</td><td><b>₹ {payroll.final_salary:,.2f}</b></td></tr>
                <tr><td>Status</td><td><span class="status-badge status-approved">APPROVED</span></td></tr>
            </table>
        </div>
        <p>Please check your bank account for salary credit.</p>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, [employee.user.email])


class TicketNotification(HREmailNotification):
    """
    Email notifications for HR helpdesk tickets.
    """

    @classmethod
    def notify_ticket_created(cls, ticket) -> bool:
        """
        Notify HR team when a ticket is created.
        """
        # Send to HR admins
        hr_admins = User.objects.filter(role__in=['Superadmin', 'Admin']).values_list('email', flat=True)
        if not hr_admins:
            return False

        employee = ticket.employee
        subject = f"New HR Ticket: {ticket.subject}"

        content = f"""
        <h2>New HR Ticket</h2>
        <p>A new HR ticket has been raised.</p>
        <div class="details">
            <table>
                <tr><td>Employee</td><td>{employee.get_full_name()} ({employee.employee_id})</td></tr>
                <tr><td>Type</td><td>{ticket.get_ticket_type_display()}</td></tr>
                <tr><td>Subject</td><td>{ticket.subject}</td></tr>
                <tr><td>Priority</td><td><b>{ticket.priority}</b></td></tr>
            </table>
        </div>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, list(hr_admins))

    @classmethod
    def notify_ticket_resolved(cls, ticket) -> bool:
        """
        Notify ticket creator when ticket is resolved.
        """
        employee = ticket.employee
        if not employee.user or not employee.user.email:
            return False

        subject = f"Ticket Resolved: {ticket.subject}"

        content = f"""
        <h2>Ticket Resolved</h2>
        <p>Hi <b>{employee.get_full_name()}</b>,</p>
        <p>Your HR ticket has been resolved.</p>
        <div class="details">
            <table>
                <tr><td>Subject</td><td>{ticket.subject}</td></tr>
                <tr><td>Resolution</td><td>{ticket.resolution_notes or 'N/A'}</td></tr>
                <tr><td>Status</td><td><span class="status-badge status-approved">RESOLVED</span></td></tr>
            </table>
        </div>
        <p>Please log in to the HR portal to view the resolution details.</p>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, [employee.user.email])


class ComplianceNotification(HREmailNotification):
    """
    Email notifications for compliance deadlines.
    """

    @classmethod
    def notify_upcoming_compliance(cls, events: list) -> bool:
        """
        Send compliance deadline reminders to HR team.

        Args:
            events: List of dicts with 'type', 'title', 'due_date', 'days_remaining'
        """
        hr_emails = User.objects.filter(role__in=['Superadmin', 'Admin']).values_list('email', flat=True)
        if not hr_emails:
            return False

        if not events:
            return False

        subject = f"⚠️ {len(events)} Compliance Deadline{'s' if len(events) > 1 else ''} Approaching"

        events_html = ""
        for event in events:
            urgency = "🔴" if event['days_remaining'] <= 3 else "🟡" if event['days_remaining'] <= 7 else "🟢"
            events_html += f"""
            <tr>
                <td>{urgency}</td>
                <td>{event['type']}</td>
                <td>{event['title']}</td>
                <td>{event['due_date']}</td>
                <td><b>{event['days_remaining']} day(s)</b></td>
            </tr>
            """

        content = f"""
        <h2>⚠️ Compliance Calendar Reminder</h2>
        <p>The following compliance deadlines are approaching:</p>
        <div class="details">
            <table>
                <tr style="background:#e3f2fd;font-weight:600;">
                    <td></td><td>Type</td><td>Title</td><td>Due Date</td><td>Due In</td>
                </tr>
                {events_html}
            </table>
        </div>
        <p>Please ensure all filings and payments are completed on time to avoid penalties.</p>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, list(hr_emails))


class GreetingNotification(HREmailNotification):
    """
    Automated greeting emails for birthdays and work anniversaries.
    """

    @classmethod
    def send_birthday_wish(cls, employee) -> bool:
        """
        Send birthday greeting to employee.
        """
        if not employee.user or not employee.user.email:
            return False

        subject = f"🎂 Happy Birthday, {employee.first_name}!"

        content = f"""
        <h2>🎂 Happy Birthday!</h2>
        <p>Dear <b>{employee.get_full_name()}</b>,</p>
        <p>On behalf of everyone at <b>{cls.COMPANY_NAME}</b>, we wish you a very happy and wonderful birthday!</p>
        <p>May your day be filled with joy, laughter, and amazing moments. We appreciate your contributions to our team and wish you continued success.</p>
        <br/>
        <p style="text-align:center;font-size:24px;">🎉🎂🎈</p>
        <br/>
        <p>Warm regards,<br/><b>HR Team, {cls.COMPANY_NAME}</b></p>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, [employee.user.email],
                                    bcc_emails=[cls.FROM_EMAIL])

    @classmethod
    def send_work_anniversary(cls, employee, years: int) -> bool:
        """
        Send work anniversary greeting.
        """
        if not employee.user or not employee.user.email:
            return False

        subject = f"🎉 {years} Year Anniversary — Thank You, {employee.first_name}!"

        content = f"""
        <h2>🎉 Work Anniversary</h2>
        <p>Dear <b>{employee.get_full_name()}</b>,</p>
        <p>Congratulations on completing <b>{years} incredible year{'s' if years > 1 else ''}</b> with <b>{cls.COMPANY_NAME}</b>!</p>
        <p>Your dedication, hard work, and valuable contributions have played a key role in our growth. We are grateful to have you as part of our team.</p>
        <p>Here's to many more years of success together!</p>
        <br/>
        <p style="text-align:center;font-size:24px;">🏆🎉👏</p>
        <br/>
        <p>With appreciation,<br/><b>HR Team, {cls.COMPANY_NAME}</b></p>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, [employee.user.email],
                                    bcc_emails=[cls.FROM_EMAIL])


class OnboardingNotification(HREmailNotification):
    """
    Email notifications for onboarding workflows.
    """

    @classmethod
    def send_welcome_email(cls, employee) -> bool:
        """
        Send welcome email to new employee.
        """
        if not employee.user or not employee.user.email:
            return False

        subject = f"🎉 Welcome to {cls.COMPANY_NAME}, {employee.first_name}!"

        content = f"""
        <h2>Welcome Aboard!</h2>
        <p>Dear <b>{employee.get_full_name()}</b>,</p>
        <p>Welcome to <b>{cls.COMPANY_NAME}</b>! We are thrilled to have you join our team.</p>
        <p>Here are a few things to help you get started:</p>
        <div class="details">
            <table>
                <tr><td>Employee ID</td><td><b>{employee.employee_id}</b></td></tr>
                <tr><td>Department</td><td>{employee.department.name if employee.department else 'N/A'}</td></tr>
                <tr><td>Designation</td><td>{employee.designation.name if employee.designation else 'N/A'}</td></tr>
                <tr><td>Date of Joining</td><td>{employee.date_of_joining}</td></tr>
                <tr><td>Work Location</td><td>{employee.work_location.name if employee.work_location else 'N/A'}</td></tr>
            </table>
        </div>
        <p><b>Next Steps:</b></p>
        <ul>
            <li>Complete your profile in the HRMS portal</li>
            <li>Submit required documents (Aadhaar, PAN, Bank Details)</li>
            <li>Review company policies</li>
            <li>Meet your team members</li>
        </ul>
        <p>Your onboarding buddy will reach out to you shortly. If you have any questions, feel free to contact HR.</p>
        <br/>
        <p>Best wishes,<br/><b>HR Team, {cls.COMPANY_NAME}</b></p>
        """

        html = cls._build_base_template(content)
        return cls._send_html_email(subject, html, [employee.user.email])


class NotificationDispatcher:
    """
    Central dispatcher for HR notifications.
    Automatically decides what notifications to send based on actions.
    """

    @classmethod
    def on_leave_applied(cls, leave_app):
        """Send notifications when leave is applied."""
        LeaveNotification.notify_manager_new_application(leave_app)

    @classmethod
    def on_leave_status_change(cls, leave_app):
        """Send notifications when leave status changes."""
        LeaveNotification.notify_employee_status_change(leave_app)

    @classmethod
    def on_payroll_processed(cls, payroll):
        """Send notifications when payroll is processed."""
        PayrollNotification.notify_payroll_processed(payroll)

    @classmethod
    def on_payroll_approved(cls, payroll):
        """Send notifications when payroll is approved."""
        PayrollNotification.notify_payroll_approved(payroll)

    @classmethod
    def on_ticket_created(cls, ticket):
        """Send notifications when a ticket is created."""
        TicketNotification.notify_ticket_created(ticket)

    @classmethod
    def on_ticket_resolved(cls, ticket):
        """Send notifications when a ticket is resolved."""
        TicketNotification.notify_ticket_resolved(ticket)

    @classmethod
    def send_daily_greetings(cls):
        """
        Check for birthdays and work anniversaries today and send greetings.
        Should be called daily via cron/management command.
        """
        from hr.models import Employee
        today = date.today()

        # Birthdays today
        birthdays = Employee.objects.filter(
            date_of_birth__day=today.day,
            date_of_birth__month=today.month,
            is_active=True
        )
        for emp in birthdays:
            GreetingNotification.send_birthday_wish(emp)

        # Work anniversaries today
        anniversaries = Employee.objects.filter(
            date_of_joining__day=today.day,
            date_of_joining__month=today.month,
            is_active=True
        )
        for emp in anniversaries:
            years = today.year - emp.date_of_joining.year
            if years > 0:
                GreetingNotification.send_work_anniversary(emp, years)

    @classmethod
    def send_compliance_reminders(cls):
        """
        Check for upcoming compliance deadlines and send reminders.
        Should be called daily via cron/management command.
        """
        from hr.services.compliance_service import ComplianceCalendarService
        service = ComplianceCalendarService()
        upcoming = service.get_upcoming_alerts(days=7)
        if upcoming:
            ComplianceNotification.notify_upcoming_compliance(upcoming)

        overdue = service.get_overdue()
        if overdue:
            # Combine upcoming and overdue
            all_events = [{
                'type': e['type'],
                'title': e['title'],
                'due_date': e['due_date'],
                'days_remaining': -e['days_overdue'],
            } for e in overdue]
            ComplianceNotification.notify_upcoming_compliance(all_events)
