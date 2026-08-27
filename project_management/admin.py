from django.contrib import admin
from project_management.models import (
    Workspace, Project, ProjectMember, Workflow,
    WorkItemStatus, WorkItem, WorkItemLink, WorkItemComment,
    WorkItemAttachment, WorkItemActivityLog, Sprint, SprintMember, Release
)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'organization', 'is_active', 'created_at']
    list_filter = ['is_active', 'organization']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'key', 'workspace', 'is_active', 'department', 'created_at']
    list_filter = ['is_active', 'workspace', 'department']
    search_fields = ['name', 'key', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'role', 'created_at']
    list_filter = ['role', 'project']
    search_fields = ['user__email', 'project__name']


class WorkItemStatusInline(admin.TabularInline):
    model = WorkItemStatus
    extra = 1
    fields = ['name', 'slug', 'order', 'color', 'category', 'is_start', 'is_end']


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'scope', 'is_default', 'created_at']
    list_filter = ['scope', 'is_default']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    inlines = [WorkItemStatusInline]
    filter_horizontal = ['projects']


@admin.register(WorkItemStatus)
class WorkItemStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'workflow', 'order', 'color', 'category', 'is_start', 'is_end']
    list_filter = ['category', 'workflow', 'color']
    search_fields = ['name', 'workflow__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ['key', 'title', 'project', 'issue_type', 'status', 'priority', 'assignee', 'due_date']
    list_filter = ['issue_type', 'priority', 'project', 'status']
    search_fields = ['key', 'title', 'description']
    readonly_fields = ['key', 'created_at', 'updated_at']
    raw_id_fields = ['assignee', 'reporter', 'parent']
    list_select_related = ['project', 'status', 'assignee']


@admin.register(WorkItemLink)
class WorkItemLinkAdmin(admin.ModelAdmin):
    list_display = ['source_item', 'relation_type', 'target_item', 'created_at']
    list_filter = ['relation_type']
    search_fields = ['source_item__key', 'target_item__key']


@admin.register(WorkItemAttachment)
class WorkItemAttachmentAdmin(admin.ModelAdmin):
    list_display = ['work_item', 'file_name', 'file_size', 'uploaded_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['file_name', 'work_item__key', 'note']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WorkItemComment)
class WorkItemCommentAdmin(admin.ModelAdmin):
    list_display = ['work_item', 'author', 'created_at']
    list_filter = ['created_at']
    search_fields = ['body', 'work_item__key', 'author__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WorkItemActivityLog)
class WorkItemActivityLogAdmin(admin.ModelAdmin):
    list_display = ['work_item', 'activity_type', 'user', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['description', 'work_item__key']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'status', 'start_date', 'end_date', 'total_committed_points', 'total_completed_points']
    list_filter = ['status', 'project']
    search_fields = ['name', 'goal', 'project__name']
    readonly_fields = ['total_committed_points', 'total_completed_points', 'completed_at', 'created_at', 'updated_at']


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'version', 'status', 'release_date', 'is_archived']
    list_filter = ['status', 'is_archived', 'project']
    search_fields = ['name', 'description', 'version']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SprintMember)
class SprintMemberAdmin(admin.ModelAdmin):
    list_display = ['sprint', 'user', 'capacity_hours']
    list_filter = ['sprint__project']
    search_fields = ['user__email', 'sprint__name']
