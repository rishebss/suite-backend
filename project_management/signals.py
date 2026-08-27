from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from project_management.models import WorkItem, WorkItemActivityLog, log_activity


@receiver(pre_save, sender=WorkItem)
def track_work_item_changes(sender, instance, **kwargs):
    """Track all relevant field changes before save for activity logging."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_status = old.status
            instance._old_assignee = old.assignee
            instance._old_priority = old.priority
            instance._old_sprint = old.sprint
            instance._old_title = old.title
            instance._old_description = old.description
            instance._old_due_date = old.due_date
            instance._old_story_points = old.story_points
            instance._is_new = False
        except sender.DoesNotExist:
            _reset_old_fields(instance, new=True)
    else:
        _reset_old_fields(instance, new=True)


def _reset_old_fields(instance, new=False):
    instance._old_status = None
    instance._old_assignee = None
    instance._old_priority = None
    instance._old_sprint = None
    instance._old_title = None
    instance._old_description = None
    instance._old_due_date = None
    instance._old_story_points = None
    instance._is_new = new


@receiver(post_save, sender=WorkItem)
def log_work_item_changes(sender, instance, created, raw=False, **kwargs):
    """Log creation and all tracked changes to work items."""
    if raw:
        return

    if created:
        log_activity(
            work_item=instance,
            user=instance.reporter,
            activity_type='ITEM_CREATED',
            description=f"{instance.get_issue_type_display()} '{instance.title}' created",
            metadata={
                'issue_type': instance.issue_type,
                'key': instance.key,
            }
        )
        return

    old_status = getattr(instance, '_old_status', None)
    old_assignee = getattr(instance, '_old_assignee', None)
    old_priority = getattr(instance, '_old_priority', None)
    old_sprint = getattr(instance, '_old_sprint', None)
    old_title = getattr(instance, '_old_title', None)
    old_description = getattr(instance, '_old_description', None)
    old_due_date = getattr(instance, '_old_due_date', None)
    old_story_points = getattr(instance, '_old_story_points', None)
    user = instance.reporter or instance.assignee

    if old_status and old_status != instance.status:
        log_activity(
            work_item=instance, user=user,
            activity_type='STATUS_CHANGED',
            description=f"Status changed from '{old_status.name}' to '{instance.status.name}'",
            metadata={
                'old_status': str(old_status.id),
                'new_status': str(instance.status.id),
                'old_status_name': old_status.name,
                'new_status_name': instance.status.name,
            }
        )

    if old_assignee != instance.assignee:
        new_name = instance.assignee.get_full_name() if instance.assignee else 'Unassigned'
        log_activity(
            work_item=instance, user=user,
            activity_type='ASSIGNEE_CHANGED',
            description=f"Assignee changed to {new_name}",
            metadata={
                'old_assignee': str(old_assignee.id) if old_assignee else None,
                'new_assignee': str(instance.assignee.id) if instance.assignee else None,
            }
        )

    if old_priority != instance.priority:
        log_activity(
            work_item=instance, user=user,
            activity_type='PRIORITY_CHANGED',
            description=f"Priority changed from {old_priority} to {instance.priority}",
            metadata={
                'old_priority': old_priority,
                'new_priority': instance.priority,
            }
        )

    if old_sprint != instance.sprint:
        old_name = old_sprint.name if old_sprint else 'Backlog'
        new_name = instance.sprint.name if instance.sprint else 'Backlog'
        log_activity(
            work_item=instance, user=user,
            activity_type='SPRINT_CHANGED',
            description=f"Moved from '{old_name}' to '{new_name}'",
            metadata={
                'old_sprint': str(old_sprint.id) if old_sprint else None,
                'new_sprint': str(instance.sprint.id) if instance.sprint else None,
            }
        )

    if old_title != instance.title:
        log_activity(
            work_item=instance, user=user,
            activity_type='TITLE_CHANGED',
            description=f"Title changed from '{old_title}' to '{instance.title}'",
            metadata={'old_title': old_title, 'new_title': instance.title}
        )

    if old_description != instance.description:
        log_activity(
            work_item=instance, user=user,
            activity_type='DESCRIPTION_CHANGED',
            description=f"Description updated for {instance.key}",
            metadata={'changed': True}
        )

    if old_due_date != instance.due_date:
        log_activity(
            work_item=instance, user=user,
            activity_type='DUE_DATE_CHANGED',
            description=f"Due date changed",
            metadata={
                'old_due_date': old_due_date.isoformat() if old_due_date else None,
                'new_due_date': instance.due_date.isoformat() if instance.due_date else None,
            }
        )

    if old_story_points != instance.story_points:
        log_activity(
            work_item=instance, user=user,
            activity_type='STORY_POINTS_CHANGED',
            description=f"Story points: {old_story_points} → {instance.story_points}",
            metadata={
                'old_value': old_story_points,
                'new_value': instance.story_points,
            }
        )
