from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework import serializers
from django.contrib.auth import get_user_model
from project_management.models import (
    Workspace, Project, ProjectMember, Workflow, WorkItemStatus, WorkItem,
    WorkItemLink, WorkItemComment, WorkItemAttachment, WorkItemActivityLog,
    Sprint, SprintMember, Release, SLAPolicy, CSATResponse, Milestone,
    Objective, KeyResult, AutomationRule,
    Notification, NotificationPreference, WebhookConfig,
    CustomFieldDefinition, ProjectFieldVisibility,
    RecurringTaskConfig, ApprovalWorkflow, ApprovalStep,
    ApprovalRequest, ApprovalAction, CannedResponse,
    ProjectTemplate, GitHubIntegration, GitHubLink, PriorityRule,
    WorkItemTimeLog, WebhookDeliveryLog, TransitionRule,
    SavedFilter, WorkItemTemplate,
)

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'avatar']
        read_only_fields = fields


class WorkspaceSerializer(serializers.ModelSerializer):
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'slug', 'description', 'organization',
            'icon', 'is_active', 'project_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_project_count(self, obj):
        return obj.projects.count()

    def validate_slug(self, value):
        from django.utils.text import slugify
        slug = slugify(value)
        if not slug:
            raise serializers.ValidationError("Invalid slug")
        return slug


class WorkItemStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkItemStatus
        fields = [
            'id', 'workflow', 'name', 'slug', 'order', 'color',
            'category', 'is_start', 'is_end',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkflowSerializer(serializers.ModelSerializer):
    statuses = WorkItemStatusSerializer(many=True, read_only=True)

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'slug', 'scope', 'description',
            'projects', 'is_default', 'statuses',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectMemberSerializer(serializers.ModelSerializer):
    user_details = UserBriefSerializer(source='user', read_only=True)

    class Meta:
        model = ProjectMember
        fields = ['id', 'project', 'user', 'user_details', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    members = ProjectMemberSerializer(many=True, read_only=True)
    workflows = WorkflowSerializer(many=True, read_only=True)
    workspace_details = WorkspaceSerializer(source='workspace', read_only=True)
    parent_project_details = serializers.SerializerMethodField()
    work_item_summary = serializers.SerializerMethodField()
    workflow_preset = serializers.ChoiceField(
        choices=['scrum', 'kanban', 'sales_pipeline', 'support_ticket', 'ops_approval'],
        write_only=True, required=False,
        help_text="Auto-create workflow from preset on project creation",
    )

    class Meta:
        model = Project
        fields = [
            'id', 'workspace', 'workspace_details', 'name', 'key',
            'description', 'enabled_issue_types', 'department',
            'icon', 'color', 'is_active',
            'start_date', 'end_date',
            'parent_project', 'parent_project_details',
            'sync_department_members',
            'members', 'workflows',
            'workflow_preset',
            'work_item_summary',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_parent_project_details(self, obj):
        if obj.parent_project:
            return {
                'id': str(obj.parent_project.id),
                'name': obj.parent_project.name,
                'key': obj.parent_project.key,
            }
        return None

    def get_work_item_summary(self, obj):
        items = obj.work_items.all()
        return {
            'total': items.count(),
            'todo': items.filter(status__category='todo').count(),
            'in_progress': items.filter(status__category='in_progress').count(),
            'done': items.filter(status__category='done').count(),
        }

    def create(self, validated_data):
        validated_data.pop('workflow_preset', None)
        return super().create(validated_data)

    def validate_key(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Project key is required")
        return value.upper()


class ProjectListSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    work_item_summary = serializers.SerializerMethodField()
    parent_project_details = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'workspace', 'name', 'key', 'description',
            'enabled_issue_types', 'icon', 'color', 'is_active',
            'parent_project', 'parent_project_details',
            'member_count', 'work_item_summary',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_parent_project_details(self, obj):
        if obj.parent_project:
            return {'id': str(obj.parent_project.id), 'name': obj.parent_project.name, 'key': obj.parent_project.key}
        return None

    def get_member_count(self, obj):
        return getattr(obj, 'member_count_annotated', None) or obj.members.count()

    def get_work_item_summary(self, obj):
        if hasattr(obj, 'work_item_summary_annotated') and obj.work_item_summary_annotated:
            return obj.work_item_summary_annotated
        items = obj.work_items.all()
        return {
            'total': items.count(),
            'todo': items.filter(status__category='todo').count(),
            'in_progress': items.filter(status__category='in_progress').count(),
            'done': items.filter(status__category='done').count(),
        }


class WorkItemLinkSerializer(serializers.ModelSerializer):
    source_key = serializers.ReadOnlyField(source='source_item.key')
    target_key = serializers.ReadOnlyField(source='target_item.key')

    class Meta:
        model = WorkItemLink
        fields = ['id', 'source_item', 'source_key', 'target_item', 'target_key', 'relation_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        if data['source_item'] == data['target_item']:
            raise serializers.ValidationError("Cannot link an item to itself")
        return data


class WorkItemCommentSerializer(serializers.ModelSerializer):
    author_details = UserBriefSerializer(source='author', read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkItemComment
        fields = ['id', 'work_item', 'author', 'author_details', 'body', 'parent', 'reply_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_reply_count(self, obj):
        return obj.replies.count()


class WorkItemAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_details = UserBriefSerializer(source='uploaded_by', read_only=True)

    class Meta:
        model = WorkItemAttachment
        fields = [
            'id', 'work_item', 'file', 'file_name', 'file_size',
            'note', 'url', 'uploaded_by', 'uploaded_by_details',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkItemActivityLogSerializer(serializers.ModelSerializer):
    user_details = UserBriefSerializer(source='user', read_only=True)

    class Meta:
        model = WorkItemActivityLog
        fields = ['id', 'work_item', 'user', 'user_details', 'activity_type', 'description', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkItemSerializer(serializers.ModelSerializer):
    assignee_details = UserBriefSerializer(source='assignee', read_only=True)
    reporter_details = UserBriefSerializer(source='reporter', read_only=True)
    status_details = WorkItemStatusSerializer(source='status', read_only=True)
    subtask_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    epic_details = serializers.SerializerMethodField()
    sprint_details = serializers.SerializerMethodField()
    version_details = serializers.SerializerMethodField()
    sla_policy_details = serializers.SerializerMethodField()

    class Meta:
        model = WorkItem
        fields = [
            'id', 'project', 'parent', 'epic', 'epic_details', 'sprint', 'sprint_details',
            'key', 'issue_type', 'title', 'description',
            'status', 'status_details',
            'priority', 'epic_priority', 'order', 'story_points',
            'assignee', 'assignee_details',
            'reporter', 'reporter_details',
            'start_date', 'due_date', 'completed_at',
            'estimated_hours', 'actual_hours',
            'version', 'version_details',
            'custom_fields', 'labels',
            'linked_object_type', 'linked_object_id',
            # Phase 2.5: Ticketing
            'sla_policy', 'sla_policy_details', 'sla_status',
            'first_response_at', 'sla_response_due_at', 'sla_resolution_due_at',
            'requester_email', 'requester_name',
            'subtask_count', 'comment_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'key', 'created_at', 'updated_at']

    def get_subtask_count(self, obj):
        annotated = getattr(obj, 'subtask_count', None)
        if annotated is not None:
            return annotated
        return obj.subtasks.count()

    def get_comment_count(self, obj):
        annotated = getattr(obj, 'comment_count', None)
        if annotated is not None:
            return annotated
        return obj.comments.count()

    def get_epic_details(self, obj):
        if obj.epic:
            return {'id': str(obj.epic.id), 'key': obj.epic.key, 'title': obj.epic.title, 'epic_priority': obj.epic.epic_priority}
        return None

    def get_sprint_details(self, obj):
        if obj.sprint:
            return {'id': str(obj.sprint.id), 'name': obj.sprint.name, 'status': obj.sprint.status}
        return None

    def get_version_details(self, obj):
        if obj.version:
            return {'id': str(obj.version.id), 'name': obj.version.name, 'version': obj.version.version, 'status': obj.version.status}
        return None

    def get_sla_policy_details(self, obj):
        if obj.sla_policy:
            return {
                'id': str(obj.sla_policy.id),
                'name': obj.sla_policy.name,
                'response_time_minutes': obj.sla_policy.response_time_minutes,
                'resolution_time_minutes': obj.sla_policy.resolution_time_minutes,
            }
        return None


class WorkItemDetailSerializer(serializers.ModelSerializer):
    assignee_details = UserBriefSerializer(source='assignee', read_only=True)
    reporter_details = UserBriefSerializer(source='reporter', read_only=True)
    status_details = WorkItemStatusSerializer(source='status', read_only=True)
    subtasks = WorkItemSerializer(many=True, read_only=True)
    outgoing_links = WorkItemLinkSerializer(many=True, read_only=True)
    incoming_links = WorkItemLinkSerializer(many=True, read_only=True)
    comments = WorkItemCommentSerializer(many=True, read_only=True)
    attachments = WorkItemAttachmentSerializer(many=True, read_only=True)
    activity_logs = WorkItemActivityLogSerializer(many=True, read_only=True)
    epic_details = serializers.SerializerMethodField()
    sprint_details = serializers.SerializerMethodField()
    version_details = serializers.SerializerMethodField()
    sla_policy_details = serializers.SerializerMethodField()
    csat_responses = serializers.SerializerMethodField()

    class Meta:
        model = WorkItem
        fields = [
            'id', 'project', 'parent', 'epic', 'epic_details', 'sprint', 'sprint_details',
            'key', 'issue_type', 'title', 'description',
            'status', 'status_details',
            'priority', 'epic_priority', 'order', 'story_points',
            'assignee', 'assignee_details',
            'reporter', 'reporter_details',
            'start_date', 'due_date', 'completed_at',
            'estimated_hours', 'actual_hours',
            'version', 'version_details',
            'custom_fields', 'labels',
            'linked_object_type', 'linked_object_id',
            # Phase 2.5: Ticketing
            'sla_policy', 'sla_policy_details', 'sla_status',
            'first_response_at', 'sla_response_due_at', 'sla_resolution_due_at',
            'requester_email', 'requester_name',
            'csat_responses',
            'subtasks', 'outgoing_links', 'incoming_links',
            'comments', 'attachments', 'activity_logs',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'key', 'created_at', 'updated_at']

    def get_epic_details(self, obj):
        if obj.epic:
            return {'id': str(obj.epic.id), 'key': obj.epic.key, 'title': obj.epic.title, 'epic_priority': obj.epic.epic_priority}
        return None

    def get_sprint_details(self, obj):
        if obj.sprint:
            return {'id': str(obj.sprint.id), 'name': obj.sprint.name, 'status': obj.sprint.status}
        return None

    def get_version_details(self, obj):
        if obj.version:
            return {'id': str(obj.version.id), 'name': obj.version.name, 'version': obj.version.version, 'status': obj.version.status}
        return None

    def get_sla_policy_details(self, obj):
        if obj.sla_policy:
            return {
                'id': str(obj.sla_policy.id),
                'name': obj.sla_policy.name,
                'response_time_minutes': obj.sla_policy.response_time_minutes,
                'resolution_time_minutes': obj.sla_policy.resolution_time_minutes,
            }
        return None

    def get_csat_responses(self, obj):
        return CSATResponseSerializer(obj.csat_responses.all(), many=True).data


class SLAPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAPolicy
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CSATResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CSATResponse
        fields = ['id', 'work_item', 'rating', 'comment', 'responded_by', 'responded_at', 'created_at']
        read_only_fields = ['id', 'responded_at', 'created_at']


class SprintMemberSerializer(serializers.ModelSerializer):
    user_details = UserBriefSerializer(source='user', read_only=True)

    class Meta:
        model = SprintMember
        fields = ['id', 'sprint', 'user', 'user_details', 'capacity_hours', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SprintSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()

    class Meta:
        model = Sprint
        fields = [
            'id', 'project', 'name', 'goal', 'start_date', 'end_date', 'status',
            'total_capacity_hours', 'total_committed_points', 'total_completed_points',
            'retrospective_notes', 'completed_at',
            'member_count', 'item_count', 'total_points',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total_committed_points', 'total_completed_points', 'completed_at', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.members.count()

    def get_item_count(self, obj):
        return obj.work_items.count()

    def get_total_points(self, obj):
        return float(obj.work_items.aggregate(total=Sum('story_points'))['total'] or 0)


class SprintDetailSerializer(serializers.ModelSerializer):
    members = SprintMemberSerializer(many=True, read_only=True)
    work_items = WorkItemSerializer(many=True, read_only=True)
    project_details = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = Sprint
        fields = [
            'id', 'project', 'project_details', 'name', 'goal',
            'start_date', 'end_date', 'status',
            'total_capacity_hours', 'total_committed_points', 'total_completed_points',
            'retrospective_notes', 'completed_at',
            'members', 'work_items',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total_committed_points', 'total_completed_points', 'completed_at', 'created_at', 'updated_at']


class MilestoneSerializer(serializers.ModelSerializer):
    project_details = serializers.ReadOnlyField(source='project.name')
    sprint_details = serializers.ReadOnlyField(source='sprint.name')
    work_item_details = serializers.ReadOnlyField(source='work_item.key')

    class Meta:
        model = Milestone
        fields = [
            'id', 'project', 'project_details', 'sprint',
            'sprint_details', 'work_item', 'work_item_details',
            'name', 'description', 'milestone_type',
            'target_date', 'completed_date', 'status',
            'weight_pct', 'revenue_impact',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# Phase 3.2: OKR / Goal Tree
class KeyResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyResult
        fields = [
            'id', 'objective', 'title', 'description', 'kr_type',
            'start_value', 'target_value', 'current_value', 'progress_pct',
            'metric_work_item', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'progress_pct', 'created_at', 'updated_at']


class ObjectiveListSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    key_results_count = serializers.SerializerMethodField()
    avg_progress = serializers.SerializerMethodField()

    class Meta:
        model = Objective
        fields = [
            'id', 'workspace', 'project', 'title', 'description',
            'alignment', 'status', 'owner', 'owner_name',
            'parent_objective', 'start_date', 'end_date', 'weight',
            'key_results_count', 'avg_progress',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_owner_name(self, obj):
        return obj.owner.get_full_name() if obj.owner else None

    def get_key_results_count(self, obj):
        return obj.key_results.count()

    def get_avg_progress(self, obj):
        krs = obj.key_results.values_list('progress_pct', flat=True)
        if krs:
            return round(sum(krs) / len(krs), 1)
        return 0.0


class ObjectiveDetailSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    key_results = KeyResultSerializer(many=True, read_only=True)
    child_objectives = ObjectiveListSerializer(many=True, read_only=True)
    work_item_details = serializers.ReadOnlyField(source='work_items.count')
    milestone_details = serializers.ReadOnlyField(source='milestones.count')

    class Meta:
        model = Objective
        fields = [
            'id', 'workspace', 'project', 'title', 'description',
            'alignment', 'status', 'owner', 'owner_name',
            'parent_objective', 'start_date', 'end_date', 'weight',
            'key_results', 'child_objectives',
            'work_items', 'work_item_details',
            'milestones', 'milestone_details',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_owner_name(self, obj):
        return obj.owner.get_full_name() if obj.owner else None


# Phase 4.3: Field-Level Visibility
class ProjectFieldVisibilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFieldVisibility
        fields = [
            'id', 'project', 'role', 'visible_fields', 'hidden_fields',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# Phase 3.4: Automation Rule
class AutomationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRule
        fields = [
            'id', 'project', 'name', 'description', 'is_enabled',
            'trigger_event', 'conditions', 'action_type', 'action_config',
            'issue_type_filter', 'priority',
            'run_count', 'last_run_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'run_count', 'last_run_at', 'created_at', 'updated_at']


# Phase 3.5: Notifications & Webhooks
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'notification_type', 'title', 'message',
            'is_read', 'read_at',
            'work_item', 'project',
            'metadata', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'read_at', 'created_at', 'updated_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'project', 'notification_type', 'channel', 'enabled',
            'digest_enabled', 'digest_frequency',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WebhookConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookConfig
        fields = [
            'id', 'project', 'provider', 'name', 'webhook_url', 'secret',
            'is_enabled', 'events',
            'last_sent_at', 'failure_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_sent_at', 'failure_count', 'created_at', 'updated_at']


# Phase 1: Release / Version
class ReleaseSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Release
        fields = [
            'id', 'project', 'name', 'description', 'version',
            'status', 'release_date', 'is_archived',
            'item_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_item_count(self, obj):
        return obj.work_items.count()


# ── Recurring Task Config ────────────────────────────────────────────────────
class RecurringTaskConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringTaskConfig
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'occurrences_created']


# ── Approval Workflows ───────────────────────────────────────────────────────
class ApprovalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalStep
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    steps = ApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalWorkflow
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ApprovalActionSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalAction
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None


class ApprovalRequestSerializer(serializers.ModelSerializer):
    actions = ApprovalActionSerializer(many=True, read_only=True)
    actions_count = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'completed_at']

    def get_actions_count(self, obj):
        return obj.actions.count()


# ── Canned Responses ─────────────────────────────────────────────────────────
class CannedResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CannedResponse
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Project Templates ────────────────────────────────────────────────────────
class ProjectTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTemplate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── GitHub Integration ───────────────────────────────────────────────────────
class GitHubIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubIntegration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class GitHubLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubLink
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Priority Rules ───────────────────────────────────────────────────────────
class PriorityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorityRule
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Transition Rules ──────────────────────────────────────────────────────────
class TransitionRuleSerializer(serializers.ModelSerializer):
    from_status_name = serializers.CharField(source='from_status.name', read_only=True)
    to_status_name = serializers.CharField(source='to_status.name', read_only=True)
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)

    class Meta:
        model = TransitionRule
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Webhook Delivery Logs ─────────────────────────────────────────────────────
class WebhookDeliveryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDeliveryLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# ── Time Logs ─────────────────────────────────────────────────────────────────
class WorkItemTimeLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkItemTimeLog
        fields = ['id', 'work_item', 'user', 'user_name', 'hours', 'description', 'date', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username if obj.user else None


# Phase 3.6: Custom Fields
class CustomFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomFieldDefinition
        fields = [
            'id', 'project', 'issue_type_filter', 'field_key', 'label',
            'field_type', 'is_required', 'is_active', 'options',
            'placeholder', 'default_value', 'order',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SavedFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedFilter
        fields = [
            'id', 'user', 'name', 'scope', 'workspace', 'project',
            'filter_data', 'column_config', 'is_default',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class WorkItemTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkItemTemplate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
