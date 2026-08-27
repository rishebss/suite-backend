"""
URL Configuration for Menu Management System

Mounted at: /api/ (via core/urls.py: path('api/', include('menus.urls')))
Endpoints:
  - /api/menus/
  - /api/menus/{id}/
  - /api/menus/my-menus/
  - /api/products/
  - /api/organizations/
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from menus.views import MenuViewSet, ProductViewSet, OrganizationViewSet

app_name = 'menus'

# Use DefaultRouter for ViewSets to auto-generate CRUD endpoints
router = DefaultRouter()
router.register(r'menus', MenuViewSet, basename='menu')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'organizations', OrganizationViewSet, basename='organization')

urlpatterns = router.urls
