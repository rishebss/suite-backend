from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import CalendarTodo
from .serializers import CalendarTodoSerializer


class CalendarTodoViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarTodoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role in ("Superadmin", "Admin"):
            qs = CalendarTodo.objects.all()
        else:
            qs = CalendarTodo.objects.filter(
                Q(assigned_to=user)
                | Q(attendees__user=user)
                | Q(todo_type="event")
                | Q(user=user)
            )

        qs = (
            qs.select_related("assigned_to", "contact", "pipeline", "user")
            .prefetch_related("attendees__user")
            .distinct()
        )

        todo_type = self.request.query_params.get("todo_type")
        if todo_type:
            qs = qs.filter(todo_type=todo_type)

        pipeline = self.request.query_params.get("pipeline")
        if pipeline:
            qs = qs.filter(pipeline_id=pipeline)

        crm = self.request.query_params.get("crm")
        if crm:
            qs = qs.filter(crm_id=crm)

        contact = self.request.query_params.get("contact")
        if contact:
            qs = qs.filter(contact_id=contact)

        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start and end:
            base_q = Q(start__gte=start, start__lte=end)
            event_span_q = Q(
                todo_type="event", start__lt=end, end__isnull=False, end__gte=start
            )
            qs = qs.filter(base_q | event_span_q)
        else:
            if start:
                qs = qs.filter(start__gte=start)
            if end:
                qs = qs.filter(start__lte=end)

        self._persist_time_statuses(qs)

        return qs.order_by("-updated_at")

    def _persist_time_statuses(self, qs):
        now = timezone.now()
        ids = list(qs.values_list("id", flat=True))
        if not ids:
            return
        CalendarTodo.objects.filter(
            id__in=ids,
            todo_type="task",
            start__lt=now,
        ).exclude(status__in=("completed", "on_hold", "approved", "canceled")).update(
            status="overdue"
        )
        CalendarTodo.objects.filter(
            id__in=ids, todo_type="task", status="overdue", start__gt=now
        ).update(status="assigned")
        CalendarTodo.objects.filter(
            id__in=ids,
            todo_type="followup",
            start__lt=now,
            status="follow_up",
        ).update(status="failed")
        CalendarTodo.objects.filter(
            id__in=ids,
            todo_type="followup",
            status="failed",
            start__gt=now,
        ).update(status="follow_up", followup_failed=None)

    def perform_create(self, serializer):
        validated = {}
        if self.request.user.role not in ("Superadmin", "Admin"):
            validated["assigned_to"] = self.request.user
        serializer.save(user=self.request.user, **validated)

    def _check_todo_permission(self, instance, action):
        user = self.request.user
        is_creator = instance.user == user

        if instance.todo_type == "task":
            if action == "update" and not (is_creator or instance.assigned_to == user):
                raise PermissionDenied(
                    "Only the creator or assigned user can update this task."
                )
            if action == "delete" and not is_creator:
                raise PermissionDenied("Only the creator can delete this task.")
            return

        if instance.todo_type == "followup":
            if action == "update" and not (is_creator or instance.assigned_to == user):
                raise PermissionDenied(
                    "Only the creator or assigned user can update this follow-up."
                )
            if action == "delete" and not is_creator:
                raise PermissionDenied("Only the creator can delete this follow-up.")
            return

        if instance.todo_type == "event" and not is_creator:
            raise PermissionDenied("Only the creator can modify this event.")

    def perform_update(self, serializer):
        self._check_todo_permission(serializer.instance, "update")
        serializer.save()

    def perform_destroy(self, instance):
        self._check_todo_permission(instance, "delete")
        instance.delete()
