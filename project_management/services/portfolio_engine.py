from datetime import date, timedelta
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from project_management.models import Project, WorkItem, Sprint, Milestone, WorkItemStatus

def get_portfolio_data(workspace_id):
    projects = Project.objects.filter(workspace_id=workspace_id, is_active=True)
    project_list = list(projects)

    done_status_ids = set(WorkItemStatus.objects.filter(category="done").values_list("id", flat=True))
    in_progress_status_ids = set(WorkItemStatus.objects.filter(category="in_progress").values_list("id", flat=True))
    review_status_ids = set(WorkItemStatus.objects.filter(category="review").values_list("id", flat=True))
    todo_status_ids = set(WorkItemStatus.objects.filter(category__in=("todo", "backlog")).values_list("id", flat=True))

    today = date.today()
    items_qs = WorkItem.objects.filter(project__in=project_list)

    items_by_project = {p.id: [] for p in project_list}
    for item in items_qs.only("id", "project_id", "status_id", "due_date", "completed_at",
                               "story_points", "estimated_hours", "actual_hours", "issue_type"):
        items_by_project.setdefault(item.project_id, []).append(item)

    projects_data = []
    total_overdue = 0
    total_completed = 0
    total_items = 0
    total_points_delivered = 0
    total_points_planned = 0
    at_risk_count = 0
    on_track_count = 0

    for p in project_list:
        p_items = items_by_project.get(p.id, [])
        total = len(p_items)
        total_items += total

        done = sum(1 for i in p_items if i.status_id in done_status_ids)
        completed = done
        total_completed += completed
        overdue = sum(1 for i in p_items if i.status_id not in done_status_ids and i.due_date and i.due_date.date() < today)
        total_overdue += overdue
        in_progress = sum(1 for i in p_items if i.status_id in in_progress_status_ids)
        review = sum(1 for i in p_items if i.status_id in review_status_ids)
        todo = sum(1 for i in p_items if i.status_id in todo_status_ids)

        points_delivered = sum(float(i.story_points or 0) for i in p_items if i.status_id in done_status_ids)
        points_planned = sum(float(i.story_points or 0) for i in p_items if i.status_id not in done_status_ids)
        total_points_delivered += points_delivered
        total_points_planned += points_planned

        hours_estimated = sum(float(i.estimated_hours or 0) for i in p_items)
        hours_logged = sum(float(i.actual_hours or 0) for i in p_items)

        # Health score: 0-100
        score = 100
        if total > 0:
            completion_rate = completed / total
            overdue_rate = overdue / max(total - completed, 1)
            score -= (1 - completion_rate) * 30
            score -= min(overdue_rate * 40, 40)
        if p.start_date and p.end_date:
            total_duration = (p.end_date - p.start_date).days
            elapsed = (today - p.start_date).days
            if total_duration > 0 and elapsed > 0:
                time_pct = elapsed / total_duration
                progress_pct = completed / max(total, 1)
                if progress_pct < time_pct - 0.15:
                    score -= 20
        score = max(0, min(100, int(score)))

        if score < 40:
            status_label = "critical"
            at_risk_count += 1
        elif score < 70:
            status_label = "at_risk"
            at_risk_count += 1
        else:
            status_label = "on_track"
            on_track_count += 1

        if p.end_date:
            days_remaining = (p.end_date - today).days
        else:
            days_remaining = None

        projects_data.append({
            "id": str(p.id),
            "name": p.name,
            "key": p.key,
            "color": p.color or "#6366f1",
            "is_active": p.is_active,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None,
            "days_remaining": days_remaining,
            "health_score": score,
            "health_status": status_label,
            "total_items": total,
            "completed_items": completed,
            "overdue_items": overdue,
            "in_progress_items": in_progress,
            "review_items": review,
            "todo_items": todo,
            "completion_pct": round((completed / total * 100) if total > 0 else 0, 1),
            "overdue_pct": round((overdue / max(total - completed, 1) * 100) if (total - completed) > 0 else 0, 1),
            "points_delivered": round(points_delivered, 1),
            "points_remaining": round(points_planned, 1),
            "hours_estimated": round(hours_estimated, 1),
            "hours_logged": round(hours_logged, 1),
        })

    portfolio_health = "healthy"
    if total_items > 0:
        completion_rate = total_completed / total_items
        overdue_rate = total_overdue / max(total_items - total_completed, 1)
        if completion_rate < 0.3 or overdue_rate > 0.5:
            portfolio_health = "critical"
        elif completion_rate < 0.5 or overdue_rate > 0.25:
            portfolio_health = "at_risk"

    item_type_breakdown = dict(
        items_qs.values("issue_type").annotate(count=Count("id")).values_list("issue_type", "count")
    )

    return {
        "portfolio_health": portfolio_health,
        "project_count": len(projects_data),
        "total_items": total_items,
        "total_completed": total_completed,
        "total_overdue": total_overdue,
        "total_points_delivered": round(total_points_delivered, 1),
        "total_points_remaining": round(total_points_planned, 1),
        "completion_pct": round((total_completed / total_items * 100) if total_items > 0 else 0, 1),
        "projects": projects_data,
        "summary": {
            "on_track": on_track_count,
            "at_risk": at_risk_count,
            "critical": at_risk_count - on_track_count if at_risk_count - on_track_count < 0 else 0,
        },
        "item_type_breakdown": item_type_breakdown,
    }
