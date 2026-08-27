from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CalendarTodoViewSet

router = DefaultRouter()
router.register(r"todos", CalendarTodoViewSet, basename="todo")

urlpatterns = [
    path("", include(router.urls)),
]
