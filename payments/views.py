from rest_framework import viewsets, permissions
from payments.models import Payment, RecurringPaymentSchedule
from payments.serializers import PaymentSerializer, RecurringScheduleSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related("contact", "crm", "recorded_by")
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        contact_id = self.request.query_params.get("contact")
        crm_id = self.request.query_params.get("crm")
        pipeline_id = self.request.query_params.get("pipeline")
        if contact_id:
            qs = qs.filter(contact_id=contact_id)
        if crm_id:
            qs = qs.filter(crm_id=crm_id)
        if pipeline_id:
            qs = qs.filter(crm__pipeline_id=pipeline_id)
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
        pipeline_id = self.request.query_params.get("pipeline")
        contact_id = self.request.query_params.get("contact")
        if pipeline_id:
            qs = qs.filter(pipeline_id=pipeline_id)
        if contact_id:
            qs = qs.filter(contact_id=contact_id)
        return qs

    def perform_create(self, serializer):
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
