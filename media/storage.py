"""
Custom Cloudinary storage that uses the ``raw`` resource type for all uploads.

Cloudinary's ``MediaCloudinaryStorage`` hard-codes ``RESOURCE_TYPE = 'image'``,
which causes "Invalid image file" errors when uploading non-image files
(videos, PDFs, Word docs, etc.).

Using ``raw`` avoids this because Cloudinary does not validate or transform
raw files — it simply stores and serves them as-is.  It also preserves the
original file extension in the public ID, so URL generation and deletion
work reliably across all file types.

The trade-off is that we lose Cloudinary's automatic image-optimisation
pipeline (auto-format, auto-quality, responsive breakpoints, etc.).  Image
transformations can still be added later via explicit URL parameters if
needed.
"""

from cloudinary_storage.storage import MediaCloudinaryStorage, RESOURCE_TYPES


class SmartMediaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Drop-in replacement for ``MediaCloudinaryStorage`` that uses the ``raw``
    resource type for every upload.  This lets images, videos, PDFs, and
    other documents all pass through the same storage backend without
    Cloudinary rejecting non-image files.
    """

    RESOURCE_TYPE = RESOURCE_TYPES['RAW']  # 'raw' — works for all file types

    def _get_resource_type(self, name):
        return self.RESOURCE_TYPE
