"""
unlock_user.py — Management command to reset rate limits for a user.

Resets the rate limit by deleting failed LoginAttempt records for a given
email address or for all users at once.

Usage:
    python manage.py unlock_user admin@example.com
    python manage.py unlock_user admin@example.com --all-statuses
    python manage.py unlock_user --all
    python manage.py unlock_user --all --dry-run
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from authentication.models import LoginAttempt


class Command(BaseCommand):
    help = "Reset rate limits by deleting failed login attempts for a user."

    def add_arguments(self, parser):
        parser.add_argument(
            "email",
            nargs="?",
            default=None,
            help="Email address of the user to unlock (omit when using --all).",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Reset rate limits for ALL users (deletes all failed attempts).",
        )
        parser.add_argument(
            "--all-statuses",
            action="store_true",
            help="Also delete successful and blocked login attempts, not just failed ones.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview how many records would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        email = options["email"]
        reset_all = options["all"]
        all_statuses = options["all_statuses"]
        dry_run = options["dry_run"]

        prefix = "[DRY RUN] " if dry_run else ""

        # ── Validate arguments ────────────────────────────────────────────────
        if not email and not reset_all:
            raise CommandError(
                "You must provide an email address or use --all to unlock all users.\n"
                "  Examples:\n"
                "    python manage.py unlock_user admin@example.com\n"
                "    python manage.py unlock_user --all"
            )
        if email and reset_all:
            raise CommandError(
                "Cannot provide both an email and --all. Use one or the other."
            )

        # ── Build query ───────────────────────────────────────────────────────
        qs = LoginAttempt.objects.all()

        if email:
            qs = qs.filter(email=email)
            label = f"user '{email}'"
        else:
            label = "ALL users"

        # By default, only delete failed attempts (rate-limiting records)
        # Successful logins are kept for audit unless --all-statuses is passed.
        if all_statuses:
            status_label = "all statuses (failed, success, blocked)"
        else:
            qs = qs.filter(status="failed")
            status_label = "failed attempts only"

        count = qs.count()

        # ── Report ────────────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{prefix}Unlock rate limit for {label}\n" + "─" * 50
        ))
        self.stdout.write(f"  Found {count} LoginAttempt record(s) ({status_label}).")

        if count == 0:
            self.stdout.write(self.style.SUCCESS(
                "  No records to delete. Rate limit is already clear.\n"
            ))
            return

        # ── Dry-run ───────────────────────────────────────────────────────────
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"  Would delete {count} record(s). Re-run without --dry-run to execute.\n"
            ))
            return

        # ── Execute ───────────────────────────────────────────────────────────
        qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f"  ✅ Deleted {count} LoginAttempt record(s) for {label}.\n"
        ))

        if email:
            self.stdout.write(self.style.SUCCESS(
                f"  User '{email}' can now log in again immediately.\n"
            ))
