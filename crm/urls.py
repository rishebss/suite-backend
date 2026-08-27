from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers
from crm.views import CRMViewSet, PipelineViewSet, StageViewSet

router = DefaultRouter()
router.register(r'pipelines', PipelineViewSet, basename='pipelines')
router.register(r'pipeline', CRMViewSet, basename='pipeline')

# Nested: /api/crm/pipelines/{pipeline_pk}/stages/
pipeline_router = nested_routers.NestedDefaultRouter(router, r'pipelines', lookup='pipeline')
pipeline_router.register(r'stages', StageViewSet, basename='pipeline-stages')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(pipeline_router.urls)),
]
