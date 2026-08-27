from django.db.models import Prefetch, Q
from django.utils import timezone
from project_management.models import (
    Workspace, Project, WorkItem, Milestone, WorkItemLink, WorkItemStatus,
)

def get_roadmap_data(workspace_id, project_ids=None, user=None):
    workspace = Workspace.objects.filter(id=workspace_id).first()
    if not workspace:
        return {"projects": [], "milestones": [], "dependencies": []}

    projects_qs = Project.objects.filter(workspace=workspace).select_related("default_workflow")
    if project_ids:
        projects_qs = projects_qs.filter(id__in=project_ids)

    projects_data = []
    all_milestones = []
    all_deps = []

    done_statuses = list(WorkItemStatus.objects.filter(category="done").values_list("id", flat=True))

    for project in projects_qs:
        epics = WorkItem.objects.filter(
            project=project, issue_type="EPIC"
        ).select_related("status", "assignee").only(
            "id", "key", "title", "issue_type", "start_date", "due_date",
            "completed_at", "status", "assignee", "project", "order", "story_points",
        ).order_by("order", "created_at")

        children = WorkItem.objects.filter(
            project=project, epic__isnull=False
        ).exclude(issue_type="EPIC").select_related("status", "assignee").only(
            "id", "key", "title", "issue_type", "start_date", "due_date",
            "completed_at", "status", "assignee", "epic", "project", "story_points",
        )

        child_map = {}
        for c in children:
            child_map.setdefault(str(c.epic_id), []).append(_serialize_item(c, done_statuses, "child"))

        epic_list = []
        for e in epics:
            eid = str(e.id)
            epic_list.append({
                **_serialize_item(e, done_statuses, "epic"),
                "children": child_map.get(eid, []),
            })

        projects_data.append({
            "id": str(project.id),
            "name": project.name,
            "key": project.key,
            "color": project.color or "#6366f1",
            "epics": epic_list,
            "epic_count": len(epic_list),
        })

        milestones = Milestone.objects.filter(
            Q(project=project) | Q(work_item__project=project)
        ).distinct().only(
            "id", "name", "milestone_type", "target_date", "completed_date",
            "status", "project",
        )
        for m in milestones:
            all_milestones.append({
                "id": str(m.id),
                "name": m.name,
                "type": m.milestone_type,
                "target_date": m.target_date.isoformat() if m.target_date else None,
                "completed_date": m.completed_date.isoformat() if m.completed_date else None,
                "status": m.status,
                "project": str(m.project_id) if m.project_id else str(project.id),
                "project_name": project.name,
            })

        links = WorkItemLink.objects.filter(
            Q(source_item__project=project) | Q(target_item__project=project),
            relation_type__in=("blocks", "blocked_by"),
        ).select_related("source_item", "target_item").only(
            "id", "source_item", "target_item", "relation_type",
        )
        for link in links:
            all_deps.append({
                "id": str(link.id),
                "source_id": str(link.source_item_id),
                "target_id": str(link.target_item_id),
                "type": link.relation_type,
            })

    return {
        "projects": projects_data,
        "milestones": all_milestones,
        "dependencies": all_deps,
        "done_status_ids": done_statuses,
    }


def _serialize_item(item, done_status_ids, role):
    status_name = item.status.name if item.status else "Unknown"
    status_color = item.status.color if item.status else "gray"
    status_category = item.status.category if item.status else "todo"
    is_done = item.status_id in done_status_ids if item.status_id else False

    assignee_data = None
    if item.assignee:
        assignee_data = {
            "id": str(item.assignee.id),
            "display_name": getattr(item.assignee, "display_name", None) or item.assignee.get_full_name() or item.assignee.username,
            "avatar_url": getattr(item.assignee, "avatar_url", None) or "",
        }

    return {
        "id": str(item.id),
        "key": item.key,
        "title": item.title,
        "issue_type": item.issue_type,
        "start_date": item.start_date.isoformat() if item.start_date else None,
        "due_date": item.due_date.isoformat() if item.due_date else None,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "status": status_name,
        "status_category": status_category,
        "status_color": status_color,
        "is_done": is_done,
        "assignee": assignee_data,
        "story_points": float(item.story_points) if item.story_points else None,
        "role": role,
    }
