from datetime import timedelta
from django.utils import timezone
from project_management.models import (
    WorkItem, SLAPolicy, log_activity, WorkItemActivityLog
)

DAY_KEYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']


class SLAEngine:
    """Manages SLA timers for support tickets — start, pause, resume, check, escalate."""

    @staticmethod
    def _parse_business_hours(policy):
        """Parse business_hours config into a dict of day -> (start_minutes, end_minutes)."""
        config = policy.business_hours or {}
        tz_name = config.get('timezone', 'UTC')
        days_config = config.get('days', {})
        parsed = {}
        for day_key in DAY_KEYS:
            entry = days_config.get(day_key)
            if entry:
                try:
                    if isinstance(entry, list) and len(entry) == 2:
                        start_h, start_m = map(int, entry[0].split(':'))
                        end_h, end_m = map(int, entry[1].split(':'))
                    elif isinstance(entry, dict):
                        start_h, start_m = map(int, entry['start'].split(':'))
                        end_h, end_m = map(int, entry['end'].split(':'))
                    else:
                        continue
                    parsed[day_key] = (start_h * 60 + start_m, end_h * 60 + end_m)
                except (ValueError, KeyError):
                    continue
        return parsed, tz_name

    @staticmethod
    def _add_business_minutes(start_dt, minutes, parsed_hours):
        """Add `minutes` of business time to start_dt."""
        if not parsed_hours:
            return start_dt + timedelta(minutes=minutes)

        current = start_dt
        remaining = minutes

        while remaining > 0:
            dow = current.weekday()
            day_key = DAY_KEYS[dow]
            hours = parsed_hours.get(day_key)
            if not hours:
                current += timedelta(days=1)
                current = current.replace(hour=0, minute=0, second=0, microsecond=0)
                continue

            biz_start, biz_end = hours
            day_start = current.replace(hour=biz_start // 60, minute=biz_start % 60, second=0, microsecond=0)
            day_end = current.replace(hour=biz_end // 60, minute=biz_end % 60, second=0, microsecond=0)

            if current < day_start:
                current = day_start

            if current < day_end:
                available = (day_end - current).total_seconds() / 60
                if available >= remaining:
                    current += timedelta(minutes=remaining)
                    remaining = 0
                else:
                    remaining -= available
                    current = day_end

            if remaining > 0:
                current += timedelta(days=1)
                current = current.replace(hour=0, minute=0, second=0, microsecond=0)

        return current

    @staticmethod
    def _count_business_minutes_between(start_dt, end_dt, parsed_hours):
        """Count business minutes between two datetimes."""
        if not parsed_hours:
            return (end_dt - start_dt).total_seconds() / 60

        total = 0.0
        current = start_dt

        while current < end_dt:
            dow = current.weekday()
            day_key = DAY_KEYS[dow]
            hours = parsed_hours.get(day_key)
            if not hours:
                current += timedelta(days=1)
                current = current.replace(hour=0, minute=0, second=0, microsecond=0)
                continue

            biz_start, biz_end = hours
            day_start = current.replace(hour=biz_start // 60, minute=biz_start % 60, second=0, microsecond=0)
            day_end = current.replace(hour=biz_end // 60, minute=biz_end % 60, second=0, microsecond=0)

            effective_start = max(current, day_start)
            effective_end = min(end_dt, day_end)

            if effective_start < effective_end:
                total += (effective_end - effective_start).total_seconds() / 60

            current += timedelta(days=1)
            current = current.replace(hour=0, minute=0, second=0, microsecond=0)

        return total

    @staticmethod
    def _execute_escalation(work_item, policy, breach_type):
        """Execute escalation rules defined on the SLA policy."""
        rules = policy.escalation_rules or []
        for rule in rules:
            action = rule.get('action', 'notify')
            notify_role = rule.get('notify_role')

            log_activity(
                work_item=work_item,
                user=None,
                activity_type='SLA_BREACHED' if breach_type == 'breach' else 'SLA_WARNING',
                description=(
                    f"Escalation triggered for {work_item.key}: {action} "
                    f"{f'-> {notify_role}' if notify_role else ''}"
                ),
                metadata={
                    'policy': policy.name,
                    'breach_type': breach_type,
                    'action': action,
                    'notify_role': notify_role,
                    'rule': rule,
                }
            )

    @staticmethod
    def start_sla(work_item: WorkItem):
        """Initialize SLA timers when a ticket is created or assigned a policy."""
        if not work_item.sla_policy:
            return

        policy = work_item.sla_policy
        now = timezone.now()
        parsed_hours, _ = SLAEngine._parse_business_hours(policy)

        if policy.business_hours_only and parsed_hours:
            work_item.sla_response_due_at = SLAEngine._add_business_minutes(
                now, policy.response_time_minutes, parsed_hours
            )
            work_item.sla_resolution_due_at = SLAEngine._add_business_minutes(
                now, policy.resolution_time_minutes, parsed_hours
            )
        else:
            work_item.sla_response_due_at = now + timedelta(minutes=policy.response_time_minutes)
            work_item.sla_resolution_due_at = now + timedelta(minutes=policy.resolution_time_minutes)

        work_item.sla_status = 'WITHIN_SLA'
        work_item.save(update_fields=[
            'sla_response_due_at', 'sla_resolution_due_at', 'sla_status'
        ])

    @staticmethod
    def pause_sla(work_item: WorkItem):
        """Pause SLA timer when status changes to 'Waiting on Customer'."""
        if work_item.sla_status in ['BREACHED', None]:
            return

        now = timezone.now()
        if work_item.sla_response_due_at:
            elapsed = now - timezone.now()
            work_item.sla_response_due_at += elapsed
        if work_item.sla_resolution_due_at:
            elapsed = now - timezone.now()
            work_item.sla_resolution_due_at += elapsed
        work_item.sla_status = 'PAUSED'
        work_item.save(update_fields=[
            'sla_response_due_at', 'sla_resolution_due_at', 'sla_status'
        ])

    @staticmethod
    def resume_sla(work_item: WorkItem):
        """Resume SLA timer when customer responds or status leaves 'Waiting on Customer'."""
        if work_item.sla_status != 'PAUSED':
            return

        work_item.sla_status = 'WITHIN_SLA'
        work_item.save(update_fields=['sla_status'])

    @staticmethod
    def mark_first_response(work_item: WorkItem, user):
        """Record first agent response and log activity."""
        if work_item.first_response_at:
            return

        work_item.first_response_at = timezone.now()
        work_item.save(update_fields=['first_response_at'])

        log_activity(
            work_item=work_item,
            user=user,
            activity_type='CUSTOMER_RESPONDED',
            description=f"First response by {user.get_full_name()}",
            metadata={
                'response_time_minutes': SLAEngine._calculate_response_time(work_item),
            }
        )

    @staticmethod
    def check_sla(work_item: WorkItem) -> dict:
        """Check SLA status of a work item. Returns status details."""
        if not work_item.sla_policy or not work_item.sla_status:
            return {'status': 'NO_SLA', 'breached': False}

        if work_item.sla_status in ['PAUSED', 'BREACHED']:
            return {
                'status': work_item.sla_status,
                'breached': work_item.sla_status == 'BREACHED',
            }

        policy = work_item.sla_policy
        now = timezone.now()
        breached = False
        warning = False

        if work_item.sla_response_due_at and not work_item.first_response_at:
            remaining_response = (work_item.sla_response_due_at - now).total_seconds()
            if remaining_response <= 0:
                breached = True
            elif remaining_response <= policy.response_time_minutes * 60 * 0.2:
                warning = True

        if work_item.sla_resolution_due_at and work_item.status.category != 'done':
            remaining_resolution = (work_item.sla_resolution_due_at - now).total_seconds()
            if remaining_resolution <= 0:
                breached = True
            elif remaining_resolution <= policy.resolution_time_minutes * 60 * 0.2:
                warning = True

        if breached and work_item.sla_status != 'BREACHED':
            work_item.sla_status = 'BREACHED'
            work_item.save(update_fields=['sla_status'])
            log_activity(
                work_item=work_item,
                user=None,
                activity_type='SLA_BREACHED',
                description=f"SLA breached for ticket {work_item.key}",
                metadata={'policy': policy.name}
            )
            SLAEngine._execute_escalation(work_item, policy, 'breach')
            return {'status': 'BREACHED', 'breached': True}

        if warning and work_item.sla_status != 'WARNING':
            work_item.sla_status = 'WARNING'
            work_item.save(update_fields=['sla_status'])
            log_activity(
                work_item=work_item,
                user=None,
                activity_type='SLA_WARNING',
                description=f"SLA warning for ticket {work_item.key} — approaching breach",
                metadata={'policy': policy.name}
            )
            SLAEngine._execute_escalation(work_item, policy, 'warning')
            return {'status': 'WARNING', 'breached': False}

        return {
            'status': work_item.sla_status or 'WITHIN_SLA',
            'breached': False,
            'response_remaining_minutes': SLAEngine._minutes_until(
                work_item.sla_response_due_at
            ) if work_item.sla_response_due_at and not work_item.first_response_at else None,
            'resolution_remaining_minutes': SLAEngine._minutes_until(
                work_item.sla_resolution_due_at
            ) if work_item.sla_resolution_due_at else None,
        }

    @staticmethod
    def check_all_active():
        """Check SLA for all active tickets. Call periodically (e.g., via cron/management command)."""
        tickets = WorkItem.objects.filter(
            issue_type='TICKET',
            sla_policy__isnull=False,
        ).exclude(sla_status='BREACHED')

        results = {'checked': 0, 'breached': 0, 'warnings': 0, 'escalations': 0}
        for ticket in tickets:
            result = SLAEngine.check_sla(ticket)
            results['checked'] += 1
            if result['breached']:
                results['breached'] += 1
            elif result['status'] == 'WARNING':
                results['warnings'] += 1
        return results

    @staticmethod
    def _minutes_until(dt):
        if not dt:
            return None
        remaining = (dt - timezone.now()).total_seconds()
        return round(max(remaining, 0) / 60, 1)

    @staticmethod
    def _calculate_response_time(work_item):
        if not work_item.first_response_at or not work_item.created_at:
            return None
        delta = work_item.first_response_at - work_item.created_at
        return round(delta.total_seconds() / 60, 1)
