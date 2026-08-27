"""
User Management API Views and ViewSets
"""

from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.utils import timezone

from authentication.models import User, AuditLog, Department
from authentication.serializers import (
    UserDetailSerializer,
    UserListSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    AuditLogSerializer,
    UserActivitySerializer,
    AssignableUserSerializer,
)
from authentication.permissions import (
    IsUserAdmin,
    IsSuperAdmin,
    CanViewOwnAuditLog,
    IsAdminOrReadOnly,
)
from authentication.audit_logger import (
    log_user_create,
    log_user_update,
    log_user_delete,
    log_user_activate,
    log_user_role_change,
    log_user_department_change,
)
from authentication.rate_limit import get_client_ip, get_user_agent


class UserPagination(PageNumberPagination):
    """Custom pagination for user list"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management (CRUD operations)

    Endpoints:
    - GET /api/users/ - List users with filtering
    - POST /api/users/ - Create new user
    - GET /api/users/{id}/ - Get user details
    - PATCH /api/users/{id}/ - Update user
    - DELETE /api/users/{id}/ - Soft delete user (deactivate)
    - GET /api/users/{id}/activities/ - Get user's audit log
    - PATCH /api/users/bulk-update/ - Bulk update users
    """

    queryset = User.objects.prefetch_related("departments").all()
    pagination_class = UserPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["email", "first_name", "last_name", "account_id", "mobile"]
    ordering_fields = ["created_at", "email", "first_name", "last_login"]
    ordering = ["-created_at"]

    permission_classes = [IsUserAdmin]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return UserCreateSerializer
        elif self.action == "update" or self.action == "partial_update":
            return UserUpdateSerializer
        elif self.action == "list":
            return UserListSerializer
        else:  # retrieve and default
            return UserDetailSerializer

    def get_queryset(self):
        """Filter users based on permissions and query params"""
        queryset = User.objects.prefetch_related("departments").all()

        # Superadmin sees all users
        if self.request.user.role == "Superadmin":
            pass  # No filter
        # Admin sees users in their organization only
        elif self.request.user.role == "Admin":
            queryset = queryset.filter(
                Q(organization=self.request.user.organization)
                | Q(role="Superadmin")  # Can always see superadmin
            )

        # Manual filtering for role, is_active, is_email_verified
        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        is_email_verified = self.request.query_params.get("is_email_verified")
        if is_email_verified is not None:
            queryset = queryset.filter(
                is_email_verified=is_email_verified.lower() == "true"
            )

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a new user with audit logging"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Log user creation
        log_user_create(
            request.user, user, get_client_ip(request), get_user_agent(request)
        )

        return Response(
            {
                "success": True,
                "message": "User created successfully",
                "data": UserDetailSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """Update user with audit logging"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        print("=== UPDATE USER ===")
        print("Request data:", request.data)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        print("Serializer validated data:", serializer.validated_data)

        # Serializer already tracks changes in context
        user = serializer.save()

        # Get changes from serializer context
        changes = serializer.context.get("changes", {})

        print("UserDetailSerializer data:", UserDetailSerializer(user).data)

        # Log user update
        if changes:
            log_user_update(
                request.user,
                user,
                changes,
                get_client_ip(request),
                get_user_agent(request),
            )

        return Response(
            {
                "success": True,
                "message": "User updated successfully",
                "data": UserDetailSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        """Permanently delete user from database"""
        try:
            instance = self.get_object()
            print(f"Deleting user: {instance.email} (ID: {instance.id})")

            # Log user deletion before deleting
            log_user_delete(
                request.user,
                instance.email,
                get_client_ip(request),
                get_user_agent(request),
            )

            # Permanently delete the user
            instance.delete()

            print("User deleted successfully!")
            return Response(
                {"success": True, "message": "User deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            print(f"ERROR deleting user: {str(e)}")
            import traceback

            traceback.print_exc()
            return Response(
                {"success": False, "message": f"Error deleting user: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["GET"], permission_classes=[CanViewOwnAuditLog])
    def activities(self, request, pk=None):
        """Get user's activity/audit log"""
        user = self.get_object()
        self.check_object_permissions(request, user)

        # Get filters from query params
        action_type = request.query_params.get("action")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        # Filter audit logs for this user
        queryset = AuditLog.objects.filter(
            Q(user=user) | Q(action_target=user)
        ).order_by("-created_at")

        if action_type:
            queryset = queryset.filter(action=action_type)

        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = AuditLogSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["PATCH"], permission_classes=[IsUserAdmin])
    def bulk_update(self, request):
        """Bulk update users"""
        user_ids = request.data.get("user_ids", [])
        updates = request.data.get("updates", {})

        if not user_ids or not isinstance(user_ids, list):
            return Response(
                {"success": False, "message": "user_ids must be provided as a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not updates:
            return Response(
                {"success": False, "message": "updates must be provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get users
        queryset = self.get_queryset()
        users = queryset.filter(id__in=user_ids)

        updated_users = []
        for user in users:
            for field, value in updates.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            user.save()
            updated_users.append(user)

            # Log each update
            log_user_update(
                request.user,
                user,
                updates,
                get_client_ip(request),
                get_user_agent(request),
            )

        return Response(
            {
                "success": True,
                "message": f"{len(updated_users)} users updated successfully",
                "updated_count": len(updated_users),
                "updated_users": UserListSerializer(updated_users, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([IsUserAdmin])
def bulk_delete_users(request):
    """Bulk delete users"""
    print("=== BULK DELETE ===")
    print("Request data:", request.data)
    user_ids = request.data.get("user_ids", [])
    print("User IDs to delete:", user_ids)

    if not user_ids or not isinstance(user_ids, list):
        print("Validation failed: user_ids invalid")
        return Response(
            {"success": False, "message": "user_ids must be provided as a list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get users
    user = request.user
    queryset = User.objects.all()
    if user.role == "Superadmin":
        pass
    elif user.role == "Admin":
        queryset = queryset.filter(organization=user.organization)
    else:
        queryset = queryset.none()

    users = queryset.filter(id__in=user_ids)
    print("Found users to delete:", users.count())

    deleted_count = users.count()
    users.delete()

    print(f"Bulk delete complete: {deleted_count} users deleted")
    return Response(
        {
            "success": True,
            "message": f"{deleted_count} users deleted successfully",
            "deleted_count": deleted_count,
        },
        status=status.HTTP_200_OK,
    )


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs

    Endpoints:
    - GET /api/activities/ - List all activities with filtering
    - GET /api/activities/{id}/ - Get specific activity details
    """

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    pagination_class = UserPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__email", "action_target__email", "ip_address"]
    ordering_fields = ["created_at", "action", "status"]
    ordering = ["-created_at"]

    permission_classes = [IsUserAdmin]  # Only admins can view all activities

    def get_queryset(self):
        """Filter activities based on permissions"""
        queryset = AuditLog.objects.all()

        # Superadmin sees all activities
        if self.request.user.role == "Superadmin":
            pass  # No filter
        # Admin sees activities related to users in their organization
        elif self.request.user.role == "Admin":
            queryset = queryset.filter(
                Q(user__organization=self.request.user.organization)
                | Q(action_target__organization=self.request.user.organization)
                | Q(user__role="Superadmin")
                | Q(action_target__role="Superadmin")
            )

        # Manual filtering for action, status, user, action_target
        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        user = self.request.query_params.get("user")
        if user:
            queryset = queryset.filter(user_id=user)

        action_target = self.request.query_params.get("action_target")
        if action_target:
            queryset = queryset.filter(action_target_id=action_target)

        return queryset

    def list(self, request, *args, **kwargs):
        """List activities with enhanced response"""
        response = super().list(request, *args, **kwargs)

        # Enhance response
        if isinstance(response.data, dict) and "results" in response.data:
            response.data = {
                "success": True,
                "count": response.data.get("count"),
                "next": response.data.get("next"),
                "previous": response.data.get("previous"),
                "results": response.data.get("results"),
            }

        return response

    def retrieve(self, request, *args, **kwargs):
        """Get specific activity with enhanced response"""
        response = super().retrieve(request, *args, **kwargs)
        response.data = {"success": True, "data": response.data}
        return response


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing departments

    Endpoints:
    - GET /api/departments/ - List all departments
    - POST /api/departments/ - Create new department
    - GET /api/departments/{id}/ - Get department details
    - PATCH /api/departments/{id}/ - Update department
    - DELETE /api/departments/{id}/ - Delete department
    """

    queryset = Department.objects.prefetch_related("users").all()
    pagination_class = UserPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        from authentication.serializers import DepartmentSerializer

        return DepartmentSerializer

    def list(self, request, *args, **kwargs):
        """List departments with enhanced response"""
        response = super().list(request, *args, **kwargs)
        if isinstance(response.data, dict) and "results" in response.data:
            response.data = {
                "success": True,
                "count": response.data.get("count"),
                "next": response.data.get("next"),
                "previous": response.data.get("previous"),
                "results": response.data.get("results"),
            }
        return response

    def retrieve(self, request, *args, **kwargs):
        """Get department details with enhanced response"""
        response = super().retrieve(request, *args, **kwargs)
        response.data = {"success": True, "data": response.data}
        return response

    def create(self, request, *args, **kwargs):
        """Create a new department"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department = serializer.save()
        return Response(
            {
                "success": True,
                "message": "Department created successfully",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """Update department"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        department = serializer.save()
        return Response(
            {
                "success": True,
                "message": "Department updated successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        """Delete department"""
        instance = self.get_object()
        instance.delete()
        return Response(
            {"success": True, "message": "Department deleted successfully"},
            status=status.HTTP_200_OK,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def assignable_users(request):
    """Return a minimal list of active users for assignment dropdowns."""
    users = User.objects.filter(is_active=True).order_by("first_name", "email")
    serializer = AssignableUserSerializer(users, many=True)
    return Response(serializer.data)
