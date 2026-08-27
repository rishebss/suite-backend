from rest_framework import serializers
from payments.models import Payment, RecurringPaymentSchedule
from contacts.serializers import ContactSerializer


class PaymentSerializer(serializers.ModelSerializer):
    contact_details = ContactSerializer(source="contact", read_only=True)
    recorded_by_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "contact",
            "contact_details",
            "crm",
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
