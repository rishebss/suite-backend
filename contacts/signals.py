"""
Signals for the contacts app — auto-sync uploaded files to the Media library
so contact images/proofs appear in the user's media page.

Also handles cascade deletion: deleting a ContactDocument removes the
synced MediaAsset, and vice versa.
"""
import logging
import mimetypes
import os

from django.db import models as db_models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from contacts.models import ContactDocument
from media.utils import COLLECTION_CONTACT_DOCUMENTS

logger = logging.getLogger(__name__)


def _classify_file_type(mime_type, file_name):
    """Classify a file into image/video/audio/document/other based on its info."""
    if not mime_type:
        mime_type = ''
    mime_type = mime_type.lower()
    if mime_type.startswith('image/'):
        return 'image'
    if mime_type.startswith('video/'):
        return 'video'
    if mime_type.startswith('audio/'):
        return 'audio'
    if mime_type.startswith('application/') or mime_type.startswith('text/'):
        return 'document'
    # Fallback: guess from extension
    ext = os.path.splitext(file_name)[1].lower() if file_name else ''
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'):
        return 'image'
    if ext in ('.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv'):
        return 'video'
    if ext in ('.mp3', '.wav', '.ogg', '.flac', '.aac'):
        return 'audio'
    if ext in ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.json', '.xml', '.html', '.md'):
        return 'document'
    return 'other'


@receiver(post_save, sender=ContactDocument)
def sync_contact_document_to_media(sender, instance, created, **kwargs):
    """
    When a contact document is uploaded, sync it to the media library
    so it appears on the Media page.

    Instead of downloading the file from Cloudinary and re-uploading
    (which fails with 401 for raw resources), we directly reference
    the SAME Cloudinary file path in the MediaAsset.
    """
    if not instance.file:
        logger.warning("ContactDocument %s has no file, skipping media sync.", instance.id)
        return

    uploaded_by = instance.uploaded_by
    if not uploaded_by:
        logger.warning("ContactDocument %s has no uploaded_by, skipping media sync.", instance.id)
        return

    # Get the Cloudinary file path (public_id) from the existing file
    cloudinary_path = instance.file.name
    if not cloudinary_path:
        logger.warning("ContactDocument %s has empty file.name, skipping.", instance.id)
        return

    from media.models import MediaAsset, MediaCollection

    # Get or create the "Contact Files" collection for this user
    collection, _ = MediaCollection.objects.get_or_create(
        name=COLLECTION_CONTACT_DOCUMENTS,
        created_by=uploaded_by,
        defaults={"is_pinned": True},
    )

    # Avoid duplicates — check if we already synced this file
    if MediaAsset.objects.filter(
        collection=collection,
        file_name=cloudinary_path,
    ).exists():
        logger.info(
            "ContactDocument %s already synced to MediaAsset (file_name=%s), skipping.",
            instance.id, cloudinary_path,
        )
        return

    # Auto-detect file info
    mime_type, _ = mimetypes.guess_type(cloudinary_path)
    file_type = _classify_file_type(mime_type, cloudinary_path)

    # Create MediaAsset referencing the EXISTING Cloudinary file (no re-upload)
    try:
        asset = MediaAsset(
            collection=collection,
            file=cloudinary_path,  # String reference to existing Cloudinary file
            file_name=cloudinary_path,
            file_type=file_type,
            mime_type=mime_type or '',
            file_size=0,
            uploaded_by=uploaded_by,
            width=None,
            height=None,
        )
        # Set source entity info for cross-referencing
        if instance.contact is not None:
            asset.source_object = instance.contact
        asset.source_display = (
            f"Contact: {instance.contact.name} ({instance.contact.contact_id})"
        )

        asset.save()

        # Bump denormalised count
        MediaCollection.objects.filter(id=collection.id).update(
            asset_count=db_models.F("asset_count") + 1
        )

        logger.info(
            "Synced ContactDocument %s → MediaAsset %s in collection '%s' "
            "(referenced existing Cloudinary file: %s)",
            instance.id, asset.id, COLLECTION_CONTACT_DOCUMENTS, cloudinary_path,
        )
    except Exception:
        logger.exception(
            "Failed to create MediaAsset for ContactDocument %s (file: %s)",
            instance.id, cloudinary_path,
        )


@receiver(post_delete, sender=ContactDocument)
def delete_media_asset_for_contact_document(sender, instance, **kwargs):
    """
    When a ContactDocument is hard-deleted, also remove the synced MediaAsset.
    Matches on source_object_id (Contact UUID) + file name.
    """
    if not instance.file or not instance.contact_id:
        return

    from media.models import MediaAsset

    file_name = getattr(instance.file, 'name', None)
    if not file_name:
        return

    try:
        matched = MediaAsset.objects.filter(
            source_object_id=str(instance.contact_id),
            file_name=file_name,
        )
        deleted_count, _ = matched.delete()
        if deleted_count:
            logger.info(
                "Cascade deleted %d MediaAsset(s) for ContactDocument %s",
                deleted_count, instance.id,
            )
    except Exception:
        logger.exception(
            "Failed to cascade-delete MediaAsset for ContactDocument %s", instance.id
        )
