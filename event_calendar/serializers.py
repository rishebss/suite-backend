from django.utils import timezone
from rest_framework import serializers
from .models import CalendarTodo, MeetingAttendee


class MeetingAttendeeSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = MeetingAttendee
        fields = ["id", "user", "user_name"]
        read_only_fields = ["id"]

    def get_user_name(self, obj):
        user = obj.user
        if user.first_name:
            return f"{user.first_name} {user.last_name or ''}".strip()
        return user.email


class CalendarTodoSerializer(serializers.ModelSerializer):
    attendees = MeetingAttendeeSerializer(many=True, read_only=True)
    attendee_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    assigned_to_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    contact_phone = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()
    pipeline_name = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = CalendarTodo
        fields = [
            "id",
            "user",
            "todo_type",
            "title",
            "description",
            "priority",
            "start",
            "end",
            "contact",
            "pipeline",
            "crm",
            "pipeline_name",
            "location",
            "status",
            "hold_reason",
            "extension_request",
            "completion_remarks",
            "followup_cancellation",
            "followup_failed",
            "assigned_to",
            "attendees",
            "attendee_ids",
            "assigned_to_name",
            "contact_name",
            "contact_phone",
            "contact_email",
            "user_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return None
        user = obj.assigned_to
        if user.first_name:
            return f"{user.first_name} {user.last_name or ''}".strip()
        return user.email

    def get_contact_name(self, obj):
        if not obj.contact:
            return None
        return obj.contact.name or obj.contact.email

    def get_contact_phone(self, obj):
        if not obj.contact:
            return None
        return obj.contact.phone

    def get_contact_email(self, obj):
        if not obj.contact:
            return None
        return obj.contact.email

    def get_pipeline_name(self, obj):
        if not obj.pipeline:
            return None
        return obj.pipeline.name

    def get_user_name(self, obj):
        user = obj.user
        if user.first_name:
            return f"{user.first_name} {user.last_name or ''}".strip()
        return user.email

    def validate(self, data):
        todo_type = data.get("todo_type", getattr(self.instance, "todo_type", None))

        start_missing = "start" in data and not data.get("start")

        if todo_type == "task":
            if start_missing or (self.instance is None and not data.get("start")):
                raise serializers.ValidationError(
                    {"start": "Deadline is required for tasks."}
                )
            status = data.get("status")
            valid_statuses = [s[0] for s in CalendarTodo.TASK_STATUS_CHOICES]
            if status and status not in valid_statuses:
                raise serializers.ValidationError(
                    {"status": f"Invalid status '{status}' for tasks."}
                )

            request = self.context.get("request")
            if self.instance is not None and status and request:
                is_creator = self.instance.user == request.user
                if not is_creator and status in ("approved", "canceled"):
                    raise serializers.ValidationError(
                        {"status": "Only the creator can set this status."}
                    )
                if status == "completed" and not (
                    (data.get("completion_remarks") or "").strip()
                ):
                    raise serializers.ValidationError(
                        {
                            "completion_remarks": "Completion remarks are required when completing a task."
                        }
                    )
                if (
                    status == "on_hold"
                    and not is_creator
                    and not (data.get("hold_reason") or "").strip()
                ):
                    raise serializers.ValidationError(
                        {
                            "hold_reason": "Hold reason is required when putting a task on hold."
                        }
                    )

        elif todo_type == "event":
            if not data.get("description"):
                raise serializers.ValidationError(
                    {"description": "Description is required for events."}
                )
            if start_missing or (self.instance is None and not data.get("start")):
                raise serializers.ValidationError(
                    {"start": "Date is required for events."}
                )
            status = data.get("status")
            valid_statuses = [s[0] for s in CalendarTodo.EVENT_STATUS_CHOICES]
            if status and status not in valid_statuses:
                raise serializers.ValidationError(
                    {"status": f"Invalid status '{status}' for events."}
                )

        elif todo_type == "followup":
            if start_missing or (self.instance is None and not data.get("start")):
                raise serializers.ValidationError(
                    {"start": "Follow-up date is required."}
                )
            if self.instance is None:
                if not data.get("pipeline"):
                    raise serializers.ValidationError(
                        {"pipeline": "Pipeline is required for follow-ups."}
                    )
                if not data.get("assigned_to"):
                    raise serializers.ValidationError(
                        {"assigned_to": "Assigned user is required for follow-ups."}
                    )
                if not data.get("contact"):
                    raise serializers.ValidationError(
                        {"contact": "Contact is required for follow-ups."}
                    )
            else:
                if "pipeline" in data and not data.get("pipeline"):
                    raise serializers.ValidationError(
                        {"pipeline": "Pipeline cannot be cleared."}
                    )
                if "assigned_to" in data and not data.get("assigned_to"):
                    raise serializers.ValidationError(
                        {"assigned_to": "Assigned user cannot be cleared."}
                    )
                if "contact" in data and not data.get("contact"):
                    raise serializers.ValidationError(
                        {"contact": "Contact cannot be cleared."}
                    )
                if "crm" in data and not data.get("crm"):
                    raise serializers.ValidationError(
                        {"crm": "CRM deal cannot be cleared."}
                    )
            status = data.get("status")
            valid_statuses = [s[0] for s in CalendarTodo.FOLLOWUP_STATUS_CHOICES]
            if status and status not in valid_statuses:
                raise serializers.ValidationError(
                    {"status": f"Invalid status '{status}' for follow-ups."}
                )

            request = self.context.get("request")
            if self.instance is not None and status and request:
                is_creator = self.instance.user == request.user
                if not is_creator:
                    now = timezone.now()
                    is_failed = self.instance.status == "failed" or (
                        self.instance.start
                        and self.instance.start < now
                        and self.instance.status == "follow_up"
                    )
                    if is_failed and status != "failed":
                        raise serializers.ValidationError(
                            {
                                "status": "Only the creator can change the status of a failed follow-up."
                            }
                        )
                    if status == "cancelled" and not (
                        (data.get("followup_cancellation") or "").strip()
                    ):
                        raise serializers.ValidationError(
                            {
                                "followup_cancellation": "Cancellation reason is required when cancelling a follow-up."
                            }
                        )
                    if status == "complete" and not (
                        (data.get("completion_remarks") or "").strip()
                    ):
                        raise serializers.ValidationError(
                            {
                                "completion_remarks": "Completion remarks are required when completing a follow-up."
                            }
                        )
                    if status == "failed" and not (
                        (data.get("followup_failed") or "").strip()
                    ):
                        raise serializers.ValidationError(
                            {
                                "followup_failed": "Failed reason is required when marking a follow-up failed."
                            }
                        )

        elif todo_type == "meeting":
            if start_missing or (self.instance is None and not data.get("start")):
                raise serializers.ValidationError(
                    {"start": "Date & time is required for meetings."}
                )
            status = data.get("status")
            valid_statuses = [s[0] for s in CalendarTodo.MEETING_STATUS_CHOICES]
            if status and status not in valid_statuses:
                raise serializers.ValidationError(
                    {"status": f"Invalid status '{status}' for meetings."}
                )

        if data.get("start") and data.get("end") and data["start"] >= data["end"]:
            raise serializers.ValidationError(
                {"end": "End time must be after start time."}
            )

        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if (
            instance.todo_type == "task"
            and instance.start
            and instance.status not in ("completed", "on_hold", "approved", "canceled")
        ):
            if instance.start < timezone.now():
                data["status"] = "overdue"

        if instance.todo_type == "followup" and instance.start:
            if instance.start < timezone.now() and instance.status == "follow_up":
                data["status"] = "failed"

        if instance.todo_type in ("event", "meeting"):
            data["status"] = CalendarTodo.compute_event_status(
                instance.start, instance.end, instance.status
            )

        return data

    def create(self, validated_data):
        attendee_ids = validated_data.pop("attendee_ids", [])
        todo = CalendarTodo.objects.create(**validated_data)

        if todo.todo_type == "meeting" and attendee_ids:
            for uid in attendee_ids:
                MeetingAttendee.objects.create(todo=todo, user_id=uid)

        return todo

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and instance.todo_type == "task" and instance.user != request.user:
            allowed_fields = {
                "status",
                "hold_reason",
                "extension_request",
                "completion_remarks",
            }
            for field in set(validated_data) - allowed_fields:
                validated_data.pop(field)
        elif (
            request
            and instance.todo_type == "followup"
            and instance.user != request.user
        ):
            allowed_fields = {
                "status",
                "followup_cancellation",
                "followup_failed",
                "completion_remarks",
            }
            for field in set(validated_data) - allowed_fields:
                validated_data.pop(field)

        attendee_ids = validated_data.pop("attendee_ids", None)

        new_status = validated_data.get("status")
        start = validated_data.get("start")
        if instance.status == "on_hold" and new_status and new_status != "on_hold":
            validated_data["hold_reason"] = None
        if instance.status == "overdue" and new_status and new_status != "overdue":
            validated_data["extension_request"] = None
        if instance.status == "completed" and new_status and new_status != "completed":
            validated_data["completion_remarks"] = None
        if instance.status == "cancelled" and new_status and new_status != "cancelled":
            validated_data["followup_cancellation"] = None
        if instance.status == "failed" and new_status and new_status != "failed":
            validated_data["followup_failed"] = None
        if instance.extension_request and start:
            validated_data["extension_request"] = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if attendee_ids is not None and instance.todo_type == "meeting":
            instance.attendees.all().delete()
            for uid in attendee_ids:
                MeetingAttendee.objects.create(todo=instance, user_id=uid)

        return instance
