from rest_framework import serializers
from contacts.models import (
    Contact,
    ImportBatch,
    ContactLog,
    ContactRemark,
    ContactDocument,
)


class ImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = ["id", "name", "contact_count", "created_at"]
        read_only_fields = ["id", "contact_count", "created_at"]


class ContactListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "status",
            "contact_id",
            "source",
            "additional_data",
            "created_at",
        ]
        read_only_fields = fields


class ContactSerializer(serializers.ModelSerializer):
    pipelines = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = "__all__"
        read_only_fields = ("contact_id", "created_at", "updated_at", "pipelines")

    def get_pipelines(self, obj):
        crm_deals = obj.crm_pipelines.all().select_related("pipeline", "stage")
        results = []
        for deal in crm_deals:
            results.append(
                {
                    "deal_id": deal.id,
                    "pipeline_id": deal.pipeline.id if deal.pipeline else None,
                    "pipeline_name": deal.pipeline.name
                    if deal.pipeline
                    else "Unknown Pipeline",
                    "stage_id": deal.stage.id if deal.stage else None,
                    "stage_name": deal.stage.name if deal.stage else "Unknown Stage",
                    "priority": deal.priority,
                    "value": deal.value,
                }
            )
        return results

    def validate(self, data):
        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        if not name:
            raise serializers.ValidationError({"name": "This field is required."})
        if not email and not phone:
            raise serializers.ValidationError("Either phone or email must be provided.")
        return data


class ContactLogSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ContactLog
        fields = [
            "id",
            "contact",
            "crm",
            "user",
            "user_details",
            "pipeline_name",
            "activity_type",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user_details"]

    def get_user_details(self, obj):
        if obj.user:
            return {
                "id": obj.user.id,
                "first_name": obj.user.first_name,
                "last_name": obj.user.last_name,
                "email": obj.user.email,
            }
        return None


class ContactRemarkSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ContactRemark
        fields = [
            "id",
            "contact",
            "crm",
            "user",
            "user_details",
            "text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user_details"]

    def get_user_details(self, obj):
        if obj.user:
            return {
                "id": obj.user.id,
                "first_name": obj.user.first_name,
                "last_name": obj.user.last_name,
                "email": obj.user.email,
            }
        return None


class ContactDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactDocument
        fields = [
            "id",
            "contact",
            "document_type",
            "file",
            "file_name",
            "description",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "file_name",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        validated_data["file_name"] = validated_data["file"].name
        return super().create(validated_data)
