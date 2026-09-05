from django.db import models
from django.conf import settings
from core.models import Main
from contacts.models import Contact
from crm.models import CRM

PAYMENT_METHOD_CHOICES = (
    ("Any", "Any"),
    ("UPI", "UPI"),
    ("Bank Transfer", "Bank Transfer"),
    ("Cash", "Cash"),
    ("Card", "Card"),
    ("Net Banking", "Net Banking"),
)


class Payment(Main):
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="payments"
    )
    crm = models.ForeignKey(
        CRM, on_delete=models.SET_NULL, related_name="payments", null=True, blank=True
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_for = models.CharField(max_length=255)
    remarks = models.TextField(blank=True, null=True)
    invoice = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(
        max_length=50, choices=PAYMENT_METHOD_CHOICES, default="UPI"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"₹{self.amount} - {self.payment_for} ({self.contact.name})"


class RecurringPaymentSchedule(Main):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="recurring_schedules",
        null=True,
        blank=True,
    )
    crm = models.ForeignKey(
        CRM,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_schedules",
    )
    pipeline = models.ForeignKey(
        "crm.Pipeline",
        on_delete=models.CASCADE,
        related_name="recurring_schedules",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_schedules",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_for = models.CharField(max_length=255)
    payment_method = models.CharField(
        max_length=50, choices=PAYMENT_METHOD_CHOICES, default="UPI"
    )
    cycle_period_days = models.PositiveIntegerField(
        default=30, help_text="Days between cycles"
    )
    cycle_count = models.PositiveIntegerField(
        default=1, help_text="Total number of cycles"
    )
    completed_cycles = models.PositiveIntegerField(default=0)
    start_date = models.DateField()
    next_due_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(
        null=True, blank=True, help_text="Optional due date for single payment"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Recurring Payment Schedule"
        verbose_name_plural = "Recurring Payment Schedules"
        indexes = [
            models.Index(fields=["contact", "status"]),
            models.Index(fields=["next_due_date"]),
        ]
        constraints = [
            # A pipeline can only have one active rule at a time (rules with a
            # specific contact are excluded — they scope to contact, not pipeline)
            models.UniqueConstraint(
                fields=["pipeline"],
                condition=models.Q(status="active", contact__isnull=True),
                name="unique_active_pipeline_rule",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.next_due_date and self.start_date:
            self.next_due_date = self.start_date
        super().save(*args, **kwargs)

    def __str__(self):
        cname = (
            self.contact.name
            if self.contact
            else (self.pipeline.name if self.pipeline else "pipeline")
        )
        return f"↻ ₹{self.amount} x{self.cycle_count} every {self.cycle_period_days}d - {self.payment_for} ({cname})"
