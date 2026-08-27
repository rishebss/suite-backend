import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import Main

# ============================================================================
# CONSTANTS
# ============================================================================

ISSUE_TYPE_CHOICES = (
    ('EPIC', 'Epic'),
    ('STORY', 'Story'),
    ('TASK', 'Task'),
    ('BUG', 'Bug'),
    ('SUBTASK', 'Sub-task'),
    ('DEAL', 'Deal'),
    ('TICKET', 'Ticket'),
    ('REQUEST', 'Request'),
    ('APPROVAL', 'Approval'),
    ('MILESTONE', 'Milestone'),
)

PRIORITY_CHOICES = (
    ('CRITICAL', 'Critical'),
    ('HIGH', 'High'),
    ('MEDIUM', 'Medium'),
    ('LOW', 'Low'),
)

EPIC_PRIORITY_CHOICES = (
    ('CRITICAL', 'Critical'),
    ('HIGH', 'High'),
    ('MEDIUM', 'Medium'),
    ('LOW', 'Low'),
    ('NONE', 'None'),
)

RELEASE_STATUS_CHOICES = (
    ('PLANNED', 'Planned'),
    ('IN_PROGRESS', 'In Progress'),
    ('RELEASED', 'Released'),
    ('CANCELLED', 'Cancelled'),
)

PROJECT_ROLE_CHOICES = (
    ('ADMIN', 'Admin'),
    ('EDITOR', 'Editor'),
    ('MEMBER', 'Member'),
    ('VIEWER', 'Viewer'),
)

WORKFLOW_SCOPE_CHOICES = (
    ('dev_scrum', 'Dev — Scrum'),
    ('dev_kanban', 'Dev — Kanban'),
    ('sales_deal', 'Sales — Deal Pipeline'),
    ('support_ticket', 'Support — Ticket'),
    ('ops_approval', 'Ops — Approval'),
    ('custom', 'Custom'),
)

WORKITEM_LINK_RELATION_CHOICES = (
    ('blocks', 'Blocks'),
    ('blocked_by', 'Blocked By'),
    ('relates_to', 'Relates To'),
    ('duplicates', 'Duplicates'),
    ('duplicated_by', 'Duplicated By'),
    ('converted_from', 'Converted From'),
    ('converted_to', 'Converted To'),
    ('parent', 'Parent'),
    ('child', 'Child'),
)

ACTIVITY_TYPE_CHOICES = (
    ('ITEM_CREATED', 'Item Created'),
    ('ITEM_UPDATED', 'Item Updated'),
    ('STATUS_CHANGED', 'Status Changed'),
    ('ASSIGNEE_CHANGED', 'Assignee Changed'),
    ('PRIORITY_CHANGED', 'Priority Changed'),
    ('COMMENT_ADDED', 'Comment Added'),
    ('ATTACHMENT_ADDED', 'Attachment Added'),
    ('LINK_ADDED', 'Link Added'),
    ('LINK_REMOVED', 'Link Removed'),
    ('SPRINT_STARTED', 'Sprint Started'),
    ('SPRINT_CLOSED', 'Sprint Closed'),
    ('SPRINT_UPDATED', 'Sprint Updated'),
    # Phase 2.5: Ticketing Mode
    ('SLA_BREACHED', 'SLA Breached'),
    ('SLA_WARNING', 'SLA Warning'),
    ('SLA_RESET', 'SLA Reset'),
    ('TICKET_ASSIGNED', 'Ticket Assigned'),
    ('CUSTOMER_RESPONDED', 'Customer Responded'),
    ('CSAT_SUBMITTED', 'CSAT Submitted'),
    # Phase 3: Cross-Cutting
    ('MILESTONE_ACHIEVED', 'Milestone Achieved'),
    ('MILESTONE_MISSED', 'Milestone Missed'),
    # Phase 4.4: Extended audit
    ('SPRINT_CHANGED', 'Sprint Changed'),
    ('TITLE_CHANGED', 'Title Changed'),
    ('DESCRIPTION_CHANGED', 'Description Changed'),
    ('DUE_DATE_CHANGED', 'Due Date Changed'),
    ('STORY_POINTS_CHANGED', 'Story Points Changed'),
    ('FIELD_UPDATED', 'Field Updated'),
)

SPRINT_STATUS_CHOICES = (
    ('PLANNING', 'Planning'),
    ('ACTIVE', 'Active'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
)

SLA_STATUS_CHOICES = (
    ('WITHIN_SLA', 'Within SLA'),
    ('WARNING', 'Warning — approaching breach'),
    ('BREACHED', 'Breached'),
    ('PAUSED', 'Paused — waiting on customer'),
)


# ============================================================================
# WORKSPACE
# ============================================================================

class Workspace(Main):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        'menus.Organization', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='workspaces'
    )
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji or icon name")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Workspace'
        verbose_name_plural = 'Workspaces'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['organization']),
        ]

    def __str__(self):
        return self.name


# ============================================================================
# PROJECT
# ============================================================================

class Project(Main):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name='projects'
    )
    name = models.CharField(max_length=255)
    key = models.CharField(
        max_length=10, db_index=True,
        help_text="Short prefix for work item keys, e.g., 'SK' for Smart Klub → SK-142"
    )
    description = models.TextField(blank=True)
    enabled_issue_types = models.JSONField(
        default=list, blank=True,
        help_text="List of issue types enabled: ['TASK', 'BUG', 'STORY', 'EPIC', ...]"
    )
    department = models.ForeignKey(
        'authentication.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='projects'
    )
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=20, default='blue')
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Hierarchy & Team
    parent_project = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sub_projects',
        help_text="Parent project for hierarchy (e.g., Programme → Project → Initiative)"
    )
    sync_department_members = models.BooleanField(
        default=False,
        help_text="Auto-sync members from the linked HR department"
    )

    # Sprint defaults
    sprint_duration_days = models.IntegerField(default=14)
    sprint_capacity_hours = models.IntegerField(
        default=40, help_text="Default capacity per team member per sprint (hours)"
    )

    class Meta:
        ordering = ['workspace__name', 'name']
        unique_together = ('workspace', 'key')
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        indexes = [
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['key']),
        ]

    def __str__(self):
        return f"{self.workspace.name} / {self.name}"

    def save(self, *args, **kwargs):
        self.key = self.key.upper()
        super().save(*args, **kwargs)


# ============================================================================
# PROJECT MEMBER
# ============================================================================

class ProjectMember(Main):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='project_memberships'
    )
    role = models.CharField(max_length=20, choices=PROJECT_ROLE_CHOICES, default='MEMBER')

    class Meta:
        unique_together = ('project', 'user')
        verbose_name = 'Project Member'
        verbose_name_plural = 'Project Members'
        indexes = [
            models.Index(fields=['project', 'role']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.project.name} ({self.get_role_display()})"


# ============================================================================
# WORKFLOW
# ============================================================================

class Workflow(Main):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    scope = models.CharField(
        max_length=20, choices=WORKFLOW_SCOPE_CHOICES, default='custom'
    )
    description = models.TextField(blank=True)
    projects = models.ManyToManyField(
        Project, blank=True, related_name='workflows'
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Auto-assign this workflow to new projects of matching scope"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Workflow'
        verbose_name_plural = 'Workflows'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['scope']),
        ]

    def __str__(self):
        return self.name


# ============================================================================
# WORK ITEM STATUS
# ============================================================================

class WorkItemStatus(Main):
    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name='statuses'
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    color = models.CharField(
        max_length=20, default='gray',
        help_text="CSS color name/hex for UI rendering"
    )
    category = models.CharField(
        max_length=20, default='todo',
        choices=[
            ('backlog', 'Backlog'),
            ('todo', 'To Do'),
            ('in_progress', 'In Progress'),
            ('review', 'Review'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ]
    )
    is_start = models.BooleanField(default=False, help_text="Initial status for new items")
    is_end = models.BooleanField(default=False, help_text="Final/completion status")

    class Meta:
        ordering = ['workflow', 'order']
        unique_together = ('workflow', 'slug')
        verbose_name = 'Work Item Status'
        verbose_name_plural = 'Work Item Statuses'
        indexes = [
            models.Index(fields=['workflow', 'order']),
        ]

    def __str__(self):
        return f"{self.workflow.name} → {self.name}"


# ============================================================================
# SPRINT — Phase 1: Dev Mode
# ============================================================================

class Sprint(Main):
    """Time-boxed iteration (Sprint/Cycle) for Scrum mode."""
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='sprints'
    )
    name = models.CharField(max_length=200)
    goal = models.TextField(blank=True, help_text="Sprint goal statement")

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    status = models.CharField(
        max_length=20, choices=SPRINT_STATUS_CHOICES, default='PLANNING'
    )

    # Capacity planning
    total_capacity_hours = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Total team capacity in hours for this sprint"
    )
    total_committed_points = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Total story points committed for this sprint"
    )
    total_completed_points = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Total story points completed at sprint end"
    )

    # Retrospective
    retrospective_notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Sprint'
        verbose_name_plural = 'Sprints'
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'start_date']),
        ]

    def __str__(self):
        return f"{self.project.key} — {self.name} ({self.get_status_display()})"

    @property
    def is_active(self):
        return self.status == 'ACTIVE'

    @property
    def duration_days(self):
        delta = self.end_date - self.start_date
        return delta.days


# ============================================================================
# SPRINT MEMBER — Per-sprint capacity for each team member
# ============================================================================

class SprintMember(Main):
    """Individual team member capacity for a specific sprint."""
    sprint = models.ForeignKey(
        Sprint, on_delete=models.CASCADE, related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sprint_memberships'
    )
    capacity_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=40,
        help_text="Available hours for this sprint"
    )

    class Meta:
        unique_together = ('sprint', 'user')
        verbose_name = 'Sprint Member'
        verbose_name_plural = 'Sprint Members'

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.sprint.name} ({self.capacity_hours}h)"


# ============================================================================
# RELEASE / VERSION — Phase 1: Dev Mode
# ============================================================================

class Release(Main):
    """A named release/version that work items can be tagged to."""
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='releases'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(
        max_length=50, blank=True,
        help_text="Semantic version string, e.g., '1.2.3'"
    )
    status = models.CharField(
        max_length=20, choices=RELEASE_STATUS_CHOICES, default='PLANNED'
    )
    release_date = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-release_date', 'name']
        unique_together = ('project', 'name')
        verbose_name = 'Release'
        verbose_name_plural = 'Releases'
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'is_archived']),
        ]

    def __str__(self):
        return f"{self.project.key} — {self.name}"


# ============================================================================
# SLA POLICY — Phase 2.5: Ticketing Mode
# ============================================================================

class SLAPolicy(Main):
    """Defines SLA targets for support tickets — response time, resolution time, escalation."""
    name = models.CharField(max_length=100)
    project = models.ForeignKey(
        'Project', on_delete=models.CASCADE, related_name='sla_policies',
        null=True, blank=True
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM',
        help_text="Which priority this SLA applies to"
    )
    response_time_minutes = models.PositiveIntegerField(
        default=60, help_text="Target first response time in minutes"
    )
    resolution_time_minutes = models.PositiveIntegerField(
        default=1440, help_text="Target resolution time in minutes (default 24h)"
    )
    business_hours_only = models.BooleanField(
        default=True, help_text="Only count time during business hours"
    )
    business_hours = models.JSONField(
        default=dict, blank=True,
        help_text="Business hours config: { 'timezone': 'Asia/Kolkata', 'days': {'mon': ['09:00','18:00'], ...} }"
    )
    escalation_rules = models.JSONField(
        default=list, blank=True,
        help_text="List of escalation rules: [{ 'after_minutes': 120, 'notify_role': 'Manager', 'action': 'reassign' }]"
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        verbose_name = 'SLA Policy'
        verbose_name_plural = 'SLA Policies'

    def __str__(self):
        return f"{self.name} (R:{self.response_time_minutes}m / S:{self.resolution_time_minutes}m)"


# ============================================================================
# WORK ITEM — The Universal Entity ✦ (Extended for Phase 1 Dev Mode, Phase 2.5 Ticketing)
# ============================================================================

class WorkItem(Main):
    """The universal work entity — every ticket, task, story, bug, deal, or request.
    Phase 0: 12 core fields. Phase 1: +Epic, Sprint, Story Points, Timestamps, Watchers.
    Phase 2.5: +SLA policy, SLA timers, first response tracking.
    """
    # ── Hierarchy ──────────────────────────────────────────────────────────
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='work_items'
    )
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subtasks'
    )
    # Phase 1: Epic relationship (self-referential FK for Epic → Story/Task hierarchy)
    epic = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='child_items',
        help_text="Parent Epic that this item belongs to (issue_type=EPIC)"
    )

    # ── Sprint (Phase 1) ────────────────────────────────────────────────────
    sprint = models.ForeignKey(
        Sprint, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='work_items'
    )

    # ── Identification ─────────────────────────────────────────────────────
    key = models.CharField(max_length=20, db_index=True, help_text="e.g., 'PROJ-142'")
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES, default='TASK')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # ── Workflow ───────────────────────────────────────────────────────────
    status = models.ForeignKey(
        WorkItemStatus, on_delete=models.PROTECT, related_name='work_items'
    )

    # ── Prioritization ─────────────────────────────────────────────────────
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    epic_priority = models.CharField(
        max_length=20, choices=EPIC_PRIORITY_CHOICES, default='NONE', blank=True,
        help_text="Priority within epic hierarchy (only meaningful for EPIC issue_type)"
    )
    order = models.IntegerField(default=0, help_text="Backlog/board ordering position")

    # Phase 1: Story points (Fibonacci: 1, 2, 3, 5, 8, 13, 21)
    story_points = models.IntegerField(
        null=True, blank=True,
        help_text="Estimation in story points (Fibonacci scale)"
    )

    # ── Assignment ─────────────────────────────────────────────────────────
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_work_items'
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reported_work_items'
    )
    # Phase 1: Watchers
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='watched_work_items'
    )

    # ── Dates & Estimation (Phase 1) ───────────────────────────────────────
    due_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    actual_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    # ── Phase 1: Release/Version tagging ───────────────────────────────────
    version = models.ForeignKey(
        'Release', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='work_items',
        help_text="Release/version that this item is tagged to"
    )

    # ── Extensibility ──────────────────────────────────────────────────────
    custom_fields = models.JSONField(default=dict, blank=True)
    labels = models.JSONField(default=list, blank=True)

    # ── External module linking ────────────────────────────────────────────
    linked_object_type = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    linked_object_id = models.UUIDField(null=True, blank=True, db_index=True)

    # ── Phase 2.5: Ticketing / SLA ─────────────────────────────────────────
    sla_policy = models.ForeignKey(
        'SLAPolicy', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='work_items'
    )
    sla_status = models.CharField(
        max_length=20, choices=SLA_STATUS_CHOICES, null=True, blank=True
    )
    first_response_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp of first agent response"
    )
    sla_response_due_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Deadline for first response"
    )
    sla_resolution_due_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Deadline for resolution"
    )
    requester_email = models.EmailField(
        max_length=254, blank=True,
        help_text="Email of the customer who submitted the ticket"
    )
    requester_name = models.CharField(
        max_length=255, blank=True,
        help_text="Name of the customer who submitted the ticket"
    )

    # ── Recurring Tasks ─────────────────────────────────────────────────────
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.CharField(
        max_length=100, blank=True,
        help_text="RRULE string or frequency label: DAILY|WEEKLY|MONTHLY|etc"
    )
    recurrence_end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Work Item'
        verbose_name_plural = 'Work Items'
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['key']),
            models.Index(fields=['issue_type']),
            models.Index(fields=['due_date']),
            models.Index(fields=['project', 'issue_type']),
            # Phase 1 indexes
            models.Index(fields=['sprint']),
            models.Index(fields=['epic']),
            models.Index(fields=['project', 'story_points']),
            # Phase 2.5 indexes
            models.Index(fields=['sla_status']),
            models.Index(fields=['sla_response_due_at']),
            models.Index(fields=['sla_resolution_due_at']),
            models.Index(fields=['requester_email']),
            # Phase 3 indexes
            models.Index(fields=['project', 'sprint']),
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['project', 'issue_type', 'sla_status']),
        ]

    def __str__(self):
        return f"{self.key}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self._generate_key()
        super().save(*args, **kwargs)

    def _generate_key(self):
        prefix = self.project.key
        last_item = WorkItem.objects.filter(
            project=self.project, key__startswith=f"{prefix}-"
        ).order_by('-created_at').first()
        if last_item and last_item.key:
            try:
                last_num = int(last_item.key.split('-')[-1])
                return f"{prefix}-{last_num + 1:04d}"
            except (ValueError, IndexError):
                pass
        return f"{prefix}-{1:04d}"


# ============================================================================
# WORK ITEM LINK
# ============================================================================

class WorkItemLink(Main):
    source_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, related_name='outgoing_links'
    )
    target_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, related_name='incoming_links'
    )
    relation_type = models.CharField(
        max_length=20, choices=WORKITEM_LINK_RELATION_CHOICES
    )

    class Meta:
        unique_together = ('source_item', 'target_item', 'relation_type')
        verbose_name = 'Work Item Link'
        verbose_name_plural = 'Work Item Links'
        indexes = [
            models.Index(fields=['source_item', 'relation_type']),
            models.Index(fields=['target_item', 'relation_type']),
        ]

    def __str__(self):
        return f"{self.source_item.key} {self.get_relation_type_display()} {self.target_item.key}"


# ============================================================================
# WORK ITEM COMMENT
# ============================================================================

class WorkItemComment(Main):
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='work_item_comments'
    )
    body = models.TextField()
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='replies'
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Work Item Comment'
        verbose_name_plural = 'Work Item Comments'
        indexes = [
            models.Index(fields=['work_item', 'created_at']),
        ]

    def __str__(self):
        return f"Comment on {self.work_item.key} by {self.author or 'Anonymous'}"


# ============================================================================
# WORK ITEM ATTACHMENT
# ============================================================================

class WorkItemAttachment(Main):
    """Files, notes, or links attached to a work item."""
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, related_name='attachments'
    )
    file = models.FileField(upload_to='work_attachments/%Y/%m/', null=True, blank=True)
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(default=0)
    note = models.TextField(blank=True)
    url = models.URLField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Work Item Attachment'
        verbose_name_plural = 'Work Item Attachments'
        indexes = [
            models.Index(fields=['work_item', 'created_at']),
        ]

    def __str__(self):
        return f"{self.work_item.key} — {self.file_name}"


# ============================================================================
# WORK ITEM ACTIVITY LOG
# ============================================================================

class WorkItemActivityLog(Main):
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, null=True, blank=True,
        related_name='activity_logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPE_CHOICES)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Work Item Activity Log'
        verbose_name_plural = 'Work Item Activity Logs'
        indexes = [
            models.Index(fields=['work_item', 'created_at']),
            models.Index(fields=['activity_type']),
        ]

    def __str__(self):
        return f"{self.get_activity_type_display()} — {self.work_item.key}: {self.description[:50]}"


# ============================================================================
# HELPER
# ============================================================================

def log_activity(work_item, user, activity_type, description, metadata=None):
    WorkItemActivityLog.objects.create(
        work_item=work_item,
        user=user,
        activity_type=activity_type,
        description=description,
        metadata=metadata or {},
    )


# ============================================================================
# CSAT SURVEY — Phase 2.5: Ticketing Mode
# ============================================================================

class CSATResponse(Main):
    """Customer satisfaction survey response for a resolved ticket."""
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, related_name='csat_responses'
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(1, '1 — Very Dissatisfied'), (2, '2 — Dissatisfied'),
                 (3, '3 — Neutral'), (4, '4 — Satisfied'), (5, '5 — Very Satisfied')]
    )
    comment = models.TextField(blank=True, help_text="Optional customer feedback")
    responded_by = models.EmailField(
        max_length=254, blank=True,
        help_text="Email of the customer who submitted the response"
    )
    responded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-responded_at']
        verbose_name = 'CSAT Response'
        verbose_name_plural = 'CSAT Responses'
        indexes = [
            models.Index(fields=['work_item']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"CSAT {self.rating}/5 — {self.work_item.key}"


# ============================================================================
# MILESTONE — Phase 3: Cross-Cutting Features
# ============================================================================

class Milestone(Main):
    """Department-agnostic milestone that can link to projects, sprints, or work items."""
    MILESTONE_TYPE_CHOICES = (
        ('PROJECT', 'Project Milestone'),
        ('SPRINT', 'Sprint Milestone'),
        ('WORK_ITEM', 'Work Item Milestone'),
        ('GENERIC', 'Generic Milestone'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACHIEVED', 'Achieved'),
        ('MISSED', 'Missed'),
        ('CANCELLED', 'Cancelled'),
    )

    project = models.ForeignKey(
        'Project', on_delete=models.CASCADE, related_name='milestones',
        null=True, blank=True
    )
    sprint = models.ForeignKey(
        'Sprint', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='milestones'
    )
    work_item = models.ForeignKey(
        'WorkItem', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='milestones'
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    milestone_type = models.CharField(
        max_length=20, choices=MILESTONE_TYPE_CHOICES, default='GENERIC'
    )
    target_date = models.DateTimeField()
    completed_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING'
    )

    # Optional: weight/revenue impact
    weight_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Weight/importance percentage (0-100)"
    )
    revenue_impact = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ['target_date', 'name']
        verbose_name = 'Milestone'
        verbose_name_plural = 'Milestones'
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['sprint']),
            models.Index(fields=['work_item']),
            models.Index(fields=['target_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


# ============================================================================
# OKR / GOAL TREE (Phase 3.2)
# ============================================================================

class Objective(Main):
    """A high-level objective aligned to a workspace or project (the 'O' in OKR)."""

    class AlignmentChoices(models.TextChoices):
        COMPANY = 'COMPANY', 'Company'
        DEPARTMENT = 'DEPARTMENT', 'Department'
        TEAM = 'TEAM', 'Team'
        INDIVIDUAL = 'INDIVIDUAL', 'Individual'

    class StatusChoices(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        ACHIEVED = 'ACHIEVED', 'Achieved'
        MISSED = 'MISSED', 'Missed'

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name='objectives'
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='objectives'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    alignment = models.CharField(
        max_length=20, choices=AlignmentChoices.choices, default=AlignmentChoices.TEAM
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.DRAFT
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='owned_objectives'
    )
    parent_objective = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='child_objectives',
        help_text="Parent objective for tree hierarchy (e.g., Company → Department → Team)"
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    weight = models.IntegerField(default=100, help_text="Relative weight 0-100")

    # Linked entities for traceability
    work_items = models.ManyToManyField(
        WorkItem, blank=True, related_name='objectives',
        help_text="Work items that contribute to this objective"
    )
    milestones = models.ManyToManyField(
        Milestone, blank=True, related_name='objectives',
        help_text="Milestones that indicate progress"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['owner']),
            models.Index(fields=['alignment']),
        ]

    def __str__(self):
        return f"[{self.get_alignment_display()}] {self.title}"


class KeyResult(Main):
    """A measurable outcome that tracks progress toward an Objective (the 'KR' in OKR)."""

    class KeyResultType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentage (%)'
        NUMBER = 'NUMBER', 'Number'
        CURRENCY = 'CURRENCY', 'Currency ($)'
        BOOLEAN = 'BOOLEAN', 'Yes/No'

    objective = models.ForeignKey(
        Objective, on_delete=models.CASCADE, related_name='key_results'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    kr_type = models.CharField(
        max_length=20, choices=KeyResultType.choices, default=KeyResultType.PERCENTAGE
    )
    start_value = models.FloatField(default=0)
    target_value = models.FloatField(default=100)
    current_value = models.FloatField(default=0)

    progress_pct = models.FloatField(default=0, editable=False)

    # Optional link to a specific work item that measures this
    metric_work_item = models.ForeignKey(
        WorkItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='key_results',
        help_text="Optional WorkItem (e.g. a Bug count query) that drives this KR"
    )

    class Meta:
        ordering = ['objective__title', 'title']

    def __str__(self):
        return f"{self.objective.title} → {self.title}: {self.current_value}/{self.target_value}"

    def save(self, *args, **kwargs):
        if self.target_value != 0:
            if self.kr_type == KeyResult.KeyResultType.BOOLEAN:
                self.progress_pct = 100.0 if self.current_value >= 1 else 0.0
            else:
                self.progress_pct = min(100.0, round(
                    (self.current_value / self.target_value) * 100, 1
                ))
        super().save(*args, **kwargs)


# ============================================================================
# AUTOMATION RULE (Phase 3.4)
# ============================================================================

class AutomationRule(Main):
    """Trigger/condition/action rule for automating work item operations."""

    class TriggerEvent(models.TextChoices):
        ITEM_CREATED = 'ITEM_CREATED', 'Work Item Created'
        ITEM_UPDATED = 'ITEM_UPDATED', 'Work Item Updated'
        STATUS_CHANGED = 'STATUS_CHANGED', 'Status Changed'
        ASSIGNEE_CHANGED = 'ASSIGNEE_CHANGED', 'Assignee Changed'
        PRIORITY_CHANGED = 'PRIORITY_CHANGED', 'Priority Changed'
        SPRINT_STARTED = 'SPRINT_STARTED', 'Sprint Started'
        SPRINT_ENDED = 'SPRINT_ENDED', 'Sprint Ended'
        SLA_BREACHED = 'SLA_BREACHED', 'SLA Breached'
        COMMENT_ADDED = 'COMMENT_ADDED', 'Comment Added'
        DUE_DATE_APPROACHING = 'DUE_DATE_APPROACHING', 'Due Date Approaching'

    class ActionType(models.TextChoices):
        ASSIGN_TO = 'ASSIGN_TO', 'Assign To'
        SET_STATUS = 'SET_STATUS', 'Set Status'
        SET_PRIORITY = 'SET_PRIORITY', 'Set Priority'
        ADD_LABEL = 'ADD_LABEL', 'Add Label'
        NOTIFY = 'NOTIFY', 'Send Notification'
        WEBHOOK = 'WEBHOOK', 'Call Webhook'
        CREATE_SUBTASK = 'CREATE_SUBTASK', 'Create Subtask'
        START_SLA = 'START_SLA', 'Start SLA Timer'

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='automation_rules'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=True)
    trigger_event = models.CharField(
        max_length=30, choices=TriggerEvent.choices
    )

    conditions = models.JSONField(default=list, blank=True)

    action_type = models.CharField(max_length=30, choices=ActionType.choices)
    action_config = models.JSONField(
        default=dict, blank=True,
        help_text="Action parameters: e.g. {'user_id': '...', 'status_id': '...', 'webhook_url': '...'}"
    )

    issue_type_filter = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="If set, only applies to this issue type"
    )

    priority = models.IntegerField(
        default=100,
        help_text="Execution priority (lower runs first)"
    )
    run_count = models.IntegerField(default=0, editable=False)
    last_run_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ['priority', 'name']
        indexes = [
            models.Index(fields=['project', 'trigger_event']),
            models.Index(fields=['is_enabled']),
        ]

    def __str__(self):
        return f"[{self.trigger_event}] {self.name}"

    def evaluate_conditions(self, work_item):
        """Check if all conditions match for a given work item."""
        import operator as op
        ops = {
            'eq': op.eq, 'ne': op.ne,
            'gt': op.gt, 'gte': op.ge,
            'lt': op.lt, 'lte': op.le,
            'in': lambda v, lst: v in lst,
            'contains': lambda v, s: s in str(v),
        }
        for cond in self.conditions:
            field = cond.get('field')
            operator_key = cond.get('operator', 'eq')
            value = cond.get('value')

            field_value = getattr(work_item, field, None)
            if field_value is None and hasattr(work_item, 'custom_fields'):
                field_value = work_item.custom_fields.get(field)

            compare_fn = ops.get(operator_key)
            if not compare_fn or not compare_fn(field_value, value):
                return False
        return True


# ============================================================================
# NOTIFICATIONS & WEBHOOKS (Phase 3.5)
# ============================================================================

class Notification(Main):
    """In-app notification for a user."""

    class NotificationType(models.TextChoices):
        ITEM_ASSIGNED = 'ITEM_ASSIGNED', 'Work Item Assigned'
        ITEM_UPDATED = 'ITEM_UPDATED', 'Work Item Updated'
        COMMENT_ADDED = 'COMMENT_ADDED', 'Comment Added'
        STATUS_CHANGED = 'STATUS_CHANGED', 'Status Changed'
        SLA_BREACHED = 'SLA_BREACHED', 'SLA Breached'
        SLA_WARNING = 'SLA_WARNING', 'SLA Warning'
        MENTION = 'MENTION', 'You were mentioned'
        DUE_SOON = 'DUE_SOON', 'Due Date Approaching'
        OVERDUE = 'OVERDUE', 'Item Overdue'
        SPRINT_STARTED = 'SPRINT_STARTED', 'Sprint Started'
        SPRINT_ENDED = 'SPRINT_ENDED', 'Sprint Ended'
        MILESTONE_ACHIEVED = 'MILESTONE_ACHIEVED', 'Milestone Achieved'
        SYSTEM = 'SYSTEM', 'System Notification'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='work_notifications'
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Optional linked entities
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notifications'
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notifications'
    )

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"

    def mark_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(Main):
    """Per-user notification channel preferences per event type."""

    class Channel(models.TextChoices):
        IN_APP = 'IN_APP', 'In-App'
        EMAIL = 'EMAIL', 'Email'
        SLACK = 'SLACK', 'Slack'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, null=True, blank=True, related_name='notification_preferences'
    )
    notification_type = models.CharField(max_length=30, choices=Notification.NotificationType.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    enabled = models.BooleanField(default=True)
    digest_enabled = models.BooleanField(default=False, help_text="Receive daily/weekly digest instead of real-time")
    digest_frequency = models.CharField(
        max_length=10, choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly')],
        default='DAILY', blank=True,
    )

    class Meta:
        unique_together = ['user', 'project', 'notification_type', 'channel']

    def __str__(self):
        return f"{self.user} - {self.notification_type} via {self.channel}: {'ON' if self.enabled else 'OFF'}"


class WebhookConfig(Main):
    """Webhook integration config (Slack, Discord, custom)."""

    class WebhookProvider(models.TextChoices):
        SLACK = 'SLACK', 'Slack'
        DISCORD = 'DISCORD', 'Discord'
        CUSTOM = 'CUSTOM', 'Custom Webhook'

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='webhook_configs'
    )
    provider = models.CharField(max_length=10, choices=WebhookProvider.choices)
    name = models.CharField(max_length=255, blank=True)
    webhook_url = models.URLField(max_length=500)
    secret = models.CharField(max_length=255, blank=True, help_text="Optional signing secret")
    is_enabled = models.BooleanField(default=True)
    events = models.JSONField(
        default=list, blank=True,
        help_text="List of NotificationType values to forward"
    )
    last_sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    failure_count = models.IntegerField(default=0, editable=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'provider']),
            models.Index(fields=['is_enabled']),
        ]

    def __str__(self):
        return f"{self.get_provider_display()} - {self.name or self.webhook_url[:50]}"


# ============================================================================
# CUSTOM FIELDS (Phase 3.6)
# ============================================================================

class CustomFieldDefinition(Main):
    """Admin-configurable custom field definitions per project/issue type."""

    class FieldType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        NUMBER = 'NUMBER', 'Number'
        DATE = 'DATE', 'Date'
        SELECT = 'SELECT', 'Select (Dropdown)'
        MULTI_SELECT = 'MULTI_SELECT', 'Multi-Select'
        BOOLEAN = 'BOOLEAN', 'Yes/No'
        URL = 'URL', 'URL'
        USER = 'USER', 'User'

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='custom_field_defs'
    )
    issue_type_filter = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="If set, only applies to this issue type"
    )
    field_key = models.SlugField(
        max_length=100,
        help_text="Key used in the JSON custom_fields object (e.g. 'deal_value')"
    )
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.TEXT)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    options = models.JSONField(
        default=list, blank=True,
        help_text="Available options for SELECT/MULTI_SELECT types"
    )
    placeholder = models.CharField(max_length=255, blank=True)
    default_value = models.JSONField(null=True, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'label']
        unique_together = ['project', 'field_key', 'issue_type_filter']
        indexes = [
            models.Index(fields=['project', 'is_active']),
            models.Index(fields=['field_key']),
        ]

    def __str__(self):
        return f"{self.label} ({self.field_key})"


# ============================================================================
# RECURRING TASKS
# ============================================================================

class RecurringTaskConfig(Main):
    """Recurrence configuration for a work item."""

    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('BIWEEKLY', 'Bi-Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]

    work_item = models.OneToOneField(
        WorkItem, on_delete=models.CASCADE, related_name='recurrence_config'
    )
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    interval = models.IntegerField(default=1, help_text="Every N frequency units")
    days_of_week = models.JSONField(default=list, blank=True, help_text="For weekly: [0=Mon, 6=Sun]")
    day_of_month = models.IntegerField(null=True, blank=True)
    month_of_year = models.IntegerField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    max_occurrences = models.IntegerField(null=True, blank=True)
    next_occurrence = models.DateField(null=True, blank=True)
    auto_create = models.BooleanField(default=True, help_text="Auto-create next occurrence when current is completed")
    occurrences_created = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Recurring {self.frequency} - {self.work_item.title}"


# ============================================================================
# APPROVAL WORKFLOWS
# ============================================================================

class ApprovalWorkflow(Main):
    """Template defining multi-step approval for a project/issue type."""

    APPROVAL_TYPES = [
        ('SINGLE', 'Single Step'),
        ('SEQUENTIAL', 'Sequential'),
        ('PARALLEL', 'Parallel'),
        ('ANY', 'Any Approver'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='approval_workflows')
    name = models.CharField(max_length=255)
    issue_type_filter = models.CharField(max_length=50, blank=True, help_text="Apply to specific issue type, or leave blank for all")
    approval_type = models.CharField(max_length=20, choices=APPROVAL_TYPES, default='SEQUENTIAL')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_approval_type_display()})"


class ApprovalStep(Main):
    """A single step within an approval workflow."""

    workflow = models.ForeignKey(
        ApprovalWorkflow, on_delete=models.CASCADE, related_name='steps'
    )
    step_order = models.IntegerField(default=0)
    name = models.CharField(max_length=255)
    assignee_role = models.CharField(max_length=50, blank=True, help_text="Role required to approve")
    assignee_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_steps'
    )
    required_approvals = models.IntegerField(default=1, help_text="For parallel: how many must approve")

    class Meta:
        ordering = ['step_order']
        unique_together = ['workflow', 'step_order']

    def __str__(self):
        return f"Step {self.step_order}: {self.name}"


class ApprovalRequest(Main):
    """An active approval request tied to a work item."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, related_name='approval_requests'
    )
    workflow = models.ForeignKey(
        ApprovalWorkflow, on_delete=models.SET_NULL, null=True, related_name='requests'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='approval_requests_made'
    )
    current_step = models.ForeignKey(
        ApprovalStep, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_requests'
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Approval {self.id} - {self.work_item.title}"


class ApprovalAction(Main):
    """A single approve/reject action on an approval step."""

    request = models.ForeignKey(
        ApprovalRequest, on_delete=models.CASCADE, related_name='actions'
    )
    step = models.ForeignKey(ApprovalStep, on_delete=models.CASCADE, related_name='actions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='approval_actions')
    action = models.CharField(max_length=20, choices=[('APPROVE', 'Approve'), ('REJECT', 'Reject')])
    comment = models.TextField(blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} by {self.user}"


# ============================================================================
# CANNED RESPONSES / MACROS
# ============================================================================

class CannedResponse(Main):
    """Pre-written response template for support tickets."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, null=True, blank=True, related_name='canned_responses'
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    is_global = models.BooleanField(default=False, help_text="Available across all projects")
    shortcut = models.CharField(max_length=50, blank=True, help_text="Keyboard shortcut eg. /thankyou")

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


# ============================================================================
# PROJECT / CAMPAIGN TEMPLATES
# ============================================================================

class ProjectTemplate(Main):
    """Reusable project template for creating projects from scratch."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    workflow_preset = models.CharField(max_length=50, blank=True)
    default_issue_types = models.JSONField(default=list, blank=True)
    template_data = models.JSONField(
        default=dict, blank=True,
        help_text="Predefined work items, milestones, sprints configuration"
    )
    is_global = models.BooleanField(default=False)
    category = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class WorkItemTemplate(Main):
    """Reusable template for creating work items with pre-filled fields."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    issue_type = models.CharField(
        max_length=20,
        help_text="Work item type this template creates (TASK, BUG, STORY, etc.)"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        null=True, blank=True, related_name='work_item_templates'
    )
    project_template = models.ForeignKey(
        ProjectTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='work_item_templates'
    )
    template_fields = models.JSONField(
        default=dict, blank=True,
        help_text="Default field values: title, description, story_points, priority, etc."
    )
    checklist_items = models.JSONField(
        default=list, blank=True,
        help_text="Predefined checklist items: [{'text': '...', 'checked': false}, ...]"
    )
    is_global = models.BooleanField(default=False)
    category = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ============================================================================
# GITHUB / CODE INTEGRATION
# ============================================================================

class GitHubIntegration(Main):
    """GitHub repo linking for a project."""

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name='github_integration'
    )
    repo_owner = models.CharField(max_length=255)
    repo_name = models.CharField(max_length=255)
    repo_full_name = models.CharField(max_length=512, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    auto_transition = models.BooleanField(
        default=True,
        help_text="Auto-transition work items when PR is merged"
    )
    branch_prefix = models.CharField(max_length=100, blank=True, help_text="e.g. feature/, bugfix/")

    class Meta:
        unique_together = ['repo_owner', 'repo_name']

    def __str__(self):
        return f"{self.repo_full_name}"


class GitHubLink(Main):
    """Link between a GitHub event (PR/commit) and a work item."""

    LINK_TYPES = [
        ('PR', 'Pull Request'),
        ('COMMIT', 'Commit'),
        ('ISSUE', 'Issue'),
    ]

    integration = models.ForeignKey(
        GitHubIntegration, on_delete=models.CASCADE, related_name='links'
    )
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, related_name='github_links'
    )
    link_type = models.CharField(max_length=20, choices=LINK_TYPES)
    github_id = models.BigIntegerField(null=True, blank=True)
    title = models.CharField(max_length=512, blank=True)
    url = models.URLField(max_length=1024, blank=True)
    state = models.CharField(max_length=50, blank=True, help_text="e.g. open, closed, merged")
    branch = models.CharField(max_length=255, blank=True)
    event_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.link_type}: {self.url}"


# ============================================================================
# PRIORITY AUTO-SUGGESTION RULES
# ============================================================================

class PriorityRule(Main):
    """Keyword-based priority auto-suggestion rule."""

    PRIORITY_CHOICES = [
        ('LOWEST', 'Lowest'),
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('HIGHEST', 'Highest'),
        ('CRITICAL', 'Critical'),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, null=True, blank=True, related_name='priority_rules'
    )
    keywords = models.JSONField(default=list, help_text="List of keywords/patterns to match")
    suggested_priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['suggested_priority']

    def __str__(self):
        return f"{', '.join(self.keywords[:3])} → {self.suggested_priority}"


# ============================================================================
# WEBHOOK DELIVERY LOGS
# ============================================================================

class WebhookDeliveryLog(Main):
    webhook = models.ForeignKey(
        WebhookConfig, on_delete=models.CASCADE, related_name='delivery_logs'
    )
    event_type = models.CharField(max_length=100)
    url = models.URLField(max_length=1024)
    status_code = models.IntegerField(null=True, blank=True)
    request_body = models.JSONField(default=dict, blank=True)
    response_body = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    duration_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Webhook Delivery Log"
        verbose_name_plural = "Webhook Delivery Logs"

    def __str__(self):
        return f"{self.event_type} → {self.status_code}"


# ============================================================================
# WORK ITEM TIME LOGS
# ============================================================================

class WorkItemTimeLog(Main):
    work_item = models.ForeignKey(
        WorkItem, on_delete=models.CASCADE, related_name='time_logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='work_time_logs'
    )
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField()

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Work Item Time Log"
        verbose_name_plural = "Work Item Time Logs"

    def __str__(self):
        return f"{self.hours}h on {self.work_item.title}"


# ============================================================================
# WORKFLOW TRANSITION GATES
# ============================================================================

class TransitionRule(Main):
    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name='transition_rules'
    )
    from_status = models.ForeignKey(
        WorkItemStatus, on_delete=models.CASCADE, related_name='transition_rules_from'
    )
    to_status = models.ForeignKey(
        WorkItemStatus, on_delete=models.CASCADE, related_name='transition_rules_to'
    )
    required_role = models.CharField(max_length=50, blank=True, help_text="Role required to perform this transition")
    required_field_keys = models.JSONField(default=list, blank=True, help_text="Field keys that must have values before transition")
    require_comment = models.BooleanField(default=False, help_text="Require a comment on transition")
    require_approval = models.BooleanField(default=False, help_text="Require an approval request before allowing transition")
    error_message = models.CharField(max_length=255, blank=True, help_text="Custom error message shown when gate blocks transition")

    class Meta:
        ordering = ['workflow', 'from_status', 'to_status']
        unique_together = ['workflow', 'from_status', 'to_status']

    def __str__(self):
        return f"{self.from_status.name} → {self.to_status.name} gate"


# ============================================================================
# FIELD-LEVEL VISIBILITY (Phase 4.3)
# ============================================================================

class ProjectFieldVisibility(Main):
    """Controls which WorkItem fields are visible per role per project."""

    class RoleChoices(models.TextChoices):
        VIEWER = 'VIEWER', 'Viewer'
        MEMBER = 'MEMBER', 'Member'
        EDITOR = 'EDITOR', 'Editor'
        ADMIN = 'ADMIN', 'Admin'

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='field_visibility_rules'
    )
    role = models.CharField(max_length=10, choices=RoleChoices.choices)
    visible_fields = models.JSONField(
        default=list, blank=True,
        help_text="List of field names that this role can see. Empty = all fields."
    )
    hidden_fields = models.JSONField(
        default=list, blank=True,
        help_text="List of field names explicitly hidden from this role."
    )

    class Meta:
        unique_together = ['project', 'role']

    def __str__(self):
        return f"{self.project.name} - {self.role} visibility"


# ============================================================================
# SAVED FILTER / CUSTOM VIEW
# ============================================================================

class SavedFilter(Main):
    """User-saved filter presets for quick reuse across views."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='saved_filters'
    )
    name = models.CharField(max_length=100)
    scope = models.CharField(
        max_length=20, default='project',
        choices=[
            ('workspace', 'Workspace'),
            ('project', 'Project'),
            ('my_work', 'My Work'),
            ('roadmap', 'Roadmap'),
        ]
    )
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, null=True, blank=True,
        related_name='saved_filters'
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, null=True, blank=True,
        related_name='saved_filters'
    )
    filter_data = models.JSONField(
        default=dict, blank=True,
        help_text="JSON object of filter key-value pairs"
    )
    column_config = models.JSONField(
        default=dict, blank=True,
        help_text="JSON object for visible columns and their order"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Auto-apply this filter on page load"
    )

    class Meta:
        ordering = ['user', 'name']
        unique_together = ['user', 'name', 'project']
        verbose_name = 'Saved Filter'
        verbose_name_plural = 'Saved Filters'

    def __str__(self):
        return f"{self.user.email} - {self.name}"
