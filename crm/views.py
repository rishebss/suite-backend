from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.text import slugify
from django.db.models import Count
from django.db import models
from crm.models import CRM, Pipeline, Stage
from crm.serializers import CRMSerializer, PipelineSerializer, StageSerializer
from authentication.models import User

DEFAULT_STAGES = [
    {"name": "Lead", "color": "blue", "order": 0},
    {"name": "Qualified", "color": "purple", "order": 1},
    {"name": "Proposal", "color": "amber", "order": 2},
    {"name": "Negotiation", "color": "orange", "order": 3},
    {"name": "Won", "color": "green", "order": 4},
    {"name": "Lost", "color": "red", "order": 5},
]


class PipelineViewSet(viewsets.ModelViewSet):
    queryset = (
        Pipeline.objects.annotate(deals_count=Count("deals"))
        .prefetch_related("stages", "departments")
        .all()
    )
    serializer_class = PipelineSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_authenticated and user.role == "Staff":
            qs = qs.filter(departments__in=user.departments.all()).distinct()
        pipeline_type = self.request.query_params.get("pipeline_type")
        if pipeline_type:
            qs = qs.filter(pipeline_type=pipeline_type)
        return qs

    def perform_create(self, serializer):
        pipeline = serializer.save()
        # Auto-create default stages for new pipelines
        Stage.objects.bulk_create(
            [
                Stage(
                    pipeline=pipeline,
                    name=s["name"],
                    slug=slugify(s["name"]),
                    order=s["order"],
                    color=s["color"],
                )
                for s in DEFAULT_STAGES
            ]
        )

    @action(detail=True, methods=["get"], url_path="assignment-stats")
    def assignment_stats(self, request, pk=None):
        """Return deal assignment breakdown and user load for a pipeline."""
        pipeline = self.get_object()

        # Deal counts
        total_deals = CRM.objects.filter(pipeline=pipeline).count()
        assigned_deals = CRM.objects.filter(
            pipeline=pipeline, assigned_user__isnull=False
        ).count()
        unassigned_deals = total_deals - assigned_deals

        # User load: count of deals per eligible user
        eligible_users = (
            User.objects.filter(
                departments__in=pipeline.departments.all(), is_active=True
            )
            .distinct()
            .annotate(
                deal_count=Count(
                    "assigned_deals", filter=models.Q(assigned_deals__pipeline=pipeline)
                )
            )
        )

        user_loads = [
            {
                "id": str(user.id),
                "name": f"{user.first_name} {user.last_name}".strip() or user.email,
                "email": user.email,
                "deal_count": user.deal_count,
            }
            for user in eligible_users
        ]

        user_loads.sort(key=lambda u: u["deal_count"])

        return Response(
            {
                "total_deals": total_deals,
                "assigned_deals": assigned_deals,
                "unassigned_deals": unassigned_deals,
                "user_loads": user_loads,
            }
        )

    @action(detail=True, methods=["post"], url_path="trigger-assignment")
    def trigger_assignment(self, request, pk=None):
        """Bulk-assign all unassigned deals using the pipeline's assignment strategy."""
        pipeline = self.get_object()
        strategy = request.data.get("strategy", pipeline.assignment_type)

        if pipeline.assignment_type != strategy:
            pipeline.assignment_type = strategy
            pipeline.save(update_fields=["assignment_type"])
            if strategy != "single_user" and pipeline.assigned_user:
                pipeline.assigned_user = None
                pipeline.save(update_fields=["assigned_user"])

        unassigned = CRM.objects.filter(
            pipeline=pipeline, assigned_user__isnull=True
        ).select_related("contact", "assigned_user")
        unassigned_count = unassigned.count()

        if unassigned_count == 0:
            return Response(
                {"message": "No unassigned deals found", "assigned_count": 0}
            )

        eligible_users = list(
            User.objects.filter(
                departments__in=pipeline.departments.all(), is_active=True
            ).distinct()
        )

        if not eligible_users:
            return Response(
                {"error": "No eligible users in assigned groups"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unassigned_list = list(unassigned)
        assigned_count = 0

        if strategy == "round_robin":
            # Start round robin from the last assigned user index if possible
            last_deal = (
                CRM.objects.filter(pipeline=pipeline, assigned_user__isnull=False)
                .order_by("-created_at")
                .first()
            )

            start_index = 0
            if last_deal and last_deal.assigned_user in eligible_users:
                start_index = (eligible_users.index(last_deal.assigned_user) + 1) % len(
                    eligible_users
                )

            for i, deal in enumerate(unassigned_list):
                user = eligible_users[(start_index + i) % len(eligible_users)]
                deal.assigned_user = user
                assigned_count += 1

        elif strategy == "least_loaded":
            # Pre-calculate current loads
            user_loads = {user: 0 for user in eligible_users}
            counts = (
                CRM.objects.filter(pipeline=pipeline, assigned_user__in=eligible_users)
                .values("assigned_user")
                .annotate(c=Count("id"))
            )

            for item in counts:
                user_obj = next(
                    (u for u in eligible_users if u.id == item["assigned_user"]), None
                )
                if user_obj:
                    user_loads[user_obj] = item["c"]

            for deal in unassigned_list:
                # Find least loaded user in memory
                least_loaded_user = min(user_loads, key=user_loads.get)
                deal.assigned_user = least_loaded_user
                user_loads[least_loaded_user] += 1
                assigned_count += 1

        elif strategy == "single_user":
            target_user_id = request.data.get("target_user_id")
            if not target_user_id:
                return Response(
                    {"error": "target_user_id is required for single_user strategy"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                target_user = next(
                    u for u in eligible_users if str(u.id) == str(target_user_id)
                )
            except StopIteration:
                return Response(
                    {"error": "Selected user is not eligible for this pipeline"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for deal in unassigned_list:
                deal.assigned_user = target_user
                assigned_count += 1

            pipeline.assigned_user = target_user
            pipeline.save(update_fields=["assigned_user"])

        # Perform Bulk Update
        CRM.objects.bulk_update(unassigned_list, ["assigned_user"], batch_size=1000)

        # Log assignment changes for triggered deals
        from contacts.models import ContactLog

        log_entries = []
        for deal in unassigned_list:
            if not deal.assigned_user:
                continue
            log_entries.append(
                ContactLog(
                    contact=deal.contact,
                    crm=deal,
                    activity_type="Assignment Changed",
                    description=f"Assigned to user {deal.assigned_user.first_name} {deal.assigned_user.last_name}".strip()
                    or deal.assigned_user.email,
                    user=request.user,
                    pipeline_name=pipeline.name,
                )
            )
        if log_entries:
            ContactLog.objects.bulk_create(log_entries, batch_size=1000)

        return Response(
            {
                "message": f"Assigned {assigned_count} deals using {strategy}",
                "assigned_count": assigned_count,
            }
        )

    @action(detail=True, methods=["post"], url_path="delete-chunk")
    def delete_chunk(self, request, pk=None):
        """Delete up to `limit` deals from a pipeline. Deletes the pipeline itself when empty."""
        pipeline = self.get_object()
        limit = int(request.data.get("limit", 500))

        total = CRM.objects.filter(pipeline=pipeline).count()
        ids = list(
            CRM.objects.filter(pipeline=pipeline)
            .order_by("id")
            .values_list("id", flat=True)[:limit]
        )

        if ids:
            from contacts.models import ContactLog

            deals_to_delete = list(
                CRM.objects.filter(id__in=ids).select_related("contact", "pipeline")
            )

            log_entries = []
            for crm in deals_to_delete:
                log_entries.append(
                    ContactLog(
                        contact=crm.contact,
                        crm=None,
                        activity_type="Deal Deleted",
                        description=f"Deal removed from pipeline '{crm.pipeline.name}'"
                        if crm.pipeline
                        else "Deal deleted",
                        user=request.user,
                        pipeline_name=crm.pipeline.name if crm.pipeline else None,
                    )
                )

            ContactLog.objects.bulk_create(log_entries, batch_size=1000)
            CRM.objects.filter(id__in=ids).delete()

        remaining = CRM.objects.filter(pipeline=pipeline).count()

        if remaining == 0:
            pipeline.delete()

        return Response({"deleted": len(ids), "total": total, "remaining": remaining})


class StageViewSet(viewsets.ModelViewSet):
    serializer_class = StageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        pipeline_pk = self.kwargs["pipeline_pk"]
        if user.is_authenticated and user.role == "Staff":
            has_access = Pipeline.objects.filter(
                id=pipeline_pk, departments__in=user.departments.all()
            ).exists()
            if not has_access:
                return Stage.objects.none()
        return Stage.objects.filter(pipeline_id=pipeline_pk).order_by("order")

    def perform_create(self, serializer):
        from django.utils.text import slugify
        import uuid

        name = serializer.validated_data.get("name")
        pipeline_id = self.kwargs["pipeline_pk"]

        # Generate base slug
        base_slug = slugify(name)
        if not base_slug:
            base_slug = f"stage-{uuid.uuid4().hex[:8]}"

        # Make sure slug is unique for this pipeline
        existing_slugs = Stage.objects.filter(pipeline_id=pipeline_id).values_list(
            "slug", flat=True
        )

        test_slug = base_slug
        counter = 1
        while test_slug in existing_slugs:
            test_slug = f"{base_slug}-{counter}"
            counter += 1

        serializer.save(pipeline_id=pipeline_id, slug=test_slug)

    def perform_update(self, serializer):
        from django.utils.text import slugify

        name = serializer.validated_data.get("name")
        instance = self.get_object()

        # Only regenerate slug if name changed
        if name and name != instance.name:
            pipeline_id = self.kwargs["pipeline_pk"]
            base_slug = slugify(name)
            if not base_slug:
                import uuid

                base_slug = f"stage-{uuid.uuid4().hex[:8]}"

            # Make sure slug is unique for this pipeline
            existing_slugs = (
                Stage.objects.filter(pipeline_id=pipeline_id)
                .exclude(id=instance.id)
                .values_list("slug", flat=True)
            )

            test_slug = base_slug
            counter = 1
            while test_slug in existing_slugs:
                test_slug = f"{base_slug}-{counter}"
                counter += 1

            serializer.save(slug=test_slug)
        else:
            serializer.save()

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request, pipeline_pk=None):
        """Accepts [{id, order}, ...] and bulk updates order."""
        items = request.data
        for item in items:
            Stage.objects.filter(id=item["id"], pipeline_id=pipeline_pk).update(
                order=item["order"]
            )
        return Response({"success": True})


class CRMViewSet(viewsets.ModelViewSet):
    queryset = (
        CRM.objects.all()
        .select_related("contact", "pipeline", "stage", "assigned_user")
        .prefetch_related("pipeline__stages", "pipeline__departments")
    )
    serializer_class = CRMSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_authenticated and user.role == "Staff":
            qs = qs.filter(assigned_user=user)

        stage_id = self.request.query_params.get("stage")
        stages = self.request.query_params.get("stages")
        pipeline_id = self.request.query_params.get("pipeline")
        assigned_user_id = self.request.query_params.get("assigned_user")
        search = self.request.query_params.get("search")
        exclude_ids = self.request.query_params.get("exclude_ids")
        exclude_pipeline_id = self.request.query_params.get("exclude_pipeline_id")
        additional_field = self.request.query_params.get("additional_field")
        additional_value = self.request.query_params.get("additional_value")

        if exclude_ids:
            ids = [int(id) for id in exclude_ids.split(",") if id]
            if ids:
                qs = qs.exclude(id__in=ids)

        if exclude_pipeline_id:
            qs = qs.exclude(contact__crm_pipelines__pipeline_id=exclude_pipeline_id)

        if additional_field and additional_value:
            qs = qs.filter(
                contact__additional_data__contains={additional_field: additional_value}
            )

        if stage_id:
            qs = qs.filter(stage_id=stage_id)
        if stages:
            stage_ids = [s for s in stages.split(",") if s]
            if stage_ids:
                qs = qs.filter(stage_id__in=stage_ids)
        if pipeline_id:
            qs = qs.filter(pipeline_id=pipeline_id)
        if assigned_user_id:
            qs = qs.filter(assigned_user_id=assigned_user_id)
        if search:
            from django.db.models import Q

            search_by = self.request.query_params.get("search_by", "name")
            allowed = {"name", "email", "phone"}
            fields = [f.strip() for f in search_by.split(",") if f.strip() in allowed]
            if not fields:
                fields = ["name"]
            q = models.Q()
            if "name" in fields:
                q |= models.Q(contact__name__icontains=search)
            if "email" in fields:
                q |= models.Q(contact__email__icontains=search)
            if "phone" in fields:
                q |= models.Q(contact__phone__icontains=search)
            qs = qs.filter(q)
        return qs

    def get_pipeline_users(self, pipeline):
        """Get all users eligible for assignment in this pipeline (from pipeline's departments)."""
        if not pipeline:
            return User.objects.none()
        return User.objects.filter(
            departments__in=pipeline.departments.all(), is_active=True
        ).distinct()

    def assign_round_robin(self, pipeline):
        """Assign the next user in round-robin order."""
        users = list(self.get_pipeline_users(pipeline))
        if not users:
            return None

        # Find the last assigned deal in this pipeline
        last_deal = (
            CRM.objects.filter(pipeline=pipeline, assigned_user__isnull=False)
            .order_by("-created_at")
            .first()
        )

        if last_deal and last_deal.assigned_user:
            # Find the index of the last assigned user
            try:
                last_index = users.index(last_deal.assigned_user)
                next_index = (last_index + 1) % len(users)
                return users[next_index]
            except ValueError:
                # Last assigned user is no longer in the list, start from beginning
                return users[0]
        # No previous assignment, start with first user
        return users[0]

    def assign_least_loaded(self, pipeline):
        """Assign to the user with the fewest assigned deals in this pipeline."""
        users = self.get_pipeline_users(pipeline)
        if not users:
            return None

        # Annotate users with deal count in this pipeline
        users_with_count = users.annotate(
            deal_count=Count(
                "assigned_deals", filter=models.Q(assigned_deals__pipeline=pipeline)
            )
        ).order_by("deal_count", "id")

        return users_with_count.first()

    def perform_create(self, serializer):
        """Handle automatic assignment when creating a deal."""
        pipeline = serializer.validated_data.get("pipeline")
        assigned_user = serializer.validated_data.get("assigned_user")

        # If no user is explicitly assigned and pipeline exists, try automatic assignment
        if not assigned_user and pipeline:
            if pipeline.assignment_type == "round_robin":
                assigned_user = self.assign_round_robin(pipeline)
            elif pipeline.assignment_type == "least_loaded":
                assigned_user = self.assign_least_loaded(pipeline)
            elif pipeline.assignment_type == "single_user":
                assigned_user = pipeline.assigned_user

        crm = serializer.save(assigned_user=assigned_user)

        # Record activity logs
        from contacts.models import ContactLog

        ContactLog.objects.create(
            contact=crm.contact,
            crm=crm,
            activity_type="Pipeline Added",
            description=f"Added to pipeline '{pipeline.name}' under stage '{crm.stage.name if crm.stage else 'Default'}'",
            user=self.request.user,
            pipeline_name=pipeline.name if pipeline else None,
        )
        if assigned_user:
            ContactLog.objects.create(
                contact=crm.contact,
                crm=crm,
                activity_type="Assignment Changed",
                description=f"Assigned to user {assigned_user.first_name} {assigned_user.last_name}".strip()
                or assigned_user.email,
                user=self.request.user,
                pipeline_name=pipeline.name if pipeline else None,
            )

    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_stage = old_instance.stage
        old_user = old_instance.assigned_user
        old_pipeline = old_instance.pipeline

        instance = serializer.save()

        # Reset assigned_user when pipeline changes (moving deals between pipelines)
        if old_pipeline and old_pipeline != instance.pipeline:
            CRM.objects.filter(id=instance.id).update(assigned_user=None)
            instance.assigned_user = None

        # Check if stage changed
        from contacts.models import ContactLog

        if old_stage != instance.stage:
            ContactLog.objects.create(
                contact=instance.contact,
                crm=instance,
                activity_type="Stage Changed",
                description=f"Moved to stage '{instance.stage.name}'"
                if instance.stage
                else "Removed from stage",
                user=self.request.user,
                pipeline_name=instance.pipeline.name if instance.pipeline else None,
            )

        # Check if pipeline changed
        if old_pipeline != instance.pipeline:
            ContactLog.objects.create(
                contact=instance.contact,
                crm=instance,
                activity_type="Pipeline Changed",
                description=f"Added to pipeline '{instance.pipeline.name}'"
                if instance.pipeline
                else "Removed from pipeline",
                user=self.request.user,
                pipeline_name=instance.pipeline.name if instance.pipeline else None,
            )
            # Log on the source deal that it was moved from old pipeline
            if old_pipeline:
                ContactLog.objects.create(
                    contact=instance.contact,
                    crm=instance,
                    activity_type="Pipeline Changed",
                    description=f"Moved from pipeline '{old_pipeline.name}' to '{instance.pipeline.name}'"
                    if instance.pipeline
                    else f"Moved from pipeline '{old_pipeline.name}'",
                    user=self.request.user,
                    pipeline_name=old_pipeline.name,
                )

        # Check if assignee changed
        if old_user != instance.assigned_user:
            user_name = (
                f"{instance.assigned_user.first_name} {instance.assigned_user.last_name}".strip()
                or instance.assigned_user.email
                if instance.assigned_user
                else "Unassigned"
            )
            ContactLog.objects.create(
                contact=instance.contact,
                crm=instance,
                activity_type="Assignment Changed",
                description=f"Assigned to user {user_name}"
                if instance.assigned_user
                else "Unassigned",
                user=self.request.user,
                pipeline_name=instance.pipeline.name if instance.pipeline else None,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        from contacts.models import ContactLog

        ContactLog.objects.create(
            contact=instance.contact,
            crm=None,
            activity_type="Deal Deleted",
            description=f"Deal removed from pipeline '{instance.pipeline.name}'"
            if instance.pipeline
            else "Deal deleted",
            user=request.user,
            pipeline_name=instance.pipeline.name if instance.pipeline else None,
        )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="copy-to-pipeline")
    def copy_to_pipeline(self, request, pk=None):
        """Copy a deal to a new pipeline (creates new CRM entry, logs on source deal)."""
        source = self.get_object()
        target_pipeline_id = request.data.get("pipeline_id")
        if not target_pipeline_id:
            return Response(
                {"error": "pipeline_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        from crm.models import Pipeline, Stage
        from contacts.models import ContactLog

        try:
            target_pipeline = Pipeline.objects.get(id=target_pipeline_id)
        except Pipeline.DoesNotExist:
            return Response(
                {"error": "Target pipeline not found"}, status=status.HTTP_404_NOT_FOUND
            )

        first_stage = (
            Stage.objects.filter(pipeline=target_pipeline).order_by("order").first()
        )

        # Don't inherit assigned_user from source — the target pipeline
        # has different user groups. Auto-assignment will handle it if
        # the pipeline has a strategy configured, otherwise leave null.
        assigned_user = None
        if target_pipeline.assignment_type == "round_robin":
            assigned_user = self.assign_round_robin(target_pipeline)
        elif target_pipeline.assignment_type == "least_loaded":
            assigned_user = self.assign_least_loaded(target_pipeline)
        elif target_pipeline.assignment_type == "single_user":
            assigned_user = target_pipeline.assigned_user

        # Create new CRM entry
        new_crm = CRM.objects.create(
            contact=source.contact,
            pipeline=target_pipeline,
            stage=first_stage,
            value=source.value,
            priority=source.priority,
            assigned_user=assigned_user,
        )

        # Log on source deal
        ContactLog.objects.create(
            contact=source.contact,
            crm=source,
            activity_type="Pipeline Changed",
            description=f"Copied to pipeline '{target_pipeline.name}'",
            user=request.user,
            pipeline_name=source.pipeline.name if source.pipeline else None,
        )

        # Log on new deal
        ContactLog.objects.create(
            contact=new_crm.contact,
            crm=new_crm,
            activity_type="Pipeline Added",
            description=f"Added to pipeline '{target_pipeline.name}' under stage '{first_stage.name if first_stage else 'Default'}' — Copied from '{source.pipeline.name}'"
            if source.pipeline
            else f"Added to pipeline '{target_pipeline.name}'",
            user=request.user,
            pipeline_name=target_pipeline.name,
        )

        # Auto-assignment log
        if new_crm.assigned_user:
            ContactLog.objects.create(
                contact=new_crm.contact,
                crm=new_crm,
                activity_type="Assignment Changed",
                description=f"Assigned to user {new_crm.assigned_user.first_name} {new_crm.assigned_user.last_name}".strip()
                or new_crm.assigned_user.email,
                user=request.user,
                pipeline_name=target_pipeline.name,
            )

        serializer = CRMSerializer(new_crm)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="bulk-add-to-pipeline")
    def bulk_add_to_pipeline(self, request):
        """
        Copy multiple deals to a target pipeline (creates NEW CRM entries).
        Unlike move which updates pipeline_id on existing rows, this creates
        fresh CRM entries — useful when a contact purchases multiple services.
        """
        deal_ids = request.data.get("deal_ids", [])
        pipeline_id = request.data.get("pipeline_id")

        if not pipeline_id or not deal_ids:
            return Response(
                {"error": "pipeline_id and deal_ids list are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from contacts.models import ContactLog

            target_pipeline = Pipeline.objects.get(id=pipeline_id)
            if (
                request.user.role == "Staff"
                and not target_pipeline.departments.filter(
                    id__in=request.user.departments.all()
                ).exists()
            ):
                return Response(
                    {"error": "You do not have access to this pipeline."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            first_stage = (
                Stage.objects.filter(pipeline=target_pipeline).order_by("order").first()
            )

            # Pre-fetch source deals with their contacts
            source_deals = list(
                CRM.objects.filter(id__in=deal_ids).select_related(
                    "contact", "pipeline"
                )
            )

            if not source_deals:
                return Response(
                    {"message": "No valid deals found to copy.", "added_count": 0}
                )

            # Pre-calculate assignment for all new entries
            eligible_users = list(
                User.objects.filter(
                    departments__in=target_pipeline.departments.all(), is_active=True
                ).distinct()
            )

            rr_index = 0
            if target_pipeline.assignment_type == "round_robin" and eligible_users:
                last_deal = (
                    CRM.objects.filter(
                        pipeline=target_pipeline, assigned_user__isnull=False
                    )
                    .order_by("-created_at")
                    .first()
                )
                if last_deal and last_deal.assigned_user in eligible_users:
                    rr_index = (
                        eligible_users.index(last_deal.assigned_user) + 1
                    ) % len(eligible_users)

            ll_loads = {}
            if target_pipeline.assignment_type == "least_loaded" and eligible_users:
                ll_loads = {user: 0 for user in eligible_users}
                counts = (
                    CRM.objects.filter(
                        pipeline=target_pipeline, assigned_user__in=eligible_users
                    )
                    .values("assigned_user")
                    .annotate(c=Count("id"))
                )
                for item in counts:
                    user_obj = next(
                        (u for u in eligible_users if u.id == item["assigned_user"]),
                        None,
                    )
                    if user_obj:
                        ll_loads[user_obj] = item["c"]

            # Build new CRM entries
            crm_entries = []
            for deal in source_deals:
                assigned_user = None
                if eligible_users:
                    if target_pipeline.assignment_type == "round_robin":
                        assigned_user = eligible_users[rr_index]
                        rr_index = (rr_index + 1) % len(eligible_users)
                    elif target_pipeline.assignment_type == "least_loaded":
                        assigned_user = min(ll_loads, key=ll_loads.get)
                        ll_loads[assigned_user] += 1

                crm_entries.append(
                    CRM(
                        contact=deal.contact,
                        pipeline=target_pipeline,
                        stage=first_stage,
                        value=deal.value,
                        priority=deal.priority,
                        assigned_user=assigned_user,
                    )
                )

            # Bulk create in chunks
            CRM.objects.bulk_create(crm_entries, batch_size=1000)

            # Fetch back saved entries for activity logs
            new_contact_ids = [c.contact_id for c in crm_entries]
            saved_crms = CRM.objects.filter(
                pipeline=target_pipeline, contact_id__in=new_contact_ids
            ).select_related("contact", "assigned_user")

            # Build activity logs
            log_entries = []
            for crm_entry in saved_crms:
                # Find matching source deal for better descriptions
                source_deal = next(
                    (d for d in source_deals if d.contact_id == crm_entry.contact_id),
                    None,
                )
                source_pipeline_name = (
                    source_deal.pipeline.name
                    if source_deal and source_deal.pipeline
                    else None
                )

                description = f"Added to pipeline '{target_pipeline.name}' under stage '{first_stage.name if first_stage else 'Default'}'"
                if source_pipeline_name:
                    description += f" — Copied from '{source_pipeline_name}'"

                log_entries.append(
                    ContactLog(
                        contact=crm_entry.contact,
                        crm=crm_entry,
                        activity_type="Pipeline Added",
                        description=description,
                        user=request.user,
                        pipeline_name=target_pipeline.name,
                    )
                )
                if crm_entry.assigned_user:
                    log_entries.append(
                        ContactLog(
                            contact=crm_entry.contact,
                            crm=crm_entry,
                            activity_type="Assignment Changed",
                            description=f"Assigned to user {crm_entry.assigned_user.first_name} {crm_entry.assigned_user.last_name}".strip()
                            or crm_entry.assigned_user.email,
                            user=request.user,
                            pipeline_name=target_pipeline.name,
                        )
                    )

            ContactLog.objects.bulk_create(log_entries, batch_size=1000)

            return Response(
                {
                    "message": f"Successfully added {len(crm_entries)} deals to the pipeline.",
                    "added_count": len(crm_entries),
                }
            )
        except Pipeline.DoesNotExist:
            return Response(
                {"error": "Target pipeline not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="bulk-add-from-batch")
    def bulk_add_from_batch(self, request):
        batch_id = request.data.get("batch_id")
        pipeline_id = request.data.get("pipeline_id")
        offset = int(request.data.get("offset", 0))
        limit = int(request.data.get("limit", 0))

        # Fetch batch name for activity log descriptions
        batch_name = None
        if batch_id:
            from contacts.models import ImportBatch

            try:
                batch = ImportBatch.objects.get(id=batch_id)
                batch_name = batch.name
            except ImportBatch.DoesNotExist:
                pass

        if not batch_id or not pipeline_id:
            return Response(
                {"error": "batch_id and pipeline_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from contacts.models import Contact

            first_stage = (
                Stage.objects.filter(pipeline_id=pipeline_id).order_by("order").first()
            )

            pipeline = Pipeline.objects.get(id=pipeline_id)
            if (
                request.user.role == "Staff"
                and not pipeline.departments.filter(
                    id__in=request.user.departments.all()
                ).exists()
            ):
                return Response(
                    {"error": "You do not have access to this pipeline."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            base_qs = Contact.objects.filter(import_batch_id=batch_id).order_by("id")
            all_ids = list(base_qs.values_list("id", flat=True))
            total_count = len(all_ids)

            # If offset/limit provided, only process that slice
            if limit > 0:
                chunk_ids = all_ids[offset : offset + limit]
            else:
                chunk_ids = all_ids

            total_added = 0
            CHUNK_SIZE = 1500

            for i in range(0, len(chunk_ids), CHUNK_SIZE):
                batch_ids = chunk_ids[i : i + CHUNK_SIZE]

                existing = set(
                    CRM.objects.filter(
                        pipeline_id=pipeline_id, contact_id__in=batch_ids
                    ).values_list("contact_id", flat=True)
                )

                new_chunk_ids = [cid for cid in batch_ids if cid not in existing]
                if not new_chunk_ids:
                    continue

                new_contacts = list(Contact.objects.filter(id__in=new_chunk_ids))

                eligible_users = list(
                    User.objects.filter(
                        departments__in=pipeline.departments.all(), is_active=True
                    ).distinct()
                )

                rr_index = 0
                if pipeline.assignment_type == "round_robin" and eligible_users:
                    last_deal = (
                        CRM.objects.filter(
                            pipeline=pipeline, assigned_user__isnull=False
                        )
                        .order_by("-created_at")
                        .first()
                    )
                    if last_deal and last_deal.assigned_user in eligible_users:
                        rr_index = (
                            eligible_users.index(last_deal.assigned_user) + 1
                        ) % len(eligible_users)

                ll_loads = {}
                if pipeline.assignment_type == "least_loaded" and eligible_users:
                    ll_loads = {user: 0 for user in eligible_users}
                    counts = (
                        CRM.objects.filter(
                            pipeline=pipeline, assigned_user__in=eligible_users
                        )
                        .values("assigned_user")
                        .annotate(c=Count("id"))
                    )
                    for item in counts:
                        user_obj = next(
                            (
                                u
                                for u in eligible_users
                                if u.id == item["assigned_user"]
                            ),
                            None,
                        )
                        if user_obj:
                            ll_loads[user_obj] = item["c"]

                crm_entries = []
                for contact in new_contacts:
                    assigned_user = None
                    if eligible_users:
                        if pipeline.assignment_type == "round_robin":
                            assigned_user = eligible_users[rr_index]
                            rr_index = (rr_index + 1) % len(eligible_users)
                        elif pipeline.assignment_type == "least_loaded":
                            assigned_user = min(ll_loads, key=ll_loads.get)
                            ll_loads[assigned_user] += 1

                    crm_entries.append(
                        CRM(
                            contact=contact,
                            pipeline_id=pipeline_id,
                            stage=first_stage,
                            priority="Medium",
                            assigned_user=assigned_user,
                        )
                    )

                CRM.objects.bulk_create(crm_entries, batch_size=1000)

                Contact.objects.filter(id__in=new_chunk_ids).update(status="Lead")

                from contacts.models import ContactLog

                saved_crms = CRM.objects.filter(
                    pipeline_id=pipeline_id, contact_id__in=new_chunk_ids
                )

                # Deduplicate: skip contacts that already have a "Pipeline Added" log for this deal
                existing_log_contacts = set(
                    ContactLog.objects.filter(
                        crm__in=saved_crms, activity_type="Pipeline Added"
                    ).values_list("crm_id", flat=True)
                )

                log_entries = []
                for crm in saved_crms:
                    if crm.id in existing_log_contacts:
                        continue
                    description = f"Added to pipeline '{pipeline.name}' under stage '{first_stage.name if first_stage else 'Default'}'"
                    if batch_name:
                        description += f" — Imported from '{batch_name}'"
                    log_entries.append(
                        ContactLog(
                            contact=crm.contact,
                            crm=crm,
                            activity_type="Pipeline Added",
                            description=description,
                            user=request.user,
                            pipeline_name=pipeline.name,
                        )
                    )
                    if crm.assigned_user:
                        log_entries.append(
                            ContactLog(
                                contact=crm.contact,
                                crm=crm,
                                activity_type="Assignment Changed",
                                description=f"Assigned to user {crm.assigned_user.first_name} {crm.assigned_user.last_name}".strip()
                                or crm.assigned_user.email,
                                user=request.user,
                                pipeline_name=pipeline.name,
                            )
                        )
                ContactLog.objects.bulk_create(log_entries, batch_size=1000)

                total_added += len(crm_entries)

            return Response(
                {
                    "message": f"Added {total_added} contacts.",
                    "added_count": total_added,
                    "total_count": total_count,
                }
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="bulk-add-contacts")
    def bulk_add_contacts(self, request):
        pipeline_id = request.data.get("pipeline_id")
        contact_ids = request.data.get("contact_ids", [])
        source_pipeline = request.data.get("source_pipeline")
        priority = request.data.get("priority", "High")
        skip_contact_status_update = request.data.get(
            "skip_contact_status_update", False
        )

        if not pipeline_id or not contact_ids:
            return Response(
                {"error": "pipeline_id and contact_ids list are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            import time
            from django.db import connection

            _t0 = time.time()
            _q0 = len(connection.queries)
            from contacts.models import Contact

            first_stage = (
                Stage.objects.filter(pipeline_id=pipeline_id).order_by("order").first()
            )

            pipeline = Pipeline.objects.get(id=pipeline_id)
            if (
                request.user.role == "Staff"
                and not pipeline.departments.filter(
                    id__in=request.user.departments.all()
                ).exists()
            ):
                return Response(
                    {"error": "You do not have access to this pipeline."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if source_pipeline:
                # MOVE existing deals from source pipeline to new pipeline
                # Reset assigned_user since the target pipeline may have different
                # user groups. Trigger-assignment (called by the frontend after
                # the move) can then assign them properly.
                moved_count = CRM.objects.filter(
                    pipeline_id=source_pipeline, contact_id__in=contact_ids
                ).update(
                    pipeline_id=pipeline_id,
                    stage=first_stage,
                    priority=priority,
                    assigned_user=None,
                )

                # Update contact statuses to Retarget (unless skipped for plain move)
                if not skip_contact_status_update:
                    Contact.objects.filter(id__in=contact_ids).update(status="Retarget")

                # Activity logs
                from contacts.models import ContactLog

                moved_deals = CRM.objects.select_related("contact").filter(
                    pipeline_id=pipeline_id, contact_id__in=contact_ids
                )
                log_entries = []
                for crm in moved_deals:
                    log_entries.append(
                        ContactLog(
                            contact=crm.contact,
                            crm=crm,
                            activity_type="Pipeline Changed",
                            description=f"Moved to retarget pipeline '{pipeline.name}' under stage '{first_stage.name if first_stage else 'Default'}'",
                            user=request.user,
                            pipeline_name=pipeline.name,
                        )
                    )
                ContactLog.objects.bulk_create(log_entries, batch_size=1000)

                print(
                    f"[TIMING] source_pipeline branch: {time.time() - _t0:.3f}s | queries={len(connection.queries) - _q0} | contacts={len(contact_ids)}"
                )
                action_label = "moved" if skip_contact_status_update else "retargeted"
                return Response(
                    {
                        "message": f"Successfully {action_label} {moved_count} deals to pipeline.",
                        "moved_count": moved_count,
                    }
                )
            else:
                # Legacy: create new CRM entries (copy)
                contact_ids_list = list(contact_ids)
                existing_ids = set(
                    CRM.objects.filter(
                        pipeline_id=pipeline_id, contact_id__in=contact_ids_list
                    ).values_list("contact_id", flat=True)
                )

                new_contact_ids = [
                    cid for cid in contact_ids_list if cid not in existing_ids
                ]
                new_contacts = list(Contact.objects.filter(id__in=new_contact_ids))
                print(
                    f"[STAGE] after fetch contacts: queries={len(connection.queries) - _q0}"
                )

                eligible_users = list(
                    User.objects.filter(
                        departments__in=pipeline.departments.all(), is_active=True
                    ).distinct()
                )
                print(
                    f"[STAGE] after eligible_users: queries={len(connection.queries) - _q0}"
                )

                rr_index = 0
                if pipeline.assignment_type == "round_robin" and eligible_users:
                    last_deal = (
                        CRM.objects.filter(
                            pipeline=pipeline, assigned_user__isnull=False
                        )
                        .order_by("-created_at")
                        .first()
                    )
                    if last_deal and last_deal.assigned_user in eligible_users:
                        rr_index = (
                            eligible_users.index(last_deal.assigned_user) + 1
                        ) % len(eligible_users)
                print(
                    f"[STAGE] after round_robin: queries={len(connection.queries) - _q0}"
                )

                ll_loads = {}
                if pipeline.assignment_type == "least_loaded" and eligible_users:
                    ll_loads = {user: 0 for user in eligible_users}
                    counts = (
                        CRM.objects.filter(
                            pipeline=pipeline, assigned_user__in=eligible_users
                        )
                        .values("assigned_user")
                        .annotate(c=Count("id"))
                    )
                    for item in counts:
                        user_obj = next(
                            (
                                u
                                for u in eligible_users
                                if u.id == item["assigned_user"]
                            ),
                            None,
                        )
                        if user_obj:
                            ll_loads[user_obj] = item["c"]

                crm_entries = []
                for contact in new_contacts:
                    assigned_user = None
                    if eligible_users:
                        if pipeline.assignment_type == "round_robin":
                            assigned_user = eligible_users[rr_index]
                            rr_index = (rr_index + 1) % len(eligible_users)
                        elif pipeline.assignment_type == "least_loaded":
                            assigned_user = min(ll_loads, key=ll_loads.get)
                            ll_loads[assigned_user] += 1

                    crm_entries.append(
                        CRM(
                            contact=contact,
                            pipeline_id=pipeline_id,
                            stage=first_stage,
                            priority="Medium",
                            assigned_user=assigned_user,
                        )
                    )

                CRM.objects.bulk_create(crm_entries, batch_size=1000)
                print(
                    f"[STAGE] after bulk_create CRM: queries={len(connection.queries) - _q0}"
                )

                Contact.objects.filter(id__in=new_contact_ids).update(status="Lead")
                print(
                    f"[STAGE] after Contact update: queries={len(connection.queries) - _q0}"
                )

                from contacts.models import ContactLog

                saved_crms = CRM.objects.filter(
                    pipeline_id=pipeline_id, contact_id__in=new_contact_ids
                ).select_related("contact", "assigned_user")

                # Deduplicate: skip contacts that already have a "Pipeline Added" log for this deal
                existing_log_contacts = set(
                    ContactLog.objects.filter(
                        crm__in=saved_crms, activity_type="Pipeline Added"
                    ).values_list("crm_id", flat=True)
                )

                log_entries = []
                for crm in saved_crms:
                    if crm.id in existing_log_contacts:
                        continue
                    log_entries.append(
                        ContactLog(
                            contact=crm.contact,
                            crm=crm,
                            activity_type="Pipeline Added",
                            description=f"Added to pipeline '{pipeline.name}' under stage '{first_stage.name if first_stage else 'Default'}'",
                            user=request.user,
                            pipeline_name=pipeline.name,
                        )
                    )
                    if crm.assigned_user:
                        log_entries.append(
                            ContactLog(
                                contact=crm.contact,
                                crm=crm,
                                activity_type="Assignment Changed",
                                description=f"Assigned to user {crm.assigned_user.first_name} {crm.assigned_user.last_name}".strip()
                                or crm.assigned_user.email,
                                user=request.user,
                                pipeline_name=pipeline.name,
                            )
                        )
                print(
                    f"[STAGE] after saved_crms loop: queries={len(connection.queries) - _q0}"
                )
                ContactLog.objects.bulk_create(log_entries, batch_size=1000)
                print(
                    f"[STAGE] after log bulk_create: queries={len(connection.queries) - _q0}"
                )

                _elapsed = time.time() - _t0
                _qtotal = len(connection.queries) - _q0
                print(
                    f"[TIMING] else branch: {_elapsed:.3f}s | queries={_qtotal} | new_ids={len(new_contact_ids)} | crm_entries={len(crm_entries)} | eligible_users={len(eligible_users)}"
                )
                _all_queries = connection.queries[-_qtotal:]
                _select_contacts = [
                    q
                    for q in _all_queries
                    if 'FROM "contacts_contact"' in q.get("sql", "")
                ]
                _select_crm = [
                    q for q in _all_queries if 'FROM "crm_crm"' in q.get("sql", "")
                ]
                _select_users = [
                    q
                    for q in _all_queries
                    if 'FROM "authentication_user"' in q.get("sql", "")
                ]
                print(
                    f"[TIMING]   contact SELECTs={len(_select_contacts)} | crm SELECTs={len(_select_crm)} | user SELECTs={len(_select_users)}"
                )
                return Response(
                    {
                        "message": f"Successfully added {len(crm_entries)} contacts to the pipeline.",
                        "added_count": len(crm_entries),
                    }
                )
        except Exception as e:
            import traceback

            print(f"[TIMING] EXCEPTION at {time.time() - _t0:.3f}s: {e}")
            traceback.print_exc()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="bulk-delete-deals")
    def bulk_delete_deals(self, request):
        """Bulk delete CRM entries by IDs."""
        deal_ids = request.data.get("deal_ids", [])

        if not deal_ids:
            return Response(
                {"error": "deal_ids list is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from contacts.models import ContactLog

            # Pre-fetch deals with contacts and pipelines for activity logging
            deals_to_delete = list(
                CRM.objects.filter(id__in=deal_ids).select_related(
                    "contact", "pipeline"
                )
            )

            if not deals_to_delete:
                return Response(
                    {"message": "No valid deals found to delete.", "deleted_count": 0}
                )

            # Create activity logs before deletion
            log_entries = []
            for crm in deals_to_delete:
                log_entries.append(
                    ContactLog(
                        contact=crm.contact,
                        crm=None,
                        activity_type="Deal Deleted",
                        description=f"Deal removed from pipeline '{crm.pipeline.name}'"
                        if crm.pipeline
                        else "Deal deleted",
                        user=request.user,
                        pipeline_name=crm.pipeline.name if crm.pipeline else None,
                    )
                )

            ContactLog.objects.bulk_create(log_entries, batch_size=1000)

            # Perform bulk delete
            deleted_count = CRM.objects.filter(id__in=deal_ids).delete()[0]

            return Response(
                {
                    "message": f"Successfully deleted {deleted_count} deals.",
                    "deleted_count": deleted_count,
                }
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="bulk-move-deals")
    def bulk_move_deals(self, request):
        """Bulk move deal cards (CRM entries) to a target pipeline and stage."""
        deal_ids = request.data.get("deal_ids", [])
        pipeline_id = request.data.get("pipeline_id")
        stage_id = request.data.get("stage_id")

        if not pipeline_id or not deal_ids:
            return Response(
                {"error": "pipeline_id and deal_ids list are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            if (
                request.user.role == "Staff"
                and not pipeline.departments.filter(
                    id__in=request.user.departments.all()
                ).exists()
            ):
                return Response(
                    {"error": "You do not have access to this pipeline."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Determine target stage
            target_stage = None
            if stage_id:
                target_stage = Stage.objects.filter(
                    id=stage_id, pipeline=pipeline
                ).first()
            if not target_stage:
                target_stage = (
                    Stage.objects.filter(pipeline=pipeline).order_by("order").first()
                )

            # Pre-fetch CRM records with existing contacts & pipeline names for activity logging
            deals_to_move = list(
                CRM.objects.filter(id__in=deal_ids).select_related(
                    "contact", "pipeline"
                )
            )

            if not deals_to_move:
                return Response(
                    {"message": "No valid deals found to move.", "moved_count": 0}
                )

            # Perform bulk update — reset assigned_user since target pipeline
            # may have different user groups
            moved_count = CRM.objects.filter(id__in=deal_ids).update(
                pipeline=pipeline,
                stage=target_stage,
                assigned_user=None,
            )

            # Create ContactLog entry with full context
            from contacts.models import ContactLog

            log_entries = []
            for crm in deals_to_move:
                old_pipeline_name = crm.pipeline.name if crm.pipeline else None
                new_pipeline_name = pipeline.name
                stage_name = target_stage.name if target_stage else "Default"

                description = f"Moved to pipeline '{new_pipeline_name}' under stage '{stage_name}'"
                if old_pipeline_name and old_pipeline_name != new_pipeline_name:
                    description = f"Moved from pipeline '{old_pipeline_name}' to '{new_pipeline_name}' under stage '{stage_name}'"

                log_entries.append(
                    ContactLog(
                        contact=crm.contact,
                        crm=crm,
                        activity_type="Pipeline Changed",
                        description=description,
                        user=request.user,
                        pipeline_name=new_pipeline_name,
                    )
                )

            ContactLog.objects.bulk_create(log_entries, batch_size=1000)

            return Response(
                {
                    "message": f"Successfully moved {moved_count} deals.",
                    "moved_count": moved_count,
                }
            )
        except Pipeline.DoesNotExist:
            return Response(
                {"error": "Target pipeline not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="bulk-move-to-stage")
    def bulk_move_to_stage(self, request):
        """Bulk move selected deals to a specific stage within the same pipeline."""
        deal_ids = request.data.get("deal_ids", [])
        stage_id = request.data.get("stage_id")

        if not stage_id or not deal_ids:
            return Response(
                {"error": "stage_id and deal_ids list are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_stage = Stage.objects.get(id=stage_id)
            pipeline = target_stage.pipeline

            if (
                request.user.role == "Staff"
                and not pipeline.departments.filter(
                    id__in=request.user.departments.all()
                ).exists()
            ):
                return Response(
                    {"error": "You do not have access to this pipeline."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            deals_to_move = list(
                CRM.objects.filter(id__in=deal_ids)
                .select_related("contact", "pipeline", "stage")
            )

            if not deals_to_move:
                return Response(
                    {"message": "No valid deals found to move.", "moved_count": 0}
                )

            moved_count = CRM.objects.filter(id__in=deal_ids).update(stage=target_stage)

            from contacts.models import ContactLog

            log_entries = []
            for crm in deals_to_move:
                old_stage_name = crm.stage.name if crm.stage else "No Stage"
                log_entries.append(
                    ContactLog(
                        contact=crm.contact,
                        crm=crm,
                        activity_type="Stage Changed",
                        description=f"Moved from stage '{old_stage_name}' to '{target_stage.name}'",
                        user=request.user,
                        pipeline_name=pipeline.name,
                    )
                )

            ContactLog.objects.bulk_create(log_entries, batch_size=1000)

            return Response(
                {
                    "message": f"Successfully moved {moved_count} deals to stage '{target_stage.name}'.",
                    "moved_count": moved_count,
                }
            )
        except Stage.DoesNotExist:
            return Response(
                {"error": "Target stage not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        """Unified, server-side paginated activity feed for a deal.

        Merges ContactLog entries and follow-up todos for the deal into a
        single timeline ordered by created_at (newest first), then paginates
        that merged stream so page boundaries match the rendered feed.
        """
        from django.db.models import Q
        from contacts.models import ContactLog
        from contacts.serializers import ContactLogSerializer
        from event_calendar.models import CalendarTodo
        from event_calendar.serializers import CalendarTodoSerializer
        from core.pagination import CustomPageNumberPagination

        deal = self.get_object()

        logs = ContactLog.objects.filter(crm_id=deal.id).select_related("user", "crm")
        todos = CalendarTodo.objects.filter(
            crm_id=deal.id, todo_type="followup"
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
