from rest_framework import viewsets, permissions, filters
from django.db.models import Q, Sum
from core.pagination import CustomPageNumberPagination
from payments.models import Payment, RecurringPaymentSchedule
from payments.serializers import PaymentSerializer, RecurringScheduleSerializer


class PaymentPageNumberPagination(CustomPageNumberPagination):
    """Paginated payment list with an opt-in exact total.

    The detail drawers page through the records, so a client-side sum would
    only cover the loaded rows. `?with_total=1` adds `total_amount` (SUM over
    the whole filtered queryset) so the collected figures stay exact.
    """

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        if self.request.query_params.get("with_total") in ("1", "true", "yes"):
            amount = self.page.paginator.object_list.aggregate(total=Sum("amount"))[
                "total"
            ]
            response.data["total_amount"] = str(amount) if amount is not None else "0"
        return response


def _restricted_to_own_deals(user):
    """Staff only see payments/rules for deals they are assigned to.
    Superadmins/Admins (and Django superusers) see everything."""
    return (
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == "Staff"
        and not getattr(user, "is_superuser", False)
    )


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related(
        "contact", "crm__pipeline", "crm__stage", "recorded_by"
    )
    serializer_class = PaymentSerializer
    pagination_class = PaymentPageNumberPagination
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "contact__name",
        "payment_for",
        "invoice",
        "payment_method",
        "crm__pipeline__name",
    ]
    ordering_fields = ["created_at", "amount"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        # Staff can only see payments recorded against deals assigned to them.
        if _restricted_to_own_deals(self.request.user):
            qs = qs.filter(crm__assigned_user=self.request.user)
        contact_id = self.request.query_params.get("contact")
        crm_id = self.request.query_params.get("crm")
        pipeline_ids = self.request.query_params.get("pipeline")
        user_ids = self.request.query_params.get("recorded_by")
        search = self.request.query_params.get("search")
        if contact_id:
            qs = qs.filter(contact_id=contact_id)
        if crm_id:
            qs = qs.filter(crm_id=crm_id)
        if pipeline_ids:
            ids = [v for v in pipeline_ids.split(",") if v]
            qs = qs.filter(crm__pipeline_id__in=ids)
        if user_ids:
            ids = [v for v in user_ids.split(",") if v]
            qs = qs.filter(recorded_by_id__in=ids)
        if search:
            search_field = self.request.query_params.get("search_field")
            if search_field:
                field_map = {
                    "contact": "contact__name__icontains",
                    "payment_for": "payment_for__icontains",
                    "invoice": "invoice__icontains",
                    "method": "payment_method__icontains",
                    "pipeline": "crm__pipeline__name__icontains",
                }
                lookup = field_map.get(search_field)
                if lookup:
                    qs = qs.filter(**{lookup: search})
                else:
                    qs = qs.filter(
                        Q(contact__name__icontains=search)
                        | Q(payment_for__icontains=search)
                        | Q(invoice__icontains=search)
                        | Q(payment_method__icontains=search)
                        | Q(crm__pipeline__name__icontains=search)
                    )
            else:
                qs = qs.filter(
                    Q(contact__name__icontains=search)
                    | Q(payment_for__icontains=search)
                    | Q(invoice__icontains=search)
                    | Q(payment_method__icontains=search)
                    | Q(crm__pipeline__name__icontains=search)
                )
        method = self.request.query_params.get("payment_method")
        if method:
            methods = [m.strip() for m in method.split(",") if m.strip()]
            qs = qs.filter(payment_method__in=methods)
        return qs

    def perform_create(self, serializer):
        payment = serializer.save(recorded_by=self.request.user)
        from contacts.models import ContactLog

        description = f"Recorded payment of ₹{float(payment.amount):,.2f} for '{payment.payment_for}'"
        ContactLog.objects.create(
            contact=payment.contact,
            crm=payment.crm,
            activity_type="Payment Recorded",
            description=description,
            user=self.request.user,
            pipeline_name=payment.crm.pipeline.name
            if payment.crm and payment.crm.pipeline
            else None,
        )
        if payment.crm_id:
            try:
                self._sync_pending_status(payment.crm)
            except Exception:
                pass

    def _sync_pending_status(self, crm):
        from payments.models import RecurringPaymentSchedule, Payment
        from django.utils import timezone
        from datetime import timedelta

        rule = (
            RecurringPaymentSchedule.objects.filter(
                pipeline_id=crm.pipeline_id, status="active"
            )
            .order_by("-created_at")
            .first()
        )
        if not rule:
            return
        is_single_check = str(rule.cycle_count) == "1"
        if is_single_check and not rule.due_date:
            if crm.contact.status in ("Paid", "Due", "Payment Pending"):
                crm.contact.status = "Lead"
                crm.contact.save(update_fields=["status"])
            return
        if not is_single_check and not (rule.due_date or rule.start_date):
            return
        qs = Payment.objects.filter(crm=crm, payment_for=rule.payment_for)
        count = qs.count()
        today = timezone.now().date()
        is_single = str(rule.cycle_count) == "1"
        new_status = None
        if is_single:
            if count > 0:
                new_status = "Paid"
            elif today >= rule.due_date:
                new_status = "Due"
        else:
            first_due = rule.due_date or rule.start_date
            if count >= rule.cycle_count:
                new_status = "Paid"
            elif count == 0:
                if today < first_due:
                    new_status = "Payment Pending"
                else:
                    new_status = "Due"
            else:
                curr_due = first_due + timedelta(
                    days=rule.cycle_period_days * (count - 1)
                )
                next_due = first_due + timedelta(days=rule.cycle_period_days * count)
                if today <= curr_due:
                    new_status = "Paid"
                elif today < next_due:
                    new_status = "Payment Pending"
                else:
                    new_status = "Due"
        contact = crm.contact
        if new_status and contact.status != new_status:
            contact.status = new_status
            contact.save(update_fields=["status"])
        elif not new_status and contact.status in ("Paid", "Due", "Payment Pending"):
            contact.status = "Lead"
            contact.save(update_fields=["status"])


class RecurringScheduleViewSet(viewsets.ModelViewSet):
    queryset = RecurringPaymentSchedule.objects.all().select_related(
        "contact", "crm", "pipeline", "created_by"
    )
    serializer_class = RecurringScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        # Staff only see rules for pipelines whose departments they belong to.
        if _restricted_to_own_deals(self.request.user):
            qs = qs.filter(
                pipeline__departments__in=self.request.user.departments.all()
            ).distinct()
        pipeline_id = self.request.query_params.get("pipeline")
        contact_id = self.request.query_params.get("contact")
        if pipeline_id:
            qs = qs.filter(pipeline_id=pipeline_id)
        if contact_id:
            qs = qs.filter(contact_id=contact_id)
        return qs

    def _supersede_other_rules(self, pipeline_id, exclude_pk=None):
        """Enforce one active rule per pipeline: cancel other active
        pipeline-wide rules on this pipeline. Must run BEFORE saving a new
        active rule, otherwise the DB unique constraint will reject the save."""
        qs = RecurringPaymentSchedule.objects.filter(
            pipeline_id=pipeline_id,
            status="active",
            contact__isnull=True,
        )
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        return qs.update(status="cancelled")

    def perform_update(self, serializer):
        from django.db import transaction

        vd = serializer.validated_data
        obj = serializer.instance
        will_be_active = vd.get("status", obj.status) == "active"
        contact_after = vd.get("contact", obj.contact)
        with transaction.atomic():
            if will_be_active and obj.pipeline_id and contact_after is None:
                self._supersede_other_rules(obj.pipeline_id, exclude_pk=obj.pk)
            obj = serializer.save()

    def perform_create(self, serializer):
        from django.db import transaction

        vd = serializer.validated_data
        pipeline = vd.get("pipeline")
        status_val = vd.get("status", "active")
        with transaction.atomic():
            if pipeline and status_val == "active" and vd.get("contact") is None:
                self._supersede_other_rules(pipeline.pk)
            obj = serializer.save(created_by=self.request.user)
        if obj.contact_id:
            from contacts.models import ContactLog

            ContactLog.objects.create(
                contact=obj.contact,
                crm=obj.crm,
                activity_type="Recurring Payment Rule Created",
                description=f"Rule ₹{float(obj.amount):,.2f} x{obj.cycle_count} every {obj.cycle_period_days}d for '{obj.payment_for}' on {obj.contact.name}",
                user=self.request.user,
                pipeline_name=obj.pipeline.name
                if obj.pipeline
                else (obj.crm.pipeline.name if obj.crm and obj.crm.pipeline else None),
            )
        if obj.pipeline_id and not obj.contact_id:
            from crm.models import CRM

            deals = CRM.objects.filter(pipeline_id=obj.pipeline_id).select_related(
                "contact"
            )
            if deals.exists():
                from contacts.models import ContactLog

                logs = []
                for d in deals:
                    logs.append(
                        ContactLog(
                            contact=d.contact,
                            crm=d,
                            activity_type="Payment Rule Applied",
                            description=f"Pipeline rule ₹{float(obj.amount):,.2f} x{obj.cycle_count} every {obj.cycle_period_days}d '{obj.payment_for}' applied",
                            user=self.request.user,
                            pipeline_name=obj.pipeline.name,
                        )
                    )
                ContactLog.objects.bulk_create(logs, batch_size=1000)
                try:
                    from django.utils import timezone
                    from payments.models import Payment as PayModel
                    from contacts.models import Contact

                    today = timezone.now().date()
                    eff_due = obj.due_date or obj.start_date
                    if not eff_due:
                        return
                    is_single = str(obj.cycle_count) == "1"
                    if is_single:
                        if today < eff_due:
                            return
                        paid_crm_ids = (
                            PayModel.objects.filter(
                                crm_id__in=deals.values_list("id", flat=True),
                                payment_for=obj.payment_for,
                            )
                            .values_list("crm_id", flat=True)
                            .distinct()
                        )
                        unpaid = deals.exclude(id__in=paid_crm_ids)
                        paid = deals.filter(id__in=paid_crm_ids)
                        if unpaid.exists():
                            Contact.objects.filter(
                                id__in=list(unpaid.values_list("contact_id", flat=True))
                            ).update(status="Due")
                        if paid.exists():
                            Contact.objects.filter(
                                id__in=list(paid.values_list("contact_id", flat=True))
                            ).update(status="Paid")
                    else:
                        if today < eff_due:
                            Contact.objects.filter(
                                id__in=list(deals.values_list("contact_id", flat=True))
                            ).update(status="Payment Pending")
                        else:
                            Contact.objects.filter(
                                id__in=list(deals.values_list("contact_id", flat=True))
                            ).update(status="Due")
                except Exception:
                    pass
