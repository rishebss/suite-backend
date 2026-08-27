from django.urls import path
from . import views

app_name = 'media'

urlpatterns = [
    # Entity Search
    path('media/search-entities/', views.search_entities, name='search-entities'),

    # Creator Groups — who can create collections (admin-only)
    path('media/creator-groups/', views.creator_group_list, name='creator-group-list'),
    path('media/creator-groups/<uuid:pk>/', views.creator_group_detail, name='creator-group-detail'),

    # Collections
    path('media/collections/', views.collection_list_create, name='collection-list-create'),
    path('media/collections/<uuid:pk>/', views.collection_detail, name='collection-detail'),
    path('media/collections/<uuid:pk>/restore/', views.collection_restore, name='collection-restore'),

    # Collection Group Permissions
    path('media/collections/<uuid:pk>/groups/', views.collection_group_permissions, name='collection-group-permissions'),
    path('media/collections/<uuid:pk>/groups/<uuid:group_pk>/', views.collection_group_permission_detail, name='collection-group-permission-detail'),

    # Assets
    path('media/assets/', views.asset_list, name='asset-list'),
    path('media/assets/upload/', views.asset_upload, name='asset-upload'),
    path('media/assets/<uuid:pk>/', views.asset_detail, name='asset-detail'),
    path('media/assets/<uuid:pk>/download/', views.asset_download, name='asset-download'),
    path('media/assets/<uuid:pk>/restore/', views.asset_restore, name='asset-restore'),
    path('media/assets/batch-delete/', views.asset_batch_delete, name='asset-batch-delete'),
]
