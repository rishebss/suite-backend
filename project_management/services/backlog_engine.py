from django.db.models import Count, Q
from project_management.models import WorkItem, WorkItemStatus


class BacklogEngine:
    """Engine for backlog management, prioritization, and sprint planning."""

    @staticmethod
    def get_backlog(project, filters=None):
        """Get prioritized backlog for a project."""
        qs = WorkItem.objects.filter(
            project=project,
            status__category__in=['backlog', 'todo']
        ).select_related('assignee', 'status')

        if filters:
            if filters.get('issue_type'):
                qs = qs.filter(issue_type=filters['issue_type'])
            if filters.get('assignee'):
                qs = qs.filter(assignee_id=filters['assignee'])
            if filters.get('priority'):
                qs = qs.filter(priority=filters['priority'])
            if filters.get('search'):
                qs = qs.filter(title__icontains=filters['search'])

        # Sort by: priority (critical first), then order, then created
        priority_order = {
            'CRITICAL': 0,
            'HIGH': 1,
            'MEDIUM': 2,
            'LOW': 3,
        }

        sorted_items = sorted(qs, key=lambda x: (
            priority_order.get(x.priority, 99),
            x.order,
            -x.created_at.timestamp(),
        ))

        return sorted_items

    @staticmethod
    def reorder_backlog(project, item_orders):
        """Bulk-reorder items: [{id, order}, ...]."""
        for item in item_orders:
            WorkItem.objects.filter(
                id=item['id'], project=project
            ).update(order=item['order'])

    @staticmethod
    def get_backlog_summary(project):
        """Summary statistics for the backlog view."""
        backlog_items = WorkItem.objects.filter(
            project=project,
            status__category__in=['backlog', 'todo']
        )

        return {
            'total': backlog_items.count(),
            'by_type': dict(
                backlog_items.values('issue_type')
                .annotate(count=Count('id'))
                .values_list('issue_type', 'count')
            ),
            'by_priority': dict(
                backlog_items.values('priority')
                .annotate(count=Count('id'))
                .values_list('priority', 'count')
            ),
            'unassigned': backlog_items.filter(assignee__isnull=True).count(),
            'overdue': backlog_items.filter(
                due_date__isnull=False,
                due_date__lt=__import__('django').utils.timezone.now()
            ).count(),
        }

    @staticmethod
    def get_sprint_candidates(project, limit=20):
        """Get top N items for an upcoming sprint based on priority and order."""
        return BacklogEngine.get_backlog(project)[:limit]
