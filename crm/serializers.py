from rest_framework import serializers
from crm.models import CRM, Pipeline, Stage
from contacts.models import Contact
from authentication.models import User, Department
from authentication.serializers import DepartmentSerializer


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "mobile",
            "role",
            "is_active",
        ]


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ["id", "pipeline", "name", "slug", "order", "color"]
        read_only_fields = ["id", "slug", "pipeline"]


class PipelineSerializer(serializers.ModelSerializer):
    stages = StageSerializer(many=True, read_only=True)
    departments = DepartmentSerializer(many=True, read_only=True)
    deals_count = serializers.SerializerMethodField()
    assigned_user_details = UserBriefSerializer(source="assigned_user", read_only=True)
    department_ids = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source="departments",
        many=True,
        required=False,
        write_only=True,
    )

    def get_deals_count(self, obj):
        if hasattr(obj, "deals_count"):
            return obj.deals_count
        return obj.deals.count()

    class Meta:
        model = Pipeline
        fields = [
            "id",
            "name",
            "description",
            "stages",
            "departments",
            "department_ids",
            "deals_count",
            "assignment_type",
            "assigned_user",
            "assigned_user_details",
            "pipeline_type",
            "mandatory_fields",
            "custom_fields_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ContactBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "status",
            "contact_id",
            "additional_data",
            "source",
        ]


class CRMSerializer(serializers.ModelSerializer):
    contact_details = ContactBriefSerializer(source="contact", read_only=True)
    stage_details = StageSerializer(source="stage", read_only=True)
    assigned_user_details = UserBriefSerializer(source="assigned_user", read_only=True)

    class Meta:
        model = CRM
        fields = [
            "id",
            "contact",
            "contact_details",
            "pipeline",
            "stage",
            "stage_details",
            "assigned_user",
            "assigned_user_details",
            "value",
            "priority",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
