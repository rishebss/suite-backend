from rest_framework import serializers
from payments.models import Payment, RecurringPaymentSchedule
from contacts.serializers import ContactSerializer


class PaymentSerializer(serializers.ModelSerializer):
    contact_details = ContactSerializer(source="contact", read_only=True)
    recorded_by_details = serializers.SerializerMethodField(read_only=True)
    crm_details = serializers.SerializerMethodField(read_only=True)
    pipeline_name = serializers.CharField(
        source="crm.pipeline.name", read_only=True, default=None
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "contact",
            "contact_details",
            "crm",
            "crm_details",
            "pipeline_name",
            "recorded_by",
            "recorded_by_details",
            "amount",
            "payment_for",
            "remarks",
            "invoice",
            "payment_method",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "recorded_by_details"]

    def get_recorded_by_details(self, obj):
        if obj.recorded_by:
            return {
                "id": obj.recorded_by.id,
                "first_name": obj.recorded_by.first_name,
                "last_name": obj.recorded_by.last_name,
                "email": obj.recorded_by.email,
            }
        return None

    def get_crm_details(self, obj):
        if obj.crm:
            return {
                "id": str(obj.crm.id),
                "pipeline": str(obj.crm.pipeline_id) if obj.crm.pipeline_id else None,
                "pipeline_name": obj.crm.pipeline.name if obj.crm.pipeline else None,
                "stage": str(obj.crm.stage_id) if obj.crm.stage_id else None,
            }
        return None

    def validate(self, attrs):
        crm = (
            attrs.get("crm")
            if "crm" in attrs
            else (self.instance.crm if self.instance else None)
        )
        if crm and getattr(crm, "pipeline_id", None):
            rule = (
                RecurringPaymentSchedule.objects.filter(
                    pipeline_id=crm.pipeline_id, status="active"
                )
                .order_by("-created_at")
                .first()
            )
            if rule:
                errors = {}
                if (
                    attrs.get("payment_for") is not None
                    and attrs.get("payment_for") != rule.payment_for
                ):
                    errors["payment_for"] = (
                        f"Must match pipeline rule: '{rule.payment_for}'."
                    )
                if attrs.get("amount") is not None and str(attrs.get("amount")) != str(
                    rule.amount
                ):
                    try:
                        if float(attrs.get("amount")) != float(rule.amount):
                            errors["amount"] = (
                                f"Must be ₹{rule.amount} per pipeline rule."
                            )
                    except Exception:
                        errors["amount"] = f"Must be ₹{rule.amount} per pipeline rule."
                if (
                    attrs.get("payment_method") is not None
                    and rule.payment_method != "Any"
                    and attrs.get("payment_method") != rule.payment_method
                ):
                    errors["payment_method"] = (
                        f"Must be '{rule.payment_method}' per pipeline rule."
                    )
                if errors:
                    raise serializers.ValidationError(errors)
                qs = Payment.objects.filter(crm=crm, payment_for=rule.payment_for)
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                count = qs.count()
                if count >= rule.cycle_count:
                    raise serializers.ValidationError(
                        {"detail": "All cycles completed for this pipeline rule."}
                    )
                is_recurring = str(rule.cycle_count) != "1"
                if is_recurring and count > 0:
                    last = qs.order_by("-created_at").first()
                    if last:
                        from datetime import timedelta

                        next_due = last.created_at.date() + timedelta(
                            days=rule.cycle_period_days
                        )
                        from django.utils import timezone

                        if timezone.now().date() < next_due:
                            raise serializers.ValidationError(
                                {
                                    "detail": f"Next payment due on {next_due.isoformat()}."
                                }
                            )
                if not is_recurring and count > 0:
                    raise serializers.ValidationError(
                        {"detail": "One-time pipeline payment already recorded."}
                    )
                if not attrs.get("invoice") and not (
                    self.instance and self.instance.invoice
                ):
                    raise serializers.ValidationError(
                        {
                            "invoice": "Invoice number required for pipeline rule payment."
                        }
                    )
        return attrs


class RecurringScheduleSerializer(serializers.ModelSerializer):
    contact_details = ContactSerializer(source="contact", read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = RecurringPaymentSchedule
        fields = [
            "id",
            "contact",
            "contact_details",
            "crm",
            "pipeline",
            "created_by",
            "amount",
            "payment_for",
            "payment_method",
            "cycle_period_days",
            "cycle_count",
            "completed_cycles",
            "start_date",
            "next_due_date",
            "due_date",
            "status",
            "remarks",
            "total_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "completed_cycles",
            "next_due_date",
            "created_at",
            "updated_at",
            "total_amount",
        ]

    def get_total_amount(self, obj):
        try:
            return float(obj.amount) * int(obj.cycle_count)
        except Exception:
            return 0

    def validate(self, attrs):
        if not attrs.get("pipeline") and not self.instance:
            raise serializers.ValidationError(
                {"pipeline": "Pipeline is required for pipeline-wide rule."}
            )
        return attrs

    def validate_cycle_period_days(self, v):
        if v < 1 or v > 365:
            raise serializers.ValidationError("Cycle period must be 1-365 days.")
        return v

    def validate_cycle_count(self, v):
        if v < 1 or v > 60:
            raise serializers.ValidationError("Cycle count must be 1-60.")
        return v
