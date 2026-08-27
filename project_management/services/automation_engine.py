import json
import logging
from django.utils import timezone
from project_management.models import (
    AutomationRule, WorkItem, WorkItemActivityLog,
    Notification, WorkItemLink,
)

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Evaluates automation rules and executes actions."""

    TRIGGER_MAP = {
        'ITEM_CREATED': 'on_item_created',
        'ITEM_UPDATED': 'on_item_updated',
        'STATUS_CHANGED': 'on_status_changed',
        'ASSIGNEE_CHANGED': 'on_assignee_changed',
        'SPRINT_STARTED': 'on_sprint_started',
        'SPRINT_ENDED': 'on_sprint_ended',
    }

    @classmethod
    def evaluate(cls, trigger_event, work_item=None, context=None):
        rules = AutomationRule.objects.filter(
            trigger_event=trigger_event,
            is_enabled=True,
        ).select_related('project')
        if work_item and work_item.project_id:
            rules = rules.filter(
                models.Q(project=work_item.project) | models.Q(project__isnull=True)
            )
        for rule in rules:
            try:
                handler = getattr(cls, cls.TRIGGER_MAP.get(trigger_event, ''), None)
                if handler:
                    handler(rule, work_item, context or {})
            except Exception as e:
                logger.error(f"Automation rule {rule.id} failed: {e}")

    @staticmethod
    def _matches_condition(rule, work_item, context):
        conditions = rule.conditions
        if not conditions:
            return True
        if isinstance(conditions, str):
            conditions = json.loads(conditions)
        field = conditions.get('field')
        operator = conditions.get('operator', 'equals')
        value = conditions.get('value')
        if not field:
            return True
        actual = getattr(work_item, field, None) or context.get(field)
        if operator == 'equals':
            return str(actual) == str(value)
        elif operator == 'not_equals':
            return str(actual) != str(value)
        elif operator == 'contains':
            return value in str(actual)
        elif operator == 'gt':
            return (actual or 0) > float(value)
        elif operator == 'lt':
            return (actual or 0) < float(value)
        return True

    @classmethod
    def on_item_created(cls, rule, work_item, context):
        if not cls._matches_condition(rule, work_item, context):
            return
        cls._execute_actions(rule, work_item)

    @classmethod
    def on_status_changed(cls, rule, work_item, context):
        if not cls._matches_condition(rule, work_item, context):
            return
        cls._execute_actions(rule, work_item)

    @classmethod
    def on_assignee_changed(cls, rule, work_item, context):
        if not cls._matches_condition(rule, work_item, context):
            return
        cls._execute_actions(rule, work_item)

    @classmethod
    def on_item_updated(cls, rule, work_item, context):
        if not cls._matches_condition(rule, work_item, context):
            return
        cls._execute_actions(rule, work_item)

    @classmethod
    def on_sprint_started(cls, rule, work_item, context):
        cls._execute_actions(rule, work_item)

    @classmethod
    def on_sprint_ended(cls, rule, work_item, context):
        cls._execute_actions(rule, work_item)

    @staticmethod
    def _execute_actions(rule, work_item):
        actions = rule.actions
        if isinstance(actions, str):
            actions = json.loads(actions)
        action_type = actions.get('action_type')
        if action_type == 'ASSIGN':
            assignee_id = actions.get('assignee_id')
            if assignee_id and work_item:
                work_item.assignee_id = assignee_id
                work_item.save(update_fields=['assignee'])
        elif action_type == 'CHANGE_STATUS':
            status_id = actions.get('status_id')
            if status_id and work_item:
                work_item.status_id = status_id
                work_item.save(update_fields=['status'])
        elif action_type == 'CHANGE_PRIORITY':
            priority = actions.get('priority')
            if priority and work_item:
                work_item.priority = priority
                work_item.save(update_fields=['priority'])
        elif action_type == 'ADD_LABEL':
            label = actions.get('label')
            if label and work_item:
                labels = list(work_item.labels or [])
                if label not in labels:
                    labels.append(label)
                    work_item.labels = labels
                    work_item.save(update_fields=['labels'])
        elif action_type == 'CREATE_SUBTASK':
            title = actions.get('title', 'Auto-created subtask')
            if work_item:
                default_status = work_item.project.workflow.statuses.first() if work_item.project.workflow else None
                WorkItem.objects.create(
                    project=work_item.project,
                    parent=work_item,
                    title=title,
                    issue_type='SUBTASK',
                    status=default_status,
                )
        elif action_type == 'NOTIFY':
            Notification.objects.create(
                recipient_id=actions.get('recipient_id', work_item.assignee_id) if work_item else None,
                title=actions.get('title', 'Automation Notification'),
                body=actions.get('body', ''),
                notification_type='AUTOMATION',
            )
        elif action_type == 'LOG_ACTIVITY':
            if work_item:
                WorkItemActivityLog.objects.create(
                    work_item=work_item,
                    activity_type='AUTOMATION',
                    description=actions.get('message', 'Automation rule executed'),
                )
