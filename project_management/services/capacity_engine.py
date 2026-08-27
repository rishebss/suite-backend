from collections import defaultdict
from django.db.models import Sum, Count, Q
from project_management.models import Project, Sprint, SprintMember, WorkItem, WorkItemStatus, ProjectMember


def get_capacity_plan(project_id, sprint_id=None):
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {"error": "Project not found"}

    if sprint_id:
        sprint = Sprint.objects.filter(id=sprint_id, project=project).first()
    else:
        sprint = Sprint.objects.filter(project=project, status="ACTIVE").first()

    if not sprint:
        return {"error": "No active sprint found"}

    members = SprintMember.objects.filter(sprint=sprint).select_related("user")
    team_capacity = {}
    for m in members:
        user = m.user
        team_capacity[str(user.id)] = {
            "id": str(user.id),
            "display_name": user.get_full_name() or user.username,
            "capacity_hours": float(m.capacity_hours or 0),
            "assigned_hours": 0,
        }

    if not team_capacity:
        project_members = ProjectMember.objects.filter(project=project).select_related("user")
        for pm in project_members:
            uid = str(pm.user.id)
            if uid not in team_capacity:
                team_capacity[uid] = {
                    "id": uid,
                    "display_name": pm.user.get_full_name() or pm.user.username,
                    "capacity_hours": float(project.sprint_capacity_hours or 40),
                    "assigned_hours": 0,
                }

    sprint_items = WorkItem.objects.filter(sprint=sprint).select_related("assignee")
    for item in sprint_items:
        if item.assignee:
            uid = str(item.assignee_id)
            if uid in team_capacity:
                team_capacity[uid]["assigned_hours"] += float(item.estimated_hours or 2)
                team_capacity[uid]["item_count"] = team_capacity[uid].get("item_count", 0) + 1
                team_capacity[uid]["points"] = team_capacity[uid].get("points", 0) + float(item.story_points or 0)

    done_status_ids = list(WorkItemStatus.objects.filter(
        workflow__project=project, category="done"
    ).values_list("id", flat=True))

    unfinished = sprint_items.exclude(status_id__in=done_status_ids)
    unfinished_by_assignee = defaultdict(list)
    for item in unfinished:
        uid = str(item.assignee_id) if item.assignee else "unassigned"
        unfinished_by_assignee[uid].append({
            "id": str(item.id),
            "key": item.key,
            "title": item.title,
            "estimated_hours": float(item.estimated_hours or 2),
            "story_points": float(item.story_points or 0) if item.story_points else None,
        })

    suggestions = []
    backlog_items = WorkItem.objects.filter(
        project=project, sprint__isnull=True
    ).exclude(status_id__in=done_status_ids).order_by("order", "created_at")

    for uid, member in team_capacity.items():
        available = member["capacity_hours"] - member["assigned_hours"]
        if available > 0:
            for item in backlog_items:
                est = float(item.estimated_hours or 2)
                if est <= available:
                    suggestions.append({
                        "user_id": uid,
                        "user_name": member["display_name"],
                        "item_id": str(item.id),
                        "item_key": item.key,
                        "item_title": item.title,
                        "estimated_hours": est,
                        "story_points": float(item.story_points or 0) if item.story_points else None,
                    })
                    available -= est

    return {
        "sprint_id": str(sprint.id),
        "sprint_name": sprint.name,
        "project_id": str(project.id),
        "project_name": project.name,
        "team": list(team_capacity.values()),
        "total_capacity": sum(m["capacity_hours"] for m in team_capacity.values()),
        "total_assigned": sum(m["assigned_hours"] for m in team_capacity.values()),
        "unfinished_items": {k: v for k, v in unfinished_by_assignee.items()},
        "suggestions": suggestions,
    }
