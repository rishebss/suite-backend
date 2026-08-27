from django.db import models
from core.models import Main
from contacts.models import Contact

CRM_PRIORITY_CHOICES = (
    ("Low", "Low"),
    ("Medium", "Medium"),
    ("High", "High"),
)

PIPELINE_TYPE_CHOICES = (
    ("sales", "Sales"),
    ("retarget", "Retarget"),
    ("clients", "Clients"),
)

STAGE_COLOR_CHOICES = (
    ("blue", "Blue"),
    ("purple", "Purple"),
    ("amber", "Amber"),
    ("orange", "Orange"),
    ("green", "Green"),
    ("red", "Red"),
    ("pink", "Pink"),
    ("cyan", "Cyan"),
)

ASSIGNMENT_TYPE_CHOICES = (
    ("round_robin", "Round Robin"),
    ("least_loaded", "Least Loaded"),
    ("single_user", "Single User"),
    ("manual", "Manual"),
)


class Pipeline(Main):
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    departments = models.ManyToManyField(
        "authentication.Department", blank=True, related_name="pipelines"
    )
    assignment_type = models.CharField(
        max_length=20, choices=ASSIGNMENT_TYPE_CHOICES, default="manual"
    )
    pipeline_type = models.CharField(
        max_length=20, choices=PIPELINE_TYPE_CHOICES, default="sales"
    )
    assigned_user = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_pipelines",
    )
    mandatory_fields = models.JSONField(default=list, blank=True)
    custom_fields_enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pipeline"
        verbose_name_plural = "Pipelines"

    def __str__(self):
        return self.name


class Stage(Main):
    """Dynamic stages tied to a specific pipeline."""

    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.CASCADE, related_name="stages"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=20, choices=STAGE_COLOR_CHOICES, default="blue")

    class Meta:
        ordering = ["order"]
        unique_together = ("pipeline", "slug")
        verbose_name = "Stage"
        verbose_name_plural = "Stages"
        indexes = [
            models.Index(
                fields=["pipeline", "order"], name="crm_stage_pipeline_order_idx"
            ),
        ]

    def __str__(self):
        return f"{self.pipeline.name} → {self.name}"


class CRM(Main):
    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.CASCADE, related_name="deals", null=True, blank=True
    )
    stage = models.ForeignKey(
        Stage, on_delete=models.SET_NULL, related_name="deals", null=True, blank=True
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="crm_pipelines"
    )
    assigned_user = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_deals",
    )
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    priority = models.CharField(
        max_length=20, choices=CRM_PRIORITY_CHOICES, default="Medium"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "CRM Entry"
        verbose_name_plural = "CRM Entries"
        indexes = [
            models.Index(
                fields=["pipeline", "stage"], name="crm_crm_pipelin_stage_idx"
            ),
            models.Index(fields=["created_at"], name="crm_crm_created_at_idx"),
            models.Index(
                fields=["pipeline", "assigned_user"], name="crm_crm_pipelin_user_idx"
            ),
        ]

    def __str__(self):
        return f"{self.contact.name} - {self.stage.name if self.stage else 'No Stage'}"
