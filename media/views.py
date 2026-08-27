import logging

from django.http import FileResponse

logger = logging.getLogger(__name__)
from django.shortcuts import get_object_or_404
from django.db import models as db_models
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from media.models import MediaCollection, MediaAsset, MediaCollectionGroupPermission, MediaCreatorGroup
from media.utils import _find_contact_document_from_asset
from media.serializers import (
    MediaCollectionSerializer,
    MediaCollectionCreateSerializer,
    MediaCollectionGroupPermissionSerializer,
    MediaCreatorGroupSerializer,
    MediaAssetSerializer,
    MediaAssetUploadSerializer,
)
from authentication.models import Department


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_admin(user):
    """Check if user has Superadmin or Admin role."""
    return user.role in ('Superadmin', 'Admin') or user.is_superuser


def _can_create_collection(user):
    """
    Check if user can create collections.
    Returns True if:
    - User is Superadmin/Admin, OR
    - User belongs to a department that's in MediaCreatorGroup
    """
    if _is_admin(user):
        return True

    # Check if any of user's departments have creator permission
    user_dept_ids = list(user.departments.values_list('id', flat=True))
    if not user_dept_ids:
        return False

    return MediaCreatorGroup.objects.filter(
        department_id__in=user_dept_ids
    ).exists()


def _response(data, status_code=status.HTTP_200_OK):
    return Response({'success': True, 'data': data}, status=status_code)


def _error(message, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'message': message}, status=status_code)


# ---------------------------------------------------------------------------
# Collection query helpers
# ---------------------------------------------------------------------------

def _get_visible_collections(user):
    """
    Return the base QuerySet of collections the user can see.

    - Superadmin / Admin: all non-deleted collections.
    - Other users: collections that their groups (departments) have been
      granted access to via MediaCollectionGroupPermission.
    """
    qs = MediaCollection.objects.filter(is_deleted=False)

    if _is_admin(user):
        return qs

    # Non-admin: only collections where one of their departments is assigned
    user_dept_ids = list(user.departments.values_list('id', flat=True))
    if not user_dept_ids:
        return qs.none()

    return qs.filter(
        group_permissions__department_id__in=user_dept_ids
    ).distinct()


# ---------------------------------------------------------------------------
# Media Collections
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def collection_list_create(request):
    """
    GET  /api/media/collections/  — List collections visible to the user.
    POST /api/media/collections/  — Create a new collection (Superadmin/Admin only).
    """
    user = request.user

    if request.method == 'GET':
        collections = _get_visible_collections(user).order_by('-is_pinned', 'name')
        serializer = MediaCollectionSerializer(
            collections, many=True, context={'request': request}
        )
        return _response({
            'collections': serializer.data,
            'can_create': _can_create_collection(user),
        })

    # POST — only Superadmin / Admin or users in a creator group can create collections
    if not _can_create_collection(user):
        return _error(
            'You do not have permission to create collections.',
            status.HTTP_403_FORBIDDEN,
        )

    serializer = MediaCollectionCreateSerializer(
        data=request.data,
        context={'request': request},
    )
    if serializer.is_valid():
        collection = serializer.save()
        result = MediaCollectionSerializer(collection, context={'request': request})
        return _response(result.data, status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'message': 'Validation failed',
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def collection_detail(request, pk):
    """
    GET    /api/media/collections/{id}/  — Get collection details.
    PUT    /api/media/collections/{id}/  — Full update.
    PATCH  /api/media/collections/{id}/  — Partial update (rename, etc.).
    DELETE /api/media/collections/{id}/  — Soft delete collection and its assets.
    """
    collection = get_object_or_404(
        _get_visible_collections(request.user), pk=pk
    )

    if request.method == 'GET':
        serializer = MediaCollectionSerializer(
            collection, context={'request': request}
        )
        return _response(serializer.data)

    # Only admins or the collection creator can modify or delete collections
    if not _is_admin(request.user) and request.user != collection.created_by:
        return _error(
            'Only the creator or an admin can modify this collection.',
            status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'DELETE':
        # Prevent deletion of pinned collections
        if collection.is_pinned:
            return _error(
                'Pinned collections cannot be deleted. Unpin it first.',
                status.HTTP_400_BAD_REQUEST,
            )
        # Soft delete
        collection.is_deleted = True
        collection.deleted_at = timezone.now()
        collection.save(update_fields=['is_deleted', 'deleted_at'])

        assets_in_collection = list(collection.assets.all())
        collection.assets.all().update(is_deleted=True, deleted_at=timezone.now())

        # Cascade: hard-delete associated ContactDocuments
        for asset in assets_in_collection:
            contact_doc = _find_contact_document_from_asset(asset)
            if contact_doc:
                try:
                    contact_doc.delete()
                except Exception:
                    logger.exception(
                        "Failed to cascade-delete ContactDocument %s from collection delete",
                        contact_doc.id,
                    )

        return _response({
            'id': str(collection.id),
            'restore_url': f'/api/media/collections/{collection.id}/restore/',
        })

    # PUT / PATCH
    partial = request.method == 'PATCH'
    serializer = MediaCollectionCreateSerializer(
        collection,
        data=request.data,
        partial=partial,
        context={'request': request},
    )
    if serializer.is_valid():
        updated = serializer.save()
        result = MediaCollectionSerializer(
            updated, context={'request': request}
        )
        return _response(result.data)

    return Response({
        'success': False,
        'message': 'Validation failed',
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def collection_restore(request, pk):
    """
    POST /api/media/collections/{id}/restore/
    Restore a soft-deleted collection and its assets.
    """
    collection = get_object_or_404(
        MediaCollection.objects.filter(is_deleted=True),
        pk=pk,
    )
    collection.is_deleted = False
    collection.deleted_at = None
    collection.save(update_fields=['is_deleted', 'deleted_at'])
    collection.assets.filter(is_deleted=True).update(is_deleted=False, deleted_at=None)
    collection.asset_count = collection.assets.filter(is_deleted=False).count()
    collection.save(update_fields=['asset_count'])
    return _response({'message': 'Collection restored.'})


# ---------------------------------------------------------------------------
# Collection — Group Permissions (Superadmin / Admin only)
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def collection_group_permissions(request, pk):
    """
    GET  /api/media/collections/{id}/groups/  — List group permissions for a collection.
    POST /api/media/collections/{id}/groups/  — Batch-set group permissions.

    POST body: { "group_ids": ["<uuid>", ...] }
    Replaces all existing group assignments with the provided list.
    Only Superadmin / Admin, or the collection creator, can manage group permissions.
    """
    collection = get_object_or_404(MediaCollection, pk=pk, is_deleted=False)

    # Allow if admin OR collection creator
    if not _is_admin(request.user) and request.user != collection.created_by:
        return _error('Permission denied.', status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        perms = collection.group_permissions.select_related('department').all()
        serializer = MediaCollectionGroupPermissionSerializer(perms, many=True)
        return _response(serializer.data)

    # POST — batch replace group permissions
    group_ids = request.data.get('group_ids', [])
    if not isinstance(group_ids, list):
        return _error('group_ids must be a list.', status.HTTP_400_BAD_REQUEST)

    # Resolve departments
    departments = Department.objects.filter(id__in=group_ids)
    found_ids = set(str(d.id) for d in departments)
    missing = [gid for gid in group_ids if gid not in found_ids]
    if missing:
        return _error(
            f'Departments not found: {", ".join(missing)}',
            status.HTTP_404_NOT_FOUND,
        )

    # Remove existing permissions not in the new list
    collection.group_permissions.exclude(
        department_id__in=[d.id for d in departments]
    ).delete()

    # Add new permissions
    for dept in departments:
        MediaCollectionGroupPermission.objects.get_or_create(
            collection=collection,
            department=dept,
        )

    # Return updated list
    perms = collection.group_permissions.select_related('department').all()
    serializer = MediaCollectionGroupPermissionSerializer(perms, many=True)
    return _response(serializer.data)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def collection_group_permission_detail(request, pk, group_pk):
    """
    DELETE /api/media/collections/{id}/groups/{group_id}/
    Remove a single group permission from a collection.
    Only Superadmin / Admin, or the collection creator, can manage group permissions.
    """
    permission = get_object_or_404(
        MediaCollectionGroupPermission,
        collection_id=pk,
        department_id=group_pk,
    )

    # Allow if admin OR collection creator
    if not _is_admin(request.user) and request.user != permission.collection.created_by:
        return _error('Permission denied.', status.HTTP_403_FORBIDDEN)

    permission.delete()
    return _response({'message': 'Group permission removed.'})


# ---------------------------------------------------------------------------
# Creator Groups — who can create collections (Superadmin / Admin only)
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def creator_group_list(request):
    """
    GET  /api/media/creator-groups/  — List all creator groups.
    POST /api/media/creator-groups/  — Add a department to creator groups.

    POST body: { "department_id": "<uuid>" }
    Only Superadmin / Admin can manage creator groups.
    """
    if not _is_admin(request.user):
        return _error('Permission denied.', status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        groups = MediaCreatorGroup.objects.select_related('department').all()
        serializer = MediaCreatorGroupSerializer(groups, many=True)
        return _response(serializer.data)

    # POST — add a department to creator groups
    dept_id = request.data.get('department_id')
    if not dept_id:
        return _error('department_id is required.', status.HTTP_400_BAD_REQUEST)

    try:
        department = Department.objects.get(id=dept_id)
    except Department.DoesNotExist:
        return _error('Department not found.', status.HTTP_404_NOT_FOUND)

    creator_group, created = MediaCreatorGroup.objects.get_or_create(department=department)
    if created:
        serializer = MediaCreatorGroupSerializer(creator_group)
        return _response(serializer.data, status.HTTP_201_CREATED)
    else:
        return _response({'message': 'Department already has creator permission.'})


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def creator_group_detail(request, pk):
    """
    DELETE /api/media/creator-groups/{id}/
    Remove a department from creator groups.
    Only Superadmin / Admin can manage creator groups.
    """
    if not _is_admin(request.user):
        return _error('Permission denied.', status.HTTP_403_FORBIDDEN)

    creator_group = get_object_or_404(MediaCreatorGroup, pk=pk)
    creator_group.delete()
    return _response({'message': 'Creator permission removed.'})


# ---------------------------------------------------------------------------
# Entity Search (for collection entity_type = contact / staff)
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_entities(request):
    """
    GET /api/media/search-entities/?entity_type=contact&q=john

    Lightweight search endpoint that returns minimal info (id + display name)
    for Contacts and Employees, accessible to any authenticated user.
    """
    entity_type = request.query_params.get('entity_type', '')
    query = request.query_params.get('q', '').strip()

    if entity_type not in ('contact', 'staff'):
        return _error('entity_type must be "contact" or "staff".')

    if not query:
        return _response([])

    results = []

    if entity_type == 'contact':
        from contacts.models import Contact
        qs = Contact.objects.filter(
            db_models.Q(name__icontains=query)
            | db_models.Q(email__icontains=query)
            | db_models.Q(phone__icontains=query)
            | db_models.Q(contact_id__icontains=query)
        )[:20]
        for c in qs:
            results.append({
                'id': str(c.id),
                'name': c.name or '',
                'contact_id': c.contact_id,
                'email': c.email,
                'phone': c.phone,
                'label': f"{c.name} ({c.contact_id})",
            })

    elif entity_type == 'staff':
        # Search the User model — this is where staff/employee accounts live
        from authentication.models import User as AuthUser
        qs = AuthUser.objects.filter(
            db_models.Q(first_name__icontains=query)
            | db_models.Q(last_name__icontains=query)
            | db_models.Q(email__icontains=query)
            | db_models.Q(account_id__icontains=query)
        )[:20]
        for u in qs:
            results.append({
                'id': str(u.id),
                'name': u.get_full_name(),
                'employee_id': u.account_id,
                'email': u.email,
                'label': f"{u.get_full_name()} ({u.email})",
            })

    return _response(results)


# ---------------------------------------------------------------------------
# Media Assets
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def asset_list(request):
    """
    GET /api/media/assets/
    List assets, optionally filtered by collection_id.
    Only returns assets in collections the user can see.
    Query params: ?collection_id=<uuid>, ?file_type=, ?search=, ?is_deleted=true
    """
    visible_collections = _get_visible_collections(request.user)

    qs = MediaAsset.objects.select_related('collection', 'uploaded_by').filter(
        collection__in=visible_collections,
    )

    show_deleted = request.query_params.get('is_deleted') == 'true'
    if show_deleted:
        qs = qs.filter(is_deleted=True)
    else:
        qs = qs.filter(is_deleted=False)

    collection_id = request.query_params.get('collection_id')
    if collection_id:
        qs = qs.filter(collection_id=collection_id)

    file_type = request.query_params.get('file_type')
    if file_type:
        qs = qs.filter(file_type=file_type)

    search_query = request.query_params.get('search', '').strip()
    if search_query:
        qs = qs.filter(
            db_models.Q(file_name__icontains=search_query)
            | db_models.Q(source_display__icontains=search_query)
            | db_models.Q(source_object_id__icontains=search_query)
        )

    source_object_id = request.query_params.get('source_object_id', '').strip()
    if source_object_id:
        qs = qs.filter(source_object_id=source_object_id)

    qs = qs.order_by('-created_at')

    serializer = MediaAssetSerializer(qs, many=True, context={'request': request})
    return _response({
        'count': qs.count(),
        'results': serializer.data,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def asset_upload(request):
    """
    POST /api/media/assets/upload/
    Upload a file to a collection. Only allows uploads to collections the user can see.
    """
    serializer = MediaAssetUploadSerializer(
        data=request.data,
        context={'request': request},
    )
    if serializer.is_valid():
        asset = serializer.save()
        result = MediaAssetSerializer(asset, context={'request': request})
        return _response(result.data, status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'message': 'Validation failed',
        'errors': serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def asset_detail(request, pk):
    """
    GET    /api/media/assets/{id}/  — Get asset details.
    DELETE /api/media/assets/{id}/  — Soft delete an asset.
    """
    asset = get_object_or_404(
        MediaAsset.objects.select_related('collection', 'uploaded_by'),
        pk=pk,
        collection__in=_get_visible_collections(request.user),
    )

    if request.method == 'GET':
        serializer = MediaAssetSerializer(asset, context={'request': request})
        return _response(serializer.data)

    # DELETE — soft delete
    asset.is_deleted = True
    asset.deleted_at = timezone.now()
    asset.save(update_fields=['is_deleted', 'deleted_at'])

    MediaCollection.objects.filter(id=asset.collection_id).update(
        asset_count=db_models.F('asset_count') - 1
    )

    contact_doc = _find_contact_document_from_asset(asset)
    if contact_doc:
        try:
            contact_doc.delete()
            logger.info(
                "Cascade-deleted ContactDocument %s from MediaAsset %s deletion",
                contact_doc.id, asset.id,
            )
        except Exception as e:
            logger.exception(
                "Failed to cascade-delete ContactDocument %s: %s", contact_doc.id, e
            )

    return _response({
        'id': str(asset.id),
        'restore_url': f'/api/media/assets/{asset.id}/restore/',
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def asset_download(request, pk):
    """
    GET /api/media/assets/{id}/download/
    Download an asset.
    """
    user = request.user if request.user.is_authenticated else None

    if not user:
        token = request.query_params.get('token')
        if token:
            try:
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(token)
                user = jwt_auth.get_user(validated)
            except (InvalidToken, TokenError):
                pass

    if not user:
        return Response(
            {'detail': 'Authentication credentials were not provided.'},
            status=status.HTTP_401_UNAUTHORIZED,
            headers={'WWW-Authenticate': 'Bearer realm="api"'},
        )

    asset = get_object_or_404(
        MediaAsset.objects.select_related('collection'),
        pk=pk,
        collection__in=_get_visible_collections(user),
    )

    try:
        file_obj = asset.file.open('rb')
    except Exception as e:
        logger.warning('Failed to open asset file %s: %s', pk, e)
        return _error('Unable to serve file.', status.HTTP_404_NOT_FOUND)

    response = FileResponse(
        file_obj,
        as_attachment=True,
        filename=asset.file_name,
    )
    return response


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def asset_restore(request, pk):
    """
    POST /api/media/assets/{id}/restore/
    Restore a soft-deleted asset.
    """
    asset = get_object_or_404(
        MediaAsset.objects.filter(is_deleted=True),
        pk=pk,
        collection__in=_get_visible_collections(request.user),
    )
    asset.is_deleted = False
    asset.deleted_at = None
    asset.save(update_fields=['is_deleted', 'deleted_at'])

    MediaCollection.objects.filter(id=asset.collection_id).update(
        asset_count=db_models.F('asset_count') + 1
    )

    return _response({'message': 'Asset restored.'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def asset_batch_delete(request):
    """
    POST /api/media/assets/batch-delete/
    Soft-delete multiple assets at once.
    """
    ids = request.data.get('ids', [])
    if not ids:
        return _error('No asset IDs provided.', status.HTTP_400_BAD_REQUEST)

    assets = MediaAsset.objects.filter(
        id__in=ids,
        collection__in=_get_visible_collections(request.user),
        is_deleted=False,
    )
    count = assets.count()
    now = timezone.now()
    collection_ids = set(assets.values_list('collection_id', flat=True))

    assets.update(is_deleted=True, deleted_at=now)

    for asset in assets.iterator():
        contact_doc = _find_contact_document_from_asset(asset)
        if contact_doc:
            try:
                contact_doc.delete()
            except Exception:
                logger.exception(
                    "Failed to cascade-delete ContactDocument %s from batch delete",
                    contact_doc.id,
                )

    for cid in collection_ids:
        MediaCollection.objects.filter(id=cid).update(
            asset_count=db_models.F('asset_count') - count
        )

    return _response({'deleted': count})
