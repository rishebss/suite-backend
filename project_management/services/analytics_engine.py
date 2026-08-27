from collections import defaultdict
from datetime import timedelta
from django.db.models import Count, Q, Avg, Min, Max
from django.utils import timezone
from project_management.models import WorkItem, WorkItemActivityLog, WorkItemStatus, Sprint


def get_time_in_status(project_id, days=90):
    since = timezone.now() - timedelta(days=days)
    statuses = {str(s.id): s for s in WorkItemStatus.objects.filter(workflow__project_id=project_id)}

    logs = WorkItemActivityLog.objects.filter(
        work_item__project_id=project_id,
        activity_type="STATUS_CHANGED",
        created_at__gte=since,
    ).order_by("work_item", "created_at").values("work_item", "created_at", "metadata")

    time_in_status = defaultdict(lambda: defaultdict(float))
    item_durations = defaultdict(list)

    grouped = defaultdict(list)
    for log in logs:
        grouped[log["work_item"]].append(log)

    for item_id, entries in grouped.items():
        for i in range(len(entries) - 1):
            current = entries[i]
            next_entry = entries[i + 1]
            meta = current.get("metadata") or {}
            new_status_id = meta.get("new_status")
            if not new_status_id:
                continue
            duration = (next_entry["created_at"] - current["created_at"]).total_seconds() / 3600
            time_in_status[str(item_id)][str(new_status_id)] += duration
        last = entries[-1]
        meta = last.get("metadata") or {}
        new_status_id = meta.get("new_status")
        if new_status_id:
            duration = (timezone.now() - last["created_at"]).total_seconds() / 3600
            time_in_status[str(item_id)][str(new_status_id)] += duration

    status_hours = defaultdict(list)
    for item_id, status_data in time_in_status.items():
        for status_id, hours in status_data.items():
            status_hours[status_id].append(hours)

    status_summary = []
    for status_id, hours_list in status_hours.items():
        s = statuses.get(status_id)
        status_summary.append({
            "status_id": status_id,
            "status_name": s.name if s else "Unknown",
            "status_color": s.color if s else "gray",
            "status_category": s.category if s else "unknown",
            "avg_hours": round(sum(hours_list) / len(hours_list), 1),
            "total_hours": round(sum(hours_list), 1),
            "item_count": len(hours_list),
            "min_hours": round(min(hours_list), 1),
            "max_hours": round(max(hours_list), 1),
        })

    status_summary.sort(key=lambda x: x.get("order", 99) if (s := statuses.get(x["status_id"])) else 99)

    return {
        "period_days": days,
        "statuses": status_summary,
        "total_items_analyzed": len(grouped),
    }


def get_cycle_time(project_id, days=90):
    since = timezone.now() - timedelta(days=days)

    done_status_ids = list(WorkItemStatus.objects.filter(
        workflow__project_id=project_id, category="done"
    ).values_list("id", flat=True))

    completed_items = WorkItem.objects.filter(
        project_id=project_id,
        status_id__in=done_status_ids,
        completed_at__gte=since,
    ).only("id", "key", "title", "created_at", "completed_at", "issue_type")

    results = []
    for item in completed_items:
        lead_time = None
        if item.completed_at and item.created_at:
            lead_time = round((item.completed_at - item.created_at).total_seconds() / 3600, 1)

        first_log = WorkItemActivityLog.objects.filter(
            work_item=item, activity_type="STATUS_CHANGED"
        ).order_by("created_at").first()

        cycle_time = None
        if first_log and item.completed_at:
            cycle_time = round((item.completed_at - first_log.created_at).total_seconds() / 3600, 1)

        results.append({
            "id": str(item.id),
            "key": item.key,
            "title": item.title,
            "issue_type": item.issue_type,
            "lead_time_hours": lead_time,
            "cycle_time_hours": cycle_time,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        })

    avg_lead_time = round(sum(r["lead_time_hours"] or 0 for r in results) / len(results), 1) if results else 0
    avg_cycle_time = round(sum(r["cycle_time_hours"] or 0 for r in results) / len(results), 1) if results else 0

    return {
        "period_days": days,
        "total_completed": len(results),
        "avg_lead_time_hours": avg_lead_time,
        "avg_cycle_time_hours": avg_cycle_time,
        "avg_lead_time_days": round(avg_lead_time / 24, 1),
        "avg_cycle_time_days": round(avg_cycle_time / 24, 1),
        "items": sorted(results, key=lambda x: x["cycle_time_hours"] or 0, reverse=True)[:50],
    }
