"""
Management command to send daily HR automated notifications.

Usage:
    python manage.py send_hr_notifications              # Send all daily notifications
    python manage.py send_hr_notifications --greetings   # Send only birthday/anniversary wishes
    python manage.py send_hr_notifications --compliance  # Send only compliance reminders
    python manage.py send_hr_notifications --dry-run     # Log what would be sent without actually sending

Recommended to set as a cron job running daily at 9 AM:
    0 9 * * * cd /app && python manage.py send_hr_notifications
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date


class Command(BaseCommand):
    help = 'Send daily HR automated notifications (birthday wishes, work anniversaries, compliance reminders)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--greetings',
            action='store_true',
            help='Send only birthday and work anniversary greetings',
        )
        parser.add_argument(
            '--compliance',
            action='store_true',
            help='Send only compliance deadline reminders',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate sending without actually sending emails',
        )

    def handle(self, *args, **options):
        send_greetings = options.get('greetings', False)
        send_compliance = options.get('compliance', False)
        dry_run = options.get('dry_run', False)

        # If no specific type is set, send all
        send_all = not send_greetings and not send_compliance

        self.stdout.write(self.style.NOTICE(
            f"{'🔍 DRY RUN: ' if dry_run else ''}🚀 Starting HR notification dispatch for {date.today()}..."
        ))

        self._dispatch_notifications(
            send_greetings=(send_all or send_greetings),
            send_compliance=(send_all or send_compliance),
            dry_run=dry_run,
        )

        self.stdout.write(self.style.SUCCESS('✅ HR notifications dispatched successfully'))

    def _dispatch_notifications(self, send_greetings=False, send_compliance=False, dry_run=False):
        """Dispatch notifications based on flags."""

        if send_greetings:
            self._send_greetings(dry_run)

        if send_compliance:
            self._send_compliance_reminders(dry_run)

    def _send_greetings(self, dry_run=False):
        """Send birthday and work anniversary greetings."""
        from hr.models import Employee

        today = date.today()
        self.stdout.write(f"   📅 Checking greetings for {today}...")

        # Birthdays today
        birthdays = Employee.objects.filter(
            date_of_birth__day=today.day,
            date_of_birth__month=today.month,
            is_active=True,
        )
        birthday_count = birthdays.count()
        if birthday_count > 0:
            self.stdout.write(f"   🎂 Found {birthday_count} birthday(s) today:")
            for emp in birthdays:
                self.stdout.write(f"      - {emp.get_full_name()} ({emp.employee_id})")
                if not dry_run:
                    try:
                        from hr.services.notification_service import GreetingNotification
                        GreetingNotification.send_birthday_wish(emp)
                        self.stdout.write(self.style.SUCCESS(f"         ✅ Birthday wish sent"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"         ❌ Failed: {e}"))
        else:
            self.stdout.write("      No birthdays today")

        # Work anniversaries today
        anniversaries = Employee.objects.filter(
            date_of_joining__day=today.day,
            date_of_joining__month=today.month,
            is_active=True,
        )
        anniversary_count = anniversaries.count()
        if anniversary_count > 0:
            self.stdout.write(f"   🎉 Found {anniversary_count} work anniversary(ies) today:")
            for emp in anniversaries:
                years = today.year - emp.date_of_joining.year
                if years > 0:
                    self.stdout.write(f"      - {emp.get_full_name()} ({years} year{'s' if years > 1 else ''})")
                    if not dry_run:
                        try:
                            from hr.services.notification_service import GreetingNotification
                            GreetingNotification.send_work_anniversary(emp, years)
                            self.stdout.write(self.style.SUCCESS(f"         ✅ Anniversary wish sent"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"         ❌ Failed: {e}"))
        else:
            self.stdout.write("      No work anniversaries today")

    def _send_compliance_reminders(self, dry_run=False):
        """Send compliance deadline reminders to HR team."""
        self.stdout.write("   ⚖️ Checking compliance deadlines...")

        try:
            from hr.services.compliance_service import ComplianceCalendarService
            service = ComplianceCalendarService()

            upcoming = service.get_upcoming_alerts(days=7)
            overdue = service.get_overdue()

            if upcoming:
                self.stdout.write(f"   📋 Found {len(upcoming)} upcoming compliance deadline(s):")
                for event in upcoming:
                    self.stdout.write(
                        f"      - {event['title']} (due {event['due_date']}, {event['days_remaining']} day(s) left)"
                    )

            if overdue:
                self.stdout.write(f"   🔴 Found {len(overdue)} overdue compliance item(s):")
                for event in overdue:
                    self.stdout.write(
                        f"      - {event['title']} (overdue by {event['days_overdue']} day(s))"
                    )

            if not dry_run and (upcoming or overdue):
                try:
                    from hr.services.notification_service import ComplianceNotification
                    all_events = []
                    for e in upcoming:
                        all_events.append({
                            'type': e['type'],
                            'title': e['title'],
                            'due_date': e['due_date'],
                            'days_remaining': e['days_remaining'],
                        })
                    for e in overdue:
                        all_events.append({
                            'type': e['type'],
                            'title': e['title'],
                            'due_date': e['due_date'],
                            'days_remaining': -e['days_overdue'],
                        })
                    ComplianceNotification.notify_upcoming_compliance(all_events)
                    self.stdout.write(self.style.SUCCESS("         ✅ Compliance reminders sent"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"         ❌ Failed: {e}"))

            if not upcoming and not overdue:
                self.stdout.write("      No compliance deadlines in next 7 days")

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   ⚠️ Could not check compliance: {e}"))
