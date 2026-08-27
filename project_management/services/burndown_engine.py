from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from project_management.models import Sprint, WorkItem


class BurndownEngine:
    """Computes burndown data, velocity, and sprint metrics."""

    @staticmethod
    def calculate_burndown(sprint: Sprint) -> dict:
        """Generate daily burndown data for a sprint.
        Returns array of {date, remaining_points, ideal_burndown} entries.
        """
        if not sprint.start_date or not sprint.end_date:
            return {'burndown': [], 'total_committed': 0, 'total_completed': 0}

        sprint_items = WorkItem.objects.filter(sprint=sprint)
        total_committed = (
            sprint_items.aggregate(total=Sum('story_points'))['total'] or 0
        )

        # Get all items completed during the sprint with their points
        completed_items = sprint_items.filter(
            completed_at__gte=sprint.start_date,
            completed_at__lte=sprint.end_date
        ).values('completed_at__date').annotate(
            points_completed=Sum('story_points')
        ).order_by('completed_at__date')

        completed_map = {}
        for item in completed_items:
            date_key = str(item['completed_at__date'])
            completed_map[date_key] = float(item['points_completed'] or 0)

        total_completed = sum(completed_map.values())

        # Generate day-by-day burndown
        current = sprint.start_date
        remaining = float(total_committed)
        days = (sprint.end_date - sprint.start_date).days or 1
        ideal_per_day = remaining / days

        burndown_data = []
        while current <= sprint.end_date:
            date_key = current.strftime('%Y-%m-%d')
            completed_today = completed_map.get(date_key, 0)
            remaining -= completed_today

            days_elapsed = (current - sprint.start_date).days
            ideal_remaining = max(0, float(total_committed) - (ideal_per_day * days_elapsed))

            burndown_data.append({
                'date': date_key,
                'remaining_points': max(0, round(remaining, 1)),
                'ideal_burndown': round(ideal_remaining, 1),
                'completed_today': completed_today,
            })

            current += timezone.timedelta(days=1)

        return {
            'burndown': burndown_data,
            'total_committed': float(total_committed),
            'total_completed': total_completed,
            'completion_pct': round(
                (total_completed / total_committed * 100) if total_committed else 0, 1
            ),
        }

    @staticmethod
    def calculate_velocity(project, last_n_sprints: int = 5) -> dict:
        """Calculate team velocity from the last N completed sprints."""
        completed_sprints = Sprint.objects.filter(
            project=project, status='COMPLETED'
        ).order_by('-end_date')[:last_n_sprints]

        if not completed_sprints:
            return {
                'velocity': 0,
                'sprints_analyzed': 0,
                'trend': [],
            }

        sprint_data = []
        total_points = 0
        for sprint in completed_sprints:
            items = WorkItem.objects.filter(sprint=sprint)
            committed = items.aggregate(total=Sum('story_points'))['total'] or 0
            completed = items.filter(
                completed_at__isnull=False
            ).aggregate(total=Sum('story_points'))['total'] or 0

            sprint_data.append({
                'sprint_id': str(sprint.id),
                'sprint_name': sprint.name,
                'committed_points': float(committed),
                'completed_points': float(completed),
                'completion_pct': round(
                    (float(completed) / float(committed) * 100) if committed else 0, 1
                ),
            })
            total_points += float(completed)

        avg_velocity = round(
            total_points / len(completed_sprints), 1
        ) if completed_sprints else 0

        return {
            'velocity': avg_velocity,
            'sprints_analyzed': len(completed_sprints),
            'trend': sprint_data,
        }

    @staticmethod
    def get_sprint_stats(sprint: Sprint) -> dict:
        """Comprehensive sprint statistics."""
        items = WorkItem.objects.filter(sprint=sprint)

        total_points = items.aggregate(total=Sum('story_points'))['total'] or 0
        completed_items = items.filter(completed_at__isnull=False)
        completed_points = completed_items.aggregate(total=Sum('story_points'))['total'] or 0
        in_progress_items = items.filter(status__category='in_progress')

        total_estimated = items.aggregate(total=Sum('estimated_hours'))['total'] or 0
        total_actual = items.aggregate(total=Sum('actual_hours'))['total'] or 0

        return {
            'sprint_id': str(sprint.id),
            'sprint_name': sprint.name,
            'status': sprint.status,
            'duration_days': sprint.duration_days,
            'total_items': items.count(),
            'total_points': float(total_points),
            'completed_points': float(completed_points),
            'completion_pct': round(
                (float(completed_points) / float(total_points) * 100) if total_points else 0, 1
            ),
            'in_progress_count': in_progress_items.count(),
            'total_estimated_hours': float(total_estimated),
            'total_actual_hours': float(total_actual),
            'capacity_hours': float(sprint.total_capacity_hours),
            'capacity_utilization_pct': round(
                (float(total_actual) / float(sprint.total_capacity_hours) * 100)
                if sprint.total_capacity_hours else 0, 1
            ),
            'members': sprint.members.count(),
        }

    @staticmethod
    def calculate_sprint_velocity(project, sprint: Sprint) -> float:
        """Calculate how many points this team typically completes per sprint."""
        velocity_data = BurndownEngine.calculate_velocity(project)
        return velocity_data['velocity']
