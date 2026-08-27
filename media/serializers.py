from rest_framework import serializers
from django.db import models
from media.models import MediaCollection, MediaAsset, MediaCollectionGroupPermission, MediaCreatorGroup


# ---------------------------------------------------------------------------
# MediaCollection
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Media Creator Groups (who can create collections)
# ---------------------------------------------------------------------------

class MediaCreatorGroupSerializer(serializers.ModelSerializer):
    """Serializer for MediaCreatorGroup — which departments can create collections."""
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_id = serializers.UUIDField(source='department.id', read_only=True)

    class Meta:
        model = MediaCreatorGroup
        fields = ['id', 'department_id', 'department_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class MediaCollectionGroupPermissionSerializer(serializers.ModelSerializer):
    """Serializer for group-to-collection permission assignment."""
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_id = serializers.UUIDField(source='department.id', read_only=True)

    class Meta:
        model = MediaCollectionGroupPermission
        fields = ['id', 'collection', 'department_id', 'department_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class MediaCollectionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    group_permissions = MediaCollectionGroupPermissionSerializer(many=True, read_only=True)
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = MediaCollection
        fields = [
            'id', 'name', 'description', 'entity_type', 'is_pinned', 'asset_count',
            'created_by', 'created_by_name',
            'group_permissions', 'is_admin',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'asset_count', 'created_by', 'created_by_name', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.email
        return ''

    def get_is_admin(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return request.user.role in ('Superadmin', 'Admin')
        return False


class MediaCollectionCreateSerializer(serializers.ModelSerializer):
    group_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        help_text='List of Department UUIDs to grant access to this collection',
    )

    class Meta:
        model = MediaCollection
        fields = ['name', 'description', 'entity_type', 'is_pinned', 'group_ids']

    def validate_name(self, value):
        user = self.context['request'].user
        qs = MediaCollection.objects.filter(
            name__iexact=value,
            created_by=user,
            is_deleted=False,  # Allow re-creating after soft delete
        )
        # When updating (rename), exclude the collection itself from the check
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A collection with this name already exists.")
        return value

    def _resolve_departments(self, group_ids):
        """Resolve Department objects from UUIDs. Returns (departments, missing_ids)."""
        from authentication.models import Department
        departments = Department.objects.filter(id__in=group_ids)
        found = set(str(d.id) for d in departments)
        missing = [str(gid) for gid in group_ids if str(gid) not in found]
        return list(departments), missing

    def create(self, validated_data):
        user = self.context['request'].user
        group_ids = validated_data.pop('group_ids', [])
        validated_data['created_by'] = user
        collection = super().create(validated_data)

        from media.models import MediaCollectionGroupPermission

        # Always include the creator's own departments so they can see the collection
        creator_dept_ids = list(user.departments.values_list('id', flat=True))
        merged_ids = list(set(str(gid) for gid in group_ids) | set(str(did) for did in creator_dept_ids))

        departments, _ = self._resolve_departments(merged_ids)
        for dept in departments:
            MediaCollectionGroupPermission.objects.get_or_create(
                collection=collection,
                department=dept,
            )

        return collection

    def update(self, instance, validated_data):
        group_ids = validated_data.pop('group_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace group permissions if group_ids provided
        if group_ids is not None:
            from media.models import MediaCollectionGroupPermission
            departments, _ = self._resolve_departments(group_ids)
            instance.group_permissions.exclude(
                department_id__in=[d.id for d in departments]
            ).delete()
            for dept in departments:
                MediaCollectionGroupPermission.objects.get_or_create(
                    collection=instance,
                    department=dept,
                )

        return instance


# ---------------------------------------------------------------------------
# MediaAsset
# ---------------------------------------------------------------------------

class MediaAssetSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    file_size_display = serializers.CharField(read_only=True)
    dimensions_display = serializers.CharField(read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    collection_name = serializers.CharField(source='collection.name', read_only=True)

    # Source mapping fields
    source_display = serializers.CharField(read_only=True)
    source_content_type_id = serializers.IntegerField(read_only=True)
    source_object_id = serializers.CharField(read_only=True)

    class Meta:
        model = MediaAsset
        fields = [
            'id', 'collection', 'collection_name',
            'file', 'file_url', 'download_url',
            'file_name', 'file_type', 'mime_type',
            'file_size', 'file_size_display',
            'width', 'height', 'dimensions_display',
            'uploaded_by', 'uploaded_by_name',
            'source_display', 'source_content_type_id', 'source_object_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'file_url', 'download_url', 'file_size_display', 'dimensions_display',
            'uploaded_by', 'uploaded_by_name',
            'source_display', 'source_content_type_id', 'source_object_id',
            'file_name', 'file_type', 'mime_type', 'file_size', 'width', 'height',
            'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'file': {'write_only': True},
        }

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def get_download_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/media/assets/{obj.id}/download/')
        return f'/api/media/assets/{obj.id}/download/'

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.email
        return ''


class MediaAssetUploadSerializer(serializers.Serializer):
    """Accepts a file upload and associates it with a collection."""
    file = serializers.FileField(required=True)
    collection_id = serializers.UUIDField(required=True)
    source_entity_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='UUID of the Contact or Employee this asset belongs to (if collection has entity_type)',
    )

    def validate_collection_id(self, value):
        try:
            collection = MediaCollection.objects.get(id=value)
        except MediaCollection.DoesNotExist:
            raise serializers.ValidationError("Collection not found.")
        # Store the collection instance for use in create() and validate()
        self._collection = collection
        return value

    def validate_source_entity_id(self, value):
        if not value:
            return value

        collection = self._collection
        if collection.entity_type == 'generic':
            raise serializers.ValidationError(
                "This collection does not map to any entity. Remove the source_entity_id."
            )

        from django.contrib.contenttypes.models import ContentType

        if collection.entity_type == 'contact':
            from contacts.models import Contact
            try:
                entity = Contact.objects.get(id=value)
            except Contact.DoesNotExist:
                raise serializers.ValidationError("Contact not found.")
            self._source_content_type = ContentType.objects.get_for_model(Contact)
            self._source_object_id = str(entity.id)
            self._source_display = f"Contact: {entity.name} ({entity.contact_id})"

        elif collection.entity_type == 'staff':
            from authentication.models import User as AuthUser
            try:
                entity = AuthUser.objects.get(id=value)
            except AuthUser.DoesNotExist:
                raise serializers.ValidationError("User not found.")
            self._source_content_type = ContentType.objects.get_for_model(AuthUser)
            self._source_object_id = str(entity.id)
            self._source_display = f"Staff: {entity.get_full_name()} ({entity.email})"

        return value

    def validate_file(self, value):
        # Check content type to determine size limit
        content_type = value.content_type or ''
        if content_type.startswith('video/'):
            max_size = 100 * 1024 * 1024  # 100 MB for videos
        else:
            max_size = 50 * 1024 * 1024  # 50 MB for everything else
        if value.size > max_size:
            limit_mb = max_size // (1024 * 1024)
            raise serializers.ValidationError(f"File must be {limit_mb} MB or smaller.")
        return value

    def create(self, validated_data):
        import os
        from PIL import Image as PILImage

        file = validated_data['file']
        collection = self._collection

        # Attempt to get image dimensions
        width, height = None, None
        try:
            img = PILImage.open(file)
            width, height = img.size
            # Seek back to beginning so the file can be saved properly
            file.seek(0)
        except Exception:
            pass

        asset_kwargs = {
            'collection': collection,
            'file': file,
            'file_name': os.path.basename(file.name),
            'file_size': file.size,
            'width': width,
            'height': height,
            'uploaded_by': self.context['request'].user,
        }

        # Set source mapping if the collection has an entity type and a source was resolved
        if hasattr(self, '_source_content_type') and self._source_content_type:
            asset_kwargs['source_content_type'] = self._source_content_type
            asset_kwargs['source_object_id'] = self._source_object_id
            asset_kwargs['source_display'] = self._source_display

        asset = MediaAsset.objects.create(**asset_kwargs)

        # Update denormalised count
        MediaCollection.objects.filter(id=collection.id).update(
            asset_count=models.F('asset_count') + 1
        )

        return asset
