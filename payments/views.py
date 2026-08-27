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
