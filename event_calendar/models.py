import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class CalendarTodo(models.Model):
    TODO_TYPES = [
        ("task", "Task"),
        ("event", "Event"),
        ("followup", "Follow Up"),
        ("meeting", "Meeting"),
    ]

    FOLLOWUP_STATUS_CHOICES = [
        ("follow_up", "Follow Up"),
        ("failed", "Failed"),
        ("complete", "Complete"),
        ("cancelled", "Cancelled"),
    ]

    MEETING_STATUS_CHOICES = [
        ("upcoming", "Upcoming"),
        ("live", "Live"),
        ("ended", "Ended"),
        ("cancelled", "Cancelled"),
    ]

    EVENT_STATUS_CHOICES = [
        ("upcoming", "Upcoming"),
        ("live", "Live"),
        ("ended", "Ended"),
        ("cancelled", "Cancelled"),
    ]

    TASK_STATUS_CHOICES = [
        ("assigned", "Assigned"),
        ("progress", "Progress"),
        ("completed", "Completed"),
        ("canceled", "Canceled"),
        ("on_hold", "On Hold"),
        ("overdue", "Overdue"),
        ("approved", "Approved"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_todos",
    )
    todo_type = models.CharField(max_length=20, choices=TODO_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, blank=True, null=True
    )

    start = models.DateTimeField(blank=True, null=True)
    end = models.DateTimeField(blank=True, null=True)

    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="followups",
    )

    status = models.CharField(max_length=20, blank=True, null=True)
    hold_reason = models.TextField(blank=True, null=True)
    extension_request = models.TextField(blank=True, null=True)
    completion_remarks = models.TextField(blank=True, null=True)
    followup_cancellation = models.TextField(blank=True, null=True)
    followup_failed = models.TextField(blank=True, null=True)

    location = models.CharField(max_length=255, blank=True, null=True)

    pipeline = models.ForeignKey(
        "crm.Pipeline",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="followups",
    )

    crm = models.ForeignKey(
        "crm.CRM",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="followups",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="todo_assignments",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event_calendar_todos"
        ordering = ["-created_at"]

    @staticmethod
    def compute_event_status(start, end, status):
        if start and status not in ("cancelled",):
            now = timezone.now()
            if end:
                if end < now:
                    return "ended"
                elif start <= now <= end and status != "ended":
                    return "live"
                elif start > now:
                    return "upcoming"
            else:
                if start < now and status != "ended":
                    return "ended"
                else:
                    return "upcoming"
        return status

    def save(self, *args, **kwargs):
        if self.todo_type == "task" and self.start:
            if self.start < timezone.now() and self.status not in (
                "completed",
                "on_hold",
                "approved",
                "canceled",
            ):
                self.status = "overdue"
            elif self.status == "overdue" and self.start > timezone.now():
                self.status = "assigned"

        if self.todo_type == "followup" and self.start:
            if self.start < timezone.now() and self.status == "follow_up":
                self.status = "failed"
            elif self.status == "failed" and self.start > timezone.now():
                self.status = "follow_up"
                self.followup_failed = None

        if self.todo_type in ("event", "meeting"):
            self.status = self.compute_event_status(self.start, self.end, self.status)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.get_todo_type_display()}] {self.title}"


class MeetingAttendee(models.Model):
    todo = models.ForeignKey(
        CalendarTodo, on_delete=models.CASCADE, related_name="attendees"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        db_table = "event_calendar_meeting_attendees"
        unique_together = ["todo", "user"]

    def __str__(self):
        return f"{self.user} -> {self.todo.title}"
