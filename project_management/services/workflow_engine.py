import json
from project_management.models import WorkItem, WorkItemStatus, Workflow, Project, Workspace


PRESET_STATUSES = {
    'scrum': {
        'scope': 'dev_scrum',
        'statuses': [
            ('Backlog', 'backlog', '#6b7280', 'backlog'),
            ('Triage', 'triage', '#f59e0b', 'backlog'),
            ('To Do', 'todo', '#3b82f6', 'todo'),
            ('In Progress', 'in_progress', '#8b5cf6', 'in_progress'),
            ('In Review', 'in_review', '#06b6d4', 'in_progress'),
            ('QA', 'qa', '#ec4899', 'in_progress'),
            ('Blocked', 'blocked', '#ef4444', 'blocked'),
            ('Done', 'done', '#22c55e', 'done'),
        ],
    },
    'kanban': {
        'scope': 'dev_kanban',
        'statuses': [
            ('To Do', 'todo', '#3b82f6', 'todo'),
            ('In Progress', 'in_progress', '#8b5cf6', 'in_progress'),
            ('Blocked', 'blocked', '#ef4444', 'blocked'),
            ('Done', 'done', '#22c55e', 'done'),
        ],
    },
    'sales_pipeline': {
        'scope': 'sales_deal',
        'statuses': [
            ('Lead', 'lead', '#3b82f6', 'todo'),
            ('Qualified', 'qualified', '#8b5cf6', 'in_progress'),
            ('Proposal Sent', 'proposal_sent', '#f59e0b', 'in_progress'),
            ('Negotiation', 'negotiation', '#ec4899', 'in_progress'),
            ('Won', 'won', '#22c55e', 'done'),
            ('Lost', 'lost', '#ef4444', 'done'),
        ],
    },
    'support_ticket': {
        'scope': 'support_ticket',
        'statuses': [
            ('New', 'new', '#3b82f6', 'todo'),
            ('Assigned', 'assigned', '#8b5cf6', 'in_progress'),
            ('In Progress', 'in_progress', '#f59e0b', 'in_progress'),
            ('Waiting on Customer', 'waiting_on_customer', '#06b6d4', 'blocked'),
            ('Resolved', 'resolved', '#22c55e', 'done'),
            ('Closed', 'closed', '#6b7280', 'done'),
        ],
    },
    'ops_approval': {
        'scope': 'ops_approval',
        'statuses': [
            ('Requested', 'requested', '#3b82f6', 'todo'),
            ('Under Review', 'under_review', '#f59e0b', 'in_progress'),
            ('Approved', 'approved', '#22c55e', 'done'),
            ('Rejected', 'rejected', '#ef4444', 'done'),
            ('Completed', 'completed', '#6b7280', 'done'),
        ],
    },
}


def apply_workflow_preset(project, preset_name):
    """Create workflow and statuses from a preset and assign to project."""
    preset = PRESET_STATUSES.get(preset_name)
    if not preset:
        return
    slug = preset_name.replace('_', '-')
    wf, _ = Workflow.objects.get_or_create(
        slug=slug,
        defaults={
            'name': preset_name.replace('_', ' ').title(),
            'scope': preset['scope'],
        },
    )
    existing_slugs = set(
        WorkItemStatus.objects.filter(workflow=wf).values_list('slug', flat=True)
    )
    for i, (name, slug_val, color, category) in enumerate(preset['statuses']):
        if slug_val not in existing_slugs:
            WorkItemStatus.objects.create(
                workflow=wf, name=name, slug=slug_val,
                order=i, color=color, category=category,
            )
    project.workflows.add(wf)


class WorkflowEngine:
    """Validates and enforces workflow transitions for WorkItems."""

    VALID_TRANSITIONS = {
        'dev_scrum': {
            'BACKLOG': ['TRIAGE'],
            'TRIAGE': ['TODO'],
            'TODO': ['IN_PROGRESS'],
            'IN_PROGRESS': ['IN_REVIEW', 'BLOCKED'],
            'IN_REVIEW': ['QA', 'IN_PROGRESS'],
            'QA': ['DONE', 'IN_PROGRESS'],
            'BLOCKED': ['IN_PROGRESS'],
            'DONE': [],
        },
        'dev_kanban': {
            'TODO': ['IN_PROGRESS'],
            'IN_PROGRESS': ['BLOCKED', 'DONE'],
            'BLOCKED': ['IN_PROGRESS'],
            'DONE': [],
        },
        'support_ticket': {
            'NEW': ['ASSIGNED'],
            'ASSIGNED': ['IN_PROGRESS'],
            'IN_PROGRESS': ['WAITING_ON_CUSTOMER', 'RESOLVED'],
            'WAITING_ON_CUSTOMER': ['IN_PROGRESS', 'RESOLVED'],
            'RESOLVED': ['CLOSED'],
            'CLOSED': [],
        },
        'sales_deal': {
            'LEAD': ['QUALIFIED'],
            'QUALIFIED': ['PROPOSAL_SENT'],
            'PROPOSAL_SENT': ['NEGOTIATION', 'LOST'],
            'NEGOTIATION': ['WON', 'LOST'],
            'WON': [],
            'LOST': [],
        },
        'ops_approval': {
            'REQUESTED': ['UNDER_REVIEW'],
            'UNDER_REVIEW': ['APPROVED', 'REJECTED'],
            'APPROVED': ['COMPLETED'],
            'REJECTED': [],
            'COMPLETED': [],
        },
    }

    @staticmethod
    def get_allowed_transitions(work_item: WorkItem) -> list:
        """Get list of allowed next statuses for a given work item."""
        workflow = work_item.status.workflow
        current_status_slug = work_item.status.slug.upper()

        # Check for scope-specific transitions
        scope_transitions = WorkflowEngine.VALID_TRANSITIONS.get(workflow.scope, {})
        allowed_slugs = scope_transitions.get(current_status_slug, [])

        # If no scope-specific rules, allow any status in the workflow
        if not allowed_slugs:
            allowed_slugs = WorkItemStatus.objects.filter(
                workflow=workflow
            ).exclude(id=work_item.status.id).values_list('slug', flat=True)

        return list(
            WorkItemStatus.objects.filter(
                workflow=workflow,
                slug__in=[s.lower() for s in allowed_slugs]
            ).values('id', 'name', 'slug', 'color', 'category')
        )

    @staticmethod
    def can_transition(work_item: WorkItem, target_status: WorkItemStatus) -> tuple:
        """Check if a transition is allowed. Returns (allowed: bool, reason: str)."""
        if work_item.status.workflow_id != target_status.workflow_id:
            return False, "Target status belongs to a different workflow"

        allowed = WorkflowEngine.get_allowed_transitions(work_item)
        allowed_ids = [s['id'] for s in allowed]

        if str(target_status.id) not in allowed_ids:
            return False, (
                f"Cannot transition from '{work_item.status.name}' "
                f"to '{target_status.name}'"
            )

        return True, ""

    @staticmethod
    def get_workflow_stats(workflow: Workflow) -> dict:
        """Get statistics about a workflow's usage."""
        status_stats = []
        for status_obj in workflow.statuses.all().order_by('order'):
            count = WorkItem.objects.filter(status=status_obj).count()
            status_stats.append({
                'id': str(status_obj.id),
                'name': status_obj.name,
                'slug': status_obj.slug,
                'color': status_obj.color,
                'category': status_obj.category,
                'item_count': count,
            })

        return {
            'workflow_id': str(workflow.id),
            'workflow_name': workflow.name,
            'total_statuses': workflow.statuses.count(),
            'statuses': status_stats,
            'total_items': sum(s['item_count'] for s in status_stats),
        }

    @staticmethod
    def create_project_from_template(template, workspace_id, name, key, user):
        """Create a Project from a ProjectTemplate."""
        from project_management.models import Workflow as WorkflowModel
        workspace = Workspace.objects.get(id=workspace_id)
        project = Project.objects.create(
            workspace=workspace,
            name=name,
            key=key,
            created_by=user,
        )
        first_status = None
        if template.workflow_preset:
            wf, _ = WorkflowModel.objects.get_or_create(
                name=template.workflow_preset,
                defaults={'scope': 'dev_scrum', 'created_by': user}
            )
            project.workflows.add(wf)
            first_status = wf.statuses.order_by('order').first()
        template_data = template.template_data
        if isinstance(template_data, str):
            template_data = json.loads(template_data)
        predefined_items = template_data.get('work_items', [])
        for item_data in predefined_items:
            WorkItem.objects.create(
                project=project,
                title=item_data.get('title', 'Task from template'),
                description=item_data.get('description', ''),
                issue_type=item_data.get('issue_type', 'task'),
                priority=item_data.get('priority', 'MEDIUM'),
                created_by=user,
                status=first_status,
            )
        return project
