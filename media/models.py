import os
import mimetypes
from django.db import models
from django.conf import settings
from django.db.models import Q
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.models import Main


def asset_upload_path(instance, filename):
    """Organise assets by collection ID to keep paths tidy."""
    return f"media_assets/{instance.collection_id}/{filename}"


class MediaCreatorGroup(Main):
    """
    Maps a Department (group) to the ability to create MediaCollections.
    Users in this department can create collections and manage group access
    on them, even if they're not Superadmin/Admin.
    Only Superadmin/Admin can manage this setting.
    """
    department = models.OneToOneField(
        'authentication.Department',
        on_delete=models.CASCADE,
        related_name='media_creator_permissions',
    )

    class Meta:
        ordering = ['department__name']
        verbose_name = 'Media Creator Group'
        verbose_name_plural = 'Media Creator Groups'

    def __str__(self):
        return f"Creators: {self.department.name}"


class MediaCollectionGroupPermission(Main):
    """
    Maps a Department (group) to a MediaCollection.
    Users in the department inherit access to the collection.
    Superadmin and Admin always have access to all collections.
    """
    collection = models.ForeignKey(
        'MediaCollection',
        on_delete=models.CASCADE,
        related_name='group_permissions',
    )
    department = models.ForeignKey(
        'authentication.Department',
        on_delete=models.CASCADE,
        related_name='media_collection_permissions',
    )

    class Meta:
        unique_together = ('collection', 'department')
        ordering = ['collection', 'department']
        verbose_name = 'Media Collection Group Permission'
        verbose_name_plural = 'Media Collection Group Permissions'
        indexes = [
            models.Index(fields=['collection']),
            models.Index(fields=['department']),
        ]

    def __str__(self):
        return f"{self.collection.name} → {self.department.name}"


class MediaCollection(Main):
    """
    User-defined dynamic collection / folder for grouping media assets.
    Users can create collections like "Invoices", "Marketing", "Brand Assets", etc.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='media_collections',
    )
    ENTITY_TYPES = (
        ('generic', 'Generic'),
        ('contact', 'Contact'),
        ('staff', 'Staff'),
    )

    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPES,
        default='generic',
        help_text="Type of entity this collection's assets map to (Generic, Contact, or Staff)",
    )
    is_pinned = models.BooleanField(default=False, help_text="Pinned collections appear first in the list")
    asset_count = models.PositiveIntegerField(default=0, help_text="Denormalised count for fast display")
    is_deleted = models.BooleanField(default=False, help_text="Soft delete flag for undo support")
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="When the item was soft-deleted")

    class Meta:
        ordering = ['-is_pinned', 'name']
        verbose_name = 'Media Collection'
        verbose_name_plural = 'Media Collections'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'created_by'],
                condition=Q(is_deleted=False),
                name='unique_collection_name_per_user',
            ),
        ]
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['is_pinned']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return self.name


class MediaAsset(Main):
    """
    A single uploaded file belonging to a MediaCollection.
    Stores file metadata so the frontend can display thumbnails, sizes, etc.
    """

    IMAGE = 'image'
    VIDEO = 'video'
    DOCUMENT = 'document'
    AUDIO = 'audio'
    OTHER = 'other'

    FILE_TYPE_CHOICES = [
        (IMAGE, 'Image'),
        (VIDEO, 'Video'),
        (DOCUMENT, 'Document'),
        (AUDIO, 'Audio'),
        (OTHER, 'Other'),
    ]

    collection = models.ForeignKey(
        MediaCollection,
        on_delete=models.CASCADE,
        related_name='assets',
    )
    file = models.FileField(upload_to=asset_upload_path)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default=OTHER)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    width = models.IntegerField(null=True, blank=True, help_text="Width in px (images/videos)")
    height = models.IntegerField(null=True, blank=True, help_text="Height in px (images/videos)")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='media_uploads',
    )

    # ── Source mapping (which entity does this file belong to?) ──
    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Content type of the source entity (Contact, Employee, etc.)",
    )
    source_object_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Primary key of the source entity",
    )
    source_object = GenericForeignKey('source_content_type', 'source_object_id')
    source_display = models.CharField(
        max_length=500,
        blank=True,
        help_text="Human-readable label like 'Contact: John Doe (CUS-001)'",
    )

    is_deleted = models.BooleanField(default=False, help_text="Soft delete flag for undo support")
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="When the item was soft-deleted")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Media Asset'
        verbose_name_plural = 'Media Assets'
        indexes = [
            models.Index(fields=['collection', 'file_type']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return self.file_name

    def save(self, *args, **kwargs):
        # Auto-populate file_name from the uploaded file if not set
        if not self.file_name and self.file:
            self.file_name = os.path.basename(self.file.name)

        # Auto-detect mime type
        if not self.mime_type and self.file_name:
            mime_type, _ = mimetypes.guess_type(self.file_name)
            self.mime_type = mime_type or ''

        # Auto-classify file type from mime type
        if not self.file_type or self.file_type == MediaAsset.OTHER:
            self.file_type = self._classify_file_type()

        # Auto-populate file_size
        if not self.file_size and self.file:
            try:
                size = self.file.size
                if size is not None:
                    self.file_size = size
            except Exception:
                pass

        super().save(*args, **kwargs)

    def _classify_file_type(self):
        mt = self.mime_type.lower()
        if mt.startswith('image/'):
            return MediaAsset.IMAGE
        if mt.startswith('video/'):
            return MediaAsset.VIDEO
        if mt.startswith('audio/'):
            return MediaAsset.AUDIO
        if mt.startswith('application/') or mt.startswith('text/'):
            return MediaAsset.DOCUMENT
        return MediaAsset.OTHER

    @property
    def file_size_display(self):
        """Human-readable file size."""
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 ** 3:
            return f"{size / 1024 ** 2:.1f} MB"
        else:
            return f"{size / 1024 ** 3:.2f} GB"

    @property
    def dimensions_display(self):
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return ""

