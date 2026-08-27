from collections import defaultdict
from django.db.models import Sum, Q
from django.utils import timezone
from project_management.models import Sprint, WorkItem, SprintMember, WorkItemStatus
from project_management.services.burndown_engine import BurndownEngine


def get_sprint_recommendations(project_id, sprint_id=None):
    project_sprints = Sprint.objects.filter(project_id=project_id)

    current_sprint = None
    if sprint_id:
        current_sprint = Sprint.objects.filter(id=sprint_id, project_id=project_id).first()

    velocity = BurndownEngine.calculate_velocity(project_id, last_n_sprints=5)

    avg_velocity = velocity.get("velocity", 0)
    sprint_count = velocity.get("sprints_analyzed", 0)

    capacity_hours = 0
    if current_sprint:
        capacity_hours = float(current_sprint.total_capacity_hours or 0)
        if not capacity_hours:
            members = SprintMember.objects.filter(sprint=current_sprint)
            capacity_hours = sum(float(m.capacity_hours or 0) for m in members)
    else:
        latest = project_sprints.order_by("-end_date").first()
        if latest:
            capacity_hours = float(latest.total_capacity_hours or 0)
        if not capacity_hours:
            capacity_hours = 120

    done_status_ids = list(WorkItemStatus.objects.filter(category="done").values_list("id", flat=True))

    backlog_items = WorkItem.objects.filter(
        project_id=project_id,
        sprint__isnull=True,
    ).exclude(status_id__in=done_status_ids).select_related("status", "assignee").order_by("order", "created_at")

    if current_sprint:
        current_items = WorkItem.objects.filter(
            sprint=current_sprint,
        ).exclude(status_id__in=done_status_ids)
        current_total = sum(float(i.story_points or 0) for i in current_items)
        current_count = current_items.count()
    else:
        current_total = 0
        current_count = 0

    recommended = []
    running_points = 0
    running_hours = 0
    items_available = list(backlog_items)

    for item in items_available:
        pts = float(item.story_points or 1)
        est = float(item.estimated_hours or 2)
        if running_points + pts <= max(avg_velocity * 1.3, 10):
            if running_hours + est <= capacity_hours:
                recommended.append(_serialize_candidate(item))
                running_points += pts
                running_hours += est

    confidence = "high" if sprint_count >= 3 else "medium" if sprint_count >= 1 else "low"

    total_backlog = backlog_items.count()
    total_backlog_points = sum(float(i.story_points or 1) for i in items_available)

    return {
        "sprint_id": str(current_sprint.id) if current_sprint else None,
        "sprint_name": current_sprint.name if current_sprint else "Next Sprint",
        "velocity": avg_velocity,
        "sprints_analyzed": sprint_count,
        "confidence": confidence,
        "capacity_hours": capacity_hours,
        "current_sprint_points": round(current_total, 1),
        "current_sprint_items": current_count,
        "recommended_count": len(recommended),
        "recommended_points": round(running_points, 1),
        "recommended_hours": round(running_hours, 1),
        "backlog_remaining": total_backlog - len(recommended),
        "backlog_points_remaining": round(total_backlog_points - running_points, 1),
        "recommendations": recommended,
    }


def _serialize_candidate(item):
    assignee_data = None
    if item.assignee:
        assignee_data = {
            "id": str(item.assignee.id),
            "display_name": item.assignee.get_full_name() or item.assignee.username,
        }

    return {
        "id": str(item.id),
        "key": item.key,
        "title": item.title,
        "issue_type": item.issue_type,
        "story_points": float(item.story_points) if item.story_points else None,
        "estimated_hours": float(item.estimated_hours) if item.estimated_hours else None,
        "priority": getattr(item, "priority", "MEDIUM"),
        "status": item.status.name if item.status else "Unknown",
        "status_color": item.status.color if item.status else "gray",
        "assignee": assignee_data,
        "order": item.order or 0,
    }
