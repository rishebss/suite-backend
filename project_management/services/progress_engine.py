from django.db.models import Count, Sum, Q
from project_management.models import WorkItem, WorkItemStatus, Milestone, Sprint


class ProgressEngine:
    """Computes weighted progress, critical path, and completion metrics."""

    @staticmethod
    def get_project_progress(project_id):
        items = WorkItem.objects.filter(project_id=project_id)
        total = items.count()
        if total == 0:
            return {'total': 0, 'completed': 0, 'in_progress': 0, 'blocked': 0, 'percent': 0}
        completed = items.filter(status__category='done').count()
        in_progress = items.filter(status__category='in_progress').count()
        blocked = items.filter(status__category='blocked').count()
        return {
            'total': total,
            'completed': completed,
            'in_progress': in_progress,
            'blocked': blocked,
            'percent': round(completed / total * 100, 1),
        }

    @staticmethod
    def get_milestone_progress(milestone: Milestone):
        linked_items = WorkItem.objects.filter(
            Q(milestone=milestone) | Q(project__milestones=milestone)
        ).distinct()
        total = linked_items.count()
        if total == 0:
            return {'milestone': milestone.title, 'total': 0, 'completed': 0, 'percent': 0}
        completed = linked_items.filter(status__category='done').count()
        return {
            'milestone': milestone.title,
            'total': total,
            'completed': completed,
            'percent': round(completed / total * 100, 1),
        }

    @staticmethod
    def get_sprint_progress(sprint: Sprint):
        items = WorkItem.objects.filter(sprint=sprint)
        total = items.count()
        if total == 0:
            return {'sprint': sprint.name, 'total': 0, 'completed': 0, 'percent': 0}
        completed = items.filter(status__category='done').count()
        completed_points = items.filter(status__category='done').aggregate(
            total=Sum('story_points')
        )['total'] or 0
        total_points = items.aggregate(total=Sum('story_points'))['total'] or 0
        return {
            'sprint': sprint.name,
            'total': total,
            'completed': completed,
            'total_points': float(total_points),
            'completed_points': float(completed_points),
            'percent_by_count': round(completed / total * 100, 1),
            'percent_by_points': round(float(completed_points) / float(total_points) * 100, 1) if total_points else 0,
        }

    @staticmethod
    def get_status_distribution(project_id):
        statuses = WorkItemStatus.objects.filter(
            workflow__project__id=project_id
        ).annotate(
            count=Count('work_items')
        ).values('id', 'name', 'slug', 'color', 'category', 'count')
        return list(statuses)

    @staticmethod
    def get_cumulative_flow(project_id, days=30):
        from django.utils import timezone
        from datetime import timedelta
        import json

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        statuses = WorkItemStatus.objects.filter(
            workflow__project__id=project_id
        ).values('id', 'name', 'slug', 'color')
        status_map = {s['id']: s for s in statuses}
        status_ids = list(status_map.keys())

        data = []
        current = start_date
        while current <= end_date:
            row = {'date': str(current)}
            for sid in status_ids:
                count = WorkItem.objects.filter(
                    project_id=project_id,
                    status_id=sid,
                    created_at__date__lte=current,
                ).exclude(
                    completed_at__date__lt=current
                ).count()
                row[status_map[sid]['slug']] = count
            data.append(row)
            current += timedelta(days=1)
        return data
