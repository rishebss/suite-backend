from django.contrib import admin
from media.models import MediaCollection, MediaAsset


@admin.register(MediaCollection)
class MediaCollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'asset_count', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'created_by__email']
    readonly_fields = ['asset_count', 'created_at', 'updated_at']


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'file_type', 'file_size', 'collection', 'uploaded_by', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['file_name', 'collection__name']
    readonly_fields = ['file_name', 'file_type', 'mime_type', 'file_size', 'width', 'height', 'created_at', 'updated_at']
