from rest_framework import permissions
from project_management.models import Project, ProjectMember


class IsOrgAdmin(permissions.BasePermission):
    """Superadmin/Admin — full access across all workspaces and projects."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )


class IsWorkspaceAdmin(permissions.BasePermission):
    """Can manage workspace-level settings (projects, members, workflows)."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class IsProjectAdminOrEditor(permissions.BasePermission):
    """Project Admin or Editor — can create/update work items, manage members."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Superadmin/Admin bypass project-level checks
        if request.user.role in ['Superadmin', 'Admin']:
            return True

        project_id = self._get_project_id(obj)
        if not project_id:
            return False

        return self._has_project_role(request.user, project_id, ['ADMIN', 'EDITOR'])

    def _get_project_id(self, obj):
        if isinstance(obj, Project):
            return obj.id
        if hasattr(obj, 'project_id'):
            return obj.project_id
        if hasattr(obj, 'project'):
            return obj.project.id if obj.project else None
        return None

    def _has_project_role(self, user, project_id, roles):
        return ProjectMember.objects.filter(
            project_id=project_id, user=user, role__in=roles
        ).exists()


class IsProjectMember(permissions.BasePermission):
    """Any project member — can view and comment."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.role in ['Superadmin', 'Admin']:
            return True

        project_id = self._get_project_id(obj)
        if not project_id:
            return False

        # Allow if user is a member of the project OR the workspace org
        return ProjectMember.objects.filter(
            project_id=project_id, user=request.user
        ).exists()

    def _get_project_id(self, obj):
        if isinstance(obj, Project):
            return obj.id
        if hasattr(obj, 'project_id'):
            return obj.project_id
        if hasattr(obj, 'project'):
            return obj.project.id if obj.project else None
        return None


class IsProjectViewer(permissions.BasePermission):
    """Viewer or higher — read-only access or better."""
    def has_permission(self, request, view):
        if request.method not in permissions.SAFE_METHODS:
            return self._is_admin_or_editor(request)
        return bool(request.user and request.user.is_authenticated)

    def _is_admin_or_editor(self, request):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin', 'Manager']
        )


class CanManageWorkflows(permissions.BasePermission):
    """Admin/Superadmin can manage workflow configurations."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ['Superadmin', 'Admin']
        )
