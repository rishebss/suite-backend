from datetime import date, timedelta
from django.db.models import Count, Sum, Q
from project_management.models import Project, Sprint, SprintMember, WorkItem, ProjectMember, WorkItemTimeLog


def get_workload(workspace_id=None, department_id=None, from_date=None, to_date=None):
    """Return workload data: users, their assigned items, logged hours, and utilization."""
    today = date.today()
    from_date = from_date or today - timedelta(days=30)
    to_date = to_date or today + timedelta(days=30)

    memberships = ProjectMember.objects.select_related(
        'user', 'project__workspace'
    ).filter(
        project__is_active=True,
    )
    if workspace_id:
        memberships = memberships.filter(project__workspace_id=workspace_id)
    if department_id:
        memberships = memberships.filter(user__departments=department_id)

    user_map = {}
    for m in memberships:
        uid = str(m.user.id)
        if uid not in user_map:
            user_map[uid] = {
                'user_id': uid,
                'email': m.user.email,
                'full_name': m.user.get_full_name() or m.user.email,
                'projects': [],
                'total_assigned': 0,
                'total_logged_hours': 0.0,
                'total_capacity_hours': 0.0,
            }
        user_map[uid]['projects'].append({
            'project_id': str(m.project.id),
            'project_name': m.project.name,
            'project_key': m.project.key,
            'role': m.role,
        })

    user_ids = list(user_map.keys())

    assigned_items = WorkItem.objects.filter(
        assignee_id__in=user_ids,
        status__category__in=['todo', 'in_progress', 'blocked'],
    ).values('assignee_id').annotate(count=Count('id'))

    for row in assigned_items:
        uid = str(row['assignee_id'])
        if uid in user_map:
            user_map[uid]['total_assigned'] = row['count']

    time_logs = WorkItemTimeLog.objects.filter(
        user_id__in=user_ids,
        date__gte=from_date,
        date__lte=to_date,
    ).values('user_id').annotate(total=Sum('hours'))

    for row in time_logs:
        uid = str(row['user_id'])
        if uid in user_map:
            user_map[uid]['total_logged_hours'] = float(row['total'] or 0)

    sprints = Sprint.objects.filter(
        status='ACTIVE',
        members__user_id__in=user_ids,
    ).values('members__user_id').annotate(
        cap=Sum('members__capacity_hours')
    )
    for row in sprints:
        uid = str(row['members__user_id'])
        if uid in user_map:
            user_map[uid]['total_capacity_hours'] = float(row['cap'] or 0)

    results = []
    for uid, data in user_map.items():
        cap = data['total_capacity_hours'] or 40
        utilization = min(round((data['total_logged_hours'] / cap) * 100, 1), 200)
        data['utilization_pct'] = utilization
        data['capacity_hours'] = round(cap, 1)
        data['logged_hours'] = round(data['total_logged_hours'], 1)
        data['status'] = 'over' if utilization > 100 else 'warning' if utilization > 80 else 'healthy'
        results.append(data)

    results.sort(key=lambda x: x['utilization_pct'], reverse=True)
    return results


def get_project_workload(project_id):
    """Return workload for all members of a specific project."""
    members = ProjectMember.objects.filter(project_id=project_id).select_related('user')
    user_ids = [str(m.user.id) for m in members]
    today = date.today()

    items = WorkItem.objects.filter(
        project_id=project_id,
        assignee_id__in=user_ids,
        status__category__in=['todo', 'in_progress'],
    ).values('assignee_id', 'status__category').annotate(count=Count('id'))

    item_map = {}
    for row in items:
        uid = str(row['assignee_id'])
        item_map.setdefault(uid, {'todo': 0, 'in_progress': 0})[row['status__category']] = row['count']

    time_logs = WorkItemTimeLog.objects.filter(
        user_id__in=user_ids,
        date=today,
    ).values('user_id').annotate(total=Sum('hours'))

    log_map = {str(r['user_id']): float(r['total']) for r in time_logs}

    result = []
    for m in members:
        uid = str(m.user.id)
        rd = item_map.get(uid, {})
        result.append({
            'user_id': uid,
            'full_name': m.user.get_full_name() or m.user.email,
            'email': m.user.email,
            'role': m.role,
            'todo_items': rd.get('todo', 0),
            'in_progress_items': rd.get('in_progress', 0),
            'today_logged_hours': log_map.get(uid, 0),
        })
    return result
