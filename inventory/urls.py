from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.views import (
    ItemCategoryViewSet, UnitViewSet, BrandViewSet,
    InventoryItemViewSet, CustomFieldDefinitionViewSet,
    LocationTypeViewSet, LocationViewSet,
    StockLedgerViewSet, StockLedgerEntryView, StockAvailabilityViewSet,
    TransferViewSet,
)

router = DefaultRouter()
router.register(r'categories', ItemCategoryViewSet, basename='item-categories')
router.register(r'units', UnitViewSet, basename='units')
router.register(r'brands', BrandViewSet, basename='brands')
router.register(r'items', InventoryItemViewSet, basename='inventory-items')
router.register(r'custom-fields', CustomFieldDefinitionViewSet, basename='custom-fields')
router.register(r'location-types', LocationTypeViewSet, basename='location-types')
router.register(r'locations', LocationViewSet, basename='locations')
router.register(r'transfers', TransferViewSet, basename='transfers')
router.register(r'stock/ledger', StockLedgerViewSet, basename='stock-ledger')
router.register(r'stock/availability', StockAvailabilityViewSet, basename='stock-availability')

urlpatterns = [
    path('', include(router.urls)),
    path('stock/ledger/entries/', StockLedgerEntryView.as_view({'post': 'create'}), name='stock-ledger-entry'),
]
