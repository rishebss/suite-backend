from collections import defaultdict
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from project_management.models import Notification, NotificationPreference


def get_smart_notifications(user, project_id=None, days=7):
    since = timezone.now() - timedelta(days=days)

    qs = Notification.objects.filter(
        recipient=user,
        created_at__gte=since,
    ).select_related("project", "work_item").order_by("-created_at")

    if project_id:
        qs = qs.filter(project_id=project_id)

    notifications = list(qs)

    groups = defaultdict(list)
    for n in notifications:
        key = (n.notification_type, n.project_id)
        groups[key].append(n)

    grouped_list = []
    for (notif_type, proj_id), items in groups.items():
        project_name = items[0].project.name if items[0].project else None
        latest = items[0]

        unread = sum(1 for i in items if not i.is_read)

        grouped_list.append({
            "group_key": f"{notif_type}-{proj_id}",
            "notification_type": notif_type,
            "project_id": str(proj_id) if proj_id else None,
            "project_name": project_name,
            "count": len(items),
            "unread_count": unread,
            "latest_title": latest.title,
            "latest_message": latest.message,
            "latest_created_at": latest.created_at.isoformat(),
            "notifications": [{
                "id": str(n.id),
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
                "work_item_id": str(n.work_item_id) if n.work_item_id else None,
                "work_item_key": n.work_item.key if n.work_item else None,
                "metadata": n.metadata,
            } for n in items],
        })

    grouped_list.sort(key=lambda g: g["latest_created_at"], reverse=True)

    preference = NotificationPreference.objects.filter(
        user=user, digest_enabled=True
    ).first()

    return {
        "total_notifications": len(notifications),
        "unread_count": sum(1 for n in notifications if not n.is_read),
        "group_count": len(grouped_list),
        "digest_enabled": preference.digest_enabled if preference else False,
        "digest_frequency": preference.digest_frequency if preference else "never",
        "groups": grouped_list,
    }
