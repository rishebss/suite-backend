from django.urls import path, include
from rest_framework.routers import DefaultRouter
from contacts.views import ContactViewSet, ImportBatchViewSet, ContactLogViewSet, ContactRemarkViewSet, ContactDocumentViewSet

router = DefaultRouter()
router.register(r'batches', ImportBatchViewSet, basename='importbatch')
router.register(r'logs', ContactLogViewSet, basename='contactlog')
router.register(r'remarks', ContactRemarkViewSet, basename='contactremark')
router.register(r'documents', ContactDocumentViewSet, basename='contactdocument')
router.register(r'', ContactViewSet, basename='contact')

urlpatterns = [
    path('', include(router.urls)),
]
