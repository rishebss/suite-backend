from django.utils import timezone
from project_management.models import Sprint, WorkItem, WorkItemActivityLog


class SprintEngine:
    """Manages sprint lifecycle, capacity, and auto-completion workflows."""

    @staticmethod
    def complete_sprint(sprint: Sprint, auto_move_incomplete: bool = True):
        """Mark a sprint as completed, optionally moving incomplete items."""
        if sprint.status == 'COMPLETED':
            return {'error': 'Sprint already completed'}
        items = WorkItem.objects.filter(sprint=sprint)
        incomplete = items.exclude(status__category='done')
        moved = 0
        if auto_move_incomplete:
            for item in incomplete:
                next_sprint = Sprint.objects.filter(
                    project=sprint.project,
                    status='ACTIVE'
                ).exclude(id=sprint.id).first()
                if next_sprint:
                    old_sprint = item.sprint
                    item.sprint = next_sprint
                    item.save(update_fields=['sprint'])
                    WorkItemActivityLog.objects.create(
                        work_item=item,
                        activity_type='SPRINT_CHANGED',
                        description=f"Auto-moved from completed sprint '{sprint.name}' to '{next_sprint.name}'",
                    )
                    moved += 1
        sprint.status = 'COMPLETED'
        sprint.completed_at = timezone.now()
        sprint.save(update_fields=['status', 'completed_at'])
        return {
            'sprint': str(sprint.id),
            'status': 'COMPLETED',
            'total_items': items.count(),
            'completed_items': items.filter(status__category='done').count(),
            'incomplete_items': incomplete.count(),
            'auto_moved': moved,
        }

    @staticmethod
    def start_sprint(sprint: Sprint):
        """Activate a sprint and move items from backlog."""
        if sprint.status != 'PLANNED':
            return {'error': 'Only PLANNED sprints can be started'}
        sprint.status = 'ACTIVE'
        sprint.started_at = timezone.now()
        sprint.save(update_fields=['status', 'started_at'])
        return {'sprint': str(sprint.id), 'status': 'ACTIVE'}

    @staticmethod
    def get_sprint_capacity(sprint: Sprint):
        members = sprint.members.all().select_related('user')
        capacity_data = []
        for member in members:
            assigned = WorkItem.objects.filter(
                sprint=sprint, assignee=member.user
            ).exclude(status__category='done')
            total_points = assigned.aggregate(models.Sum('story_points'))['story_points__sum'] or 0
            total_hours = assigned.aggregate(models.Sum('estimated_hours'))['estimated_hours__sum'] or 0
            capacity_data.append({
                'user_id': str(member.user.id),
                'name': member.user.get_full_name() or member.user.username,
                'capacity_hours': float(member.capacity_hours or 0),
                'assigned_points': float(total_points),
                'assigned_hours': float(total_hours),
                'utilization': round(float(total_hours) / float(member.capacity_hours or 1) * 100, 1),
            })
        return capacity_data
