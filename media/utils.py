"""
Media sync utilities — allow other modules (contacts, HR, etc.) to
automatically push files into the user's Media library so they appear
alongside manually uploaded assets.

Usage:
    from media.utils import sync_file_to_media_library

    sync_file_to_media_library(
        file_content=file_bytes_or_contentfile,
        file_name="document.pdf",
        collection_name="Employee Documents",
        uploaded_by=request.user,
        source_object=contact_instance,
        source_display="Contact: John Doe (CUS-001)",
    )
"""
import logging
from django.core.files.base import ContentFile
from django.db import models as db_models

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Collection name constants — used by signals and other modules
# ─────────────────────────────────────────────────────────────────────────────

COLLECTION_HR_DOCUMENTS = "HR Documents"
COLLECTION_HR_PHOTOS = "Employee Photos"
COLLECTION_CONTACT_DOCUMENTS = "Contact Files"


def _get_or_create_collection(name, user, pinned=True, description=""):
    """
    Find or create a pinned media collection for the given user.
    Returns (collection, created).
    """
    from media.models import MediaCollection

    collection, created = MediaCollection.objects.get_or_create(
        name=name,
        created_by=user,
        defaults={
            "is_pinned": pinned,
            "description": description,
        },
    )

    # Keep pinned collections pinned even if someone unpinned them
    if not created and pinned and not collection.is_pinned:
        MediaCollection.objects.filter(id=collection.id).update(is_pinned=True)

    return collection, created


def _find_contact_document_from_asset(asset):
    """
    Given a MediaAsset that was synced from a ContactDocument, find the
    original ContactDocument by matching source_object_id (Contact UUID) and
    file_name (the full upload path originally stored).

    Returns the ContactDocument instance or None.
    """
    from contacts.models import ContactDocument

    if not asset.source_object_id or not asset.file_name:
        return None

    try:
        # The asset's source_object_id is the Contact UUID, and file_name
        # was set to ContactDocument.file.name (the full upload path).
        return ContactDocument.objects.filter(
            contact_id=asset.source_object_id,
            file__endswith=asset.file_name.rsplit("/", 1)[-1],
        ).first()
    except Exception:
        logger.exception("Failed to find ContactDocument for asset %s", asset.id)
        return None


def sync_file_to_media_library(
    file_content,
    file_name,
    collection_name,
    uploaded_by,
    description="",
    skip_if_exists=True,
    source_object=None,
    source_display="",
):
    """
    Save a copy of *file_content* into a named media collection so the file
    appears in the user's Media library.

    Parameters
    ----------
    file_content : bytes or ContentFile or File
        The raw bytes / Django file object to store.
    file_name : str
        Target filename (e.g. ``"photo_2025-01-01.jpg"``).
    collection_name : str
        Name of the ``MediaCollection`` (created/pinned automatically).
    uploaded_by : User
        The user who owns this asset.
    description : str, optional
        Collection description (used only on first creation).
    skip_if_exists : bool, default True
        If ``True`` and an asset with the same file_name already exists in
        the collection, silently skip instead of creating a duplicate.
    source_object : Model instance or None, optional
        The source entity this file belongs to (Contact, Employee, etc.)
        Will be stored via a GenericForeignKey for cross-referencing.
    source_display : str, optional
        Human-readable label for the source, e.g.
        ``"Contact: John Doe (CUS-001)"``

    Returns
    -------
    media.models.MediaAsset or None
        The created asset, or ``None`` if skipped.
    """
    try:
        from media.models import MediaAsset, MediaCollection

        collection, _ = _get_or_create_collection(
            collection_name,
            uploaded_by,
            pinned=True,
            description=description,
        )

        # Optionally skip duplicates
        if skip_if_exists and MediaAsset.objects.filter(
            collection=collection, file_name=file_name
        ).exists():
            return None

        # Wrap raw bytes in a ContentFile if needed
        if isinstance(file_content, (bytes, bytearray)):
            file_content = ContentFile(file_content, name=file_name)

        asset_kwargs = {
            "collection": collection,
            "file": file_content,
            "file_name": file_name,
            "uploaded_by": uploaded_by,
        }

        # Attach source entity info for cross-referencing
        if source_object is not None:
            asset_kwargs["source_object"] = source_object
        if source_display:
            asset_kwargs["source_display"] = source_display

        asset = MediaAsset.objects.create(**asset_kwargs)

        # Bump the denormalised count
        MediaCollection.objects.filter(id=collection.id).update(
            asset_count=db_models.F("asset_count") + 1
        )

        return asset

    except Exception:
        logger.exception(
            "Failed to sync '%s' to media collection '%s' for user %s",
            file_name,
            collection_name,
            uploaded_by,
        )
        return None
