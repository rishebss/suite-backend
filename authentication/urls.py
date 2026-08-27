from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView
from . import views
from .usermanagement_views import (
    UserViewSet,
    AuditLogViewSet,
    DepartmentViewSet,
    bulk_delete_users,
    assignable_users,
)

app_name = "authentication"

# Create router for viewsets
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"activities", AuditLogViewSet, basename="activity")
router.register(r"departments", DepartmentViewSet, basename="department")

urlpatterns = [
    # Bulk delete users
    path("users/bulk-delete", bulk_delete_users, name="bulk-delete-users"),
    # Assignable users for dropdowns (any authenticated user)
    path("users/assignable/", assignable_users, name="assignable-users"),
    # Router URLs for viewsets
    path("", include(router.urls)),
    # Session-based Auth (for backward compatibility with web frontend)
    path("register/", views.register_user, name="register"),
    path("login/", views.login_user, name="login"),
    path("logout/", views.logout_user, name="logout"),
    path("profile/", views.get_user_profile, name="profile"),
    path("profile/update/", views.update_user_profile, name="profile-update"),
    path("change-password/", views.change_password, name="change-password"),
    path("verify-password/", views.verify_password, name="verify-password"),
    # JWT Token Auth (for mobile and advanced clients)
    path("token/", views.CustomTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path(
        "token/refresh/", views.CustomTokenRefreshView.as_view(), name="token-refresh"
    ),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token-blacklist"),
    # Email Verification & Password Reset
    path(
        "send-verification-email/",
        views.send_verification_email_view,
        name="send-verification-email",
    ),
    path("verify-email/", views.verify_email_view, name="verify-email"),
    path("forgot-password/", views.forgot_password_view, name="forgot-password"),
    path("reset-password/", views.reset_password_view, name="reset-password"),
]
