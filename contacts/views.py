from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch
from contacts.models import (
    Contact,
    ImportBatch,
    ContactLog,
    ContactRemark,
    ContactDocument,
)
from contacts.serializers import (
    ContactListSerializer,
    ContactSerializer,
    ImportBatchSerializer,
    ContactLogSerializer,
    ContactRemarkSerializer,
    ContactDocumentSerializer,
)
from crm.models import CRM


class ImportBatchViewSet(viewsets.ModelViewSet):
    """List, retrieve, and delete import batches."""

    queryset = ImportBatch.objects.all()
    serializer_class = ImportBatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def perform_destroy(self, instance):
        qs = Contact.objects.filter(import_batch=instance)
        ids = list(qs.values_list("id", flat=True))
        for i in range(0, len(ids), 500):
            Contact.objects.filter(id__in=ids[i : i + 500]).delete()
        instance.delete()

    @action(detail=True, methods=["post"], url_path="delete-chunk")
    def delete_chunk(self, request, pk=None):
        batch = self.get_object()
        limit = int(request.data.get("limit", 1500))

        total = Contact.objects.filter(import_batch=batch).count()
        ids = list(
            Contact.objects.filter(import_batch=batch)
            .order_by("id")
            .values_list("id", flat=True)[:limit]
        )

        Contact.objects.filter(id__in=ids).delete()

        remaining = Contact.objects.filter(import_batch=batch).count()

        if remaining == 0:
            batch.delete()

        return Response({"deleted": len(ids), "total": total, "remaining": remaining})


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "email", "phone", "contact_id"]

    def get_serializer_class(self):
        if self.action == "list":
            return ContactListSerializer
        return ContactSerializer

    def get_queryset(self):
        qs = Contact.objects.all()
        qs = qs.select_related("import_batch")
        if self.action in ("retrieve", "update", "partial_update", "destroy"):
            qs = qs.prefetch_related(
                Prefetch(
                    "crm_pipelines",
                    queryset=CRM.objects.select_related("pipeline", "stage"),
                )
            )
        batch_id = self.request.query_params.get("batch")
        if batch_id:
            qs = qs.filter(import_batch_id=batch_id)
        assigned_user_id = self.request.query_params.get("assigned_user")
        if assigned_user_id:
            qs = qs.filter(crm_pipelines__assigned_user_id=assigned_user_id)
        return qs

    def perform_destroy(self, instance):
        batch = instance.import_batch
        instance.delete()
        # If the batch is now empty, delete it too
        if batch and not batch.contacts.exists():
            batch.delete()

    @action(detail=False, methods=["get"], url_path="track-field-values")
    def track_field_values(self, request):
        """Return value distribution for a specific additional_data field key."""
        field = request.query_params.get("field")
        pipeline_id = request.query_params.get("pipeline_id")

        if not field:
            return Response(
                {"error": "field parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db import connection

        with connection.cursor() as cursor:
            if pipeline_id:
                cursor.execute(
                    "SELECT c.additional_data->>%s AS val, COUNT(*) AS cnt "
                    "FROM contacts_contact c "
                    "JOIN crm_crm deal ON deal.contact_id = c.id "
                    "WHERE deal.pipeline_id = %s "
                    "AND c.additional_data ? %s "
                    "GROUP BY val ORDER BY cnt DESC",
                    [field, pipeline_id, field],
                )
            else:
                cursor.execute(
                    "SELECT additional_data->>%s AS val, COUNT(*) AS cnt "
                    "FROM contacts_contact "
                    "WHERE additional_data ? %s "
                    "GROUP BY val ORDER BY cnt DESC",
                    [field, field],
                )
            rows = cursor.fetchall()

        values = [{"value": row[0], "count": row[1]} for row in rows]
        total = sum(row[1] for row in rows)
        return Response({"field": field, "total": total, "values": values})

    @action(detail=False, methods=["get"], url_path="track-fields")
    def track_fields(self, request):
        """Return all unique keys from additional_data JSONB for contacts in a pipeline."""
        from django.db import connection

        pipeline_id = request.query_params.get("pipeline_id")

        with connection.cursor() as cursor:
            if pipeline_id:
                cursor.execute(
                    "SELECT DISTINCT jsonb_object_keys(c.additional_data) "
                    "FROM contacts_contact c "
                    "JOIN crm_crm deal ON deal.contact_id = c.id "
                    "WHERE deal.pipeline_id = %s "
                    "AND c.additional_data IS NOT NULL "
                    "AND c.additional_data != '{}'::jsonb",
                    [pipeline_id],
                )
            else:
                cursor.execute(
                    "SELECT DISTINCT jsonb_object_keys(additional_data) "
                    "FROM contacts_contact "
                    "WHERE additional_data IS NOT NULL AND additional_data != '{}'::jsonb"
                )
            keys = [row[0] for row in cursor.fetchall()]

        system_fields = {
            "name",
            "email",
            "phone",
            "status",
            "contact_id",
            "source",
            "id",
            "created_at",
            "updated_at",
        }
        filtered = [k for k in keys if k.lower() not in system_fields]
        return Response({"fields": filtered})

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response(
                {"success": False, "message": "Expected a list of contacts"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch_name = request.query_params.get("batch_name") or "Unnamed Import"
        batch_id = request.query_params.get("batch_id")

        serializer = self.get_serializer(data=data, many=True)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or Create the import batch
        if batch_id:
            try:
                batch = ImportBatch.objects.get(id=batch_id)
            except (ImportBatch.DoesNotExist, ValidationError):
                return Response(
                    {"success": False, "message": "Invalid batch_id provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            batch = ImportBatch.objects.create(name=batch_name)

        last_contact = Contact.objects.order_by("created_at").last()
        next_id_num = 1001
        if last_contact:
            try:
                # Get the numeric part of the last contact_id
                # Handles cases like CON-1001, CON-1002, etc.
                parts = last_contact.contact_id.split("-")
                if len(parts) > 1 and parts[1].isdigit():
                    next_id_num = int(parts[1]) + 1
            except (IndexError, ValueError):
                pass

        contact_objects = []
        for item_data in serializer.validated_data:
            contact = Contact(**item_data)
            contact.contact_id = f"CON-{next_id_num}"
            contact.import_batch = batch
            contact.source = batch.name
            if not item_data.get("status"):
                contact.status = "Imports"
            next_id_num += 1
            contact_objects.append(contact)

        try:
            Contact.objects.bulk_create(contact_objects)
            batch.contact_count += len(contact_objects)
            batch.save()

            # Bulk create import activity logs (only for contacts created in this call)
            log_objects = [
                ContactLog(
                    contact=c,
                    activity_type="Imported",
                    description=f"Contact imported from batch '{batch.name}'",
                    user=request.user,
                    pipeline_name=None,
                )
                for c in contact_objects
            ]
            if log_objects:
                ContactLog.objects.bulk_create(log_objects, batch_size=1000)

            return Response(
                {
                    "success": True,
                    "message": f"Successfully imported {len(contact_objects)} contacts.",
                    "batch_id": str(batch.id),
                    "batch_name": batch.name,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            # Only delete the batch if we just created it and it failed
            if not batch_id:
                batch.delete()
            return Response(
                {"success": False, "message": f"Database error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        """Unified, server-side paginated activity feed for a contact.

        Merges ContactLog entries (across all of the contact's deals) and
        follow-up todos for the contact into a single timeline ordered by
        created_at (newest first), then paginates that merged stream so page
        boundaries match the rendered feed.
        """
        from django.db.models import Q
        from contacts.serializers import ContactLogSerializer
        from event_calendar.models import CalendarTodo
        from event_calendar.serializers import CalendarTodoSerializer
        from core.pagination import CustomPageNumberPagination

        contact = self.get_object()

        logs = ContactLog.objects.filter(contact_id=contact.id).select_related(
            "user", "crm", "crm__pipeline"
        )
        todos = CalendarTodo.objects.filter(
            contact_id=contact.id, todo_type="followup"
        ).select_related("user", "assigned_to", "contact", "pipeline")

        date_filter = request.query_params.get("date")
        if date_filter:
            logs = logs.filter(created_at__date=date_filter)
            todos = todos.filter(start__date=date_filter)

        user = request.user
        if user.role not in ("Superadmin", "Admin"):
            todos = todos.filter(Q(assigned_to=user) | Q(user=user))

        items = [
            {"kind": "log", **entry}
            for entry in ContactLogSerializer(
                logs, many=True, context={"request": request}
            ).data
        ]
        items += [
            {"kind": "followup", **entry}
            for entry in CalendarTodoSerializer(
                todos, many=True, context={"request": request}
            ).data
        ]

        kind = request.query_params.get("kind")
        if kind == "log":
            items = [i for i in items if i["kind"] == "log"]
        elif kind == "followup":
            items = [i for i in items if i["kind"] == "followup"]

        items.sort(key=lambda x: x.get("created_at") or "", reverse=True)

        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(items, request, view=self)
        return paginator.get_paginated_response(page)


class ContactLogViewSet(viewsets.ModelViewSet):
    queryset = ContactLog.objects.all().select_related(
        "contact", "crm", "crm__pipeline", "user"
    )
    serializer_class = ContactLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        contact_id = self.request.query_params.get("contact")
        crm_id = self.request.query_params.get("crm")

        if crm_id:
            qs = qs.filter(crm_id=crm_id)
        elif contact_id:
            qs = qs.filter(contact_id=contact_id)

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ContactRemarkViewSet(viewsets.ModelViewSet):
    """Viewset for contact remarks/updates"""

    queryset = ContactRemark.objects.all()
    serializer_class = ContactRemarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        contact_id = self.request.query_params.get("contact")
        crm_id = self.request.query_params.get("crm")

        if crm_id:
            qs = qs.filter(crm_id=crm_id)
        elif contact_id:
            qs = qs.filter(contact_id=contact_id)

        return qs

    def perform_create(self, serializer):
        remark = serializer.save(user=self.request.user)
        # Create an activity log for the remark
        ContactLog.objects.create(
            contact=remark.contact,
            crm=remark.crm,
            user=remark.user,
            activity_type="Remark Added",
            description=f'Added an update: "{remark.text}"',
            pipeline_name=remark.crm.pipeline.name
            if remark.crm and remark.crm.pipeline
            else None,
        )


class ContactDocumentViewSet(viewsets.ModelViewSet):
    """Upload and manage files attached to contacts."""

    serializer_class = ContactDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["file_name", "description"]

    def get_queryset(self):
        qs = ContactDocument.objects.select_related("contact", "uploaded_by")
        contact_id = self.request.query_params.get("contact")
        if contact_id:
            qs = qs.filter(contact_id=contact_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
