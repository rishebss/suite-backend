import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.models import Main

CONTACT_STATUS = (
    ("Lead", "Lead"),
    ("Prospect", "Prospect"),
    ("Customer", "Customer"),
    ("Inactive", "Inactive"),
    ("Retarget", "Retarget"),
    ("Imports", "Imports"),
)


class ImportBatch(Main):
    """Represents a single import session — groups contacts by their source."""

    name = models.CharField(
        max_length=255, help_text="User-defined import name, e.g. 'Q1 Trade Show Leads'"
    )
    contact_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Import Batch"
        verbose_name_plural = "Import Batches"

    def __str__(self):
        return f"{self.name} ({self.contact_count} contacts)"


class Contact(Main):
    """
    Contact model for storing customer coordinates.
    Validation: Must have (Name + Phone) OR (Name + Email)
    """

    contact_id = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=50, choices=CONTACT_STATUS, default="Lead")
    additional_data = models.JSONField(
        default=dict, blank=True, help_text="Additional JSON attributes"
    )
    import_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="contacts",
        help_text="The import batch this contact belongs to",
    )
    source = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Import batch name, denormalized for fast filtering",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"

    def clean(self):
        if not self.name:
            raise ValidationError(_("Contact name is required."))
        if not self.email and not self.phone:
            raise ValidationError(
                _("Either Phone or Email must be provided alongside the Name.")
            )

    def generate_contact_id(self):
        last_contact = Contact.objects.order_by("created_at").last()
        if not last_contact:
            return "CON-1001"
        try:
            last_id_int = int(last_contact.contact_id.split("-")[1])
            return f"CON-{last_id_int + 1}"
        except (IndexError, ValueError):
            return f"CON-{uuid.uuid4().hex[:6].upper()}"

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.contact_id:
            self.contact_id = self.generate_contact_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.contact_id})"


class ContactLog(Main):
    from django.conf import settings

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="logs")
    crm = models.ForeignKey(
        "crm.CRM", on_delete=models.SET_NULL, null=True, blank=True, related_name="logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_logs",
    )
    activity_type = models.CharField(max_length=100)
    description = models.TextField()
    pipeline_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Log"
        verbose_name_plural = "Contact Logs"

    def __str__(self):
        return f"{self.contact.name} - {self.activity_type} - {self.description[:30]}"


class ContactRemark(Main):
    from django.conf import settings

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="remarks"
    )
    crm = models.ForeignKey(
        "crm.CRM",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="remarks",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_remarks",
    )
    text = models.TextField()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Remark"
        verbose_name_plural = "Contact Remarks"

    def __str__(self):
        return f"{self.contact.name} - {self.text[:30]}"


class ContactDocument(Main):
    """
    Files / images attached to a contact (proof documents, customer photos, etc.).
    Auto-synced to the Media library via post_save signal.
    """

    from django.conf import settings

    DOCUMENT_TYPE_CHOICES = [
        ("photo", "Photo"),
        ("proof", "Proof Document"),
        ("contract", "Contract"),
        ("invoice", "Invoice"),
        ("other", "Other"),
    ]

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(
        max_length=50, choices=DOCUMENT_TYPE_CHOICES, default="other"
    )
    file = models.FileField(upload_to="contact_documents/%Y/%m/")
    file_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_document_uploads",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Document"
        verbose_name_plural = "Contact Documents"

    def __str__(self):
        return f"{self.contact.name} - {self.get_document_type_display()}: {self.file_name}"
