from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payments.views import PaymentViewSet, RecurringScheduleViewSet

router = DefaultRouter()
router.register(r"schedules", RecurringScheduleViewSet, basename="recurring-schedule")
router.register(r"", PaymentViewSet, basename="payment")

urlpatterns = [
    path("", include(router.urls)),
]
