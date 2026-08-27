from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.models import User, Department, AuditLog


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""

    user_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, required=False, write_only=True
    )
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "name", "description", "user_ids", "user_count"]
        read_only_fields = ["id"]

    def get_user_count(self, obj):
        return obj.users.count()

    def create(self, validated_data):
        user_ids = validated_data.pop("user_ids", [])
        department = Department.objects.create(**validated_data)
        if user_ids:
            department.users.add(*user_ids)
        return department

    def update(self, instance, validated_data):
        user_ids = validated_data.pop("user_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if user_ids is not None:
            instance.users.set(user_ids)
        return instance


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - read-only"""

    departments = DepartmentSerializer(many=True, read_only=True)
    account_id = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "mobile",
            "account_id",
            "role",
            "departments",
            "is_email_verified",
            "is_mobile_verified",
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "account_id",
            "is_email_verified",
            "is_mobile_verified",
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "mobile",
            "password",
            "password_confirm",
            "role",
            "gender",
        ]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate(self, data):
        """Validate that passwords match"""
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        """Create user with hashed password"""
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name"),
            last_name=validated_data.get("last_name"),
            mobile=validated_data.get("mobile"),
            role=validated_data.get("role", "User"),
            gender=validated_data.get("gender"),
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer with additional user info"""

    def validate(self, attrs):
        # Use email instead of username
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_active:
            raise serializers.ValidationError("User is inactive")

        # Get tokens
        refresh = RefreshToken.for_user(user)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        }

        return data


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for token refresh endpoint"""

    refresh = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    """Serializer for login endpoint"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""

    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "mobile", "gender"]
        extra_kwargs = {
            "mobile": {"required": False},
            "gender": {"required": False},
        }


class SendVerificationEmailSerializer(serializers.Serializer):
    """Serializer for sending verification email"""

    email = serializers.EmailField()
    purpose = serializers.ChoiceField(
        choices=["email_verify", "password_reset", "mobile_verify"],
        default="email_verify",
    )


class VerifyEmailSerializer(serializers.Serializer):
    """Serializer for verifying email with token"""

    email = serializers.EmailField()
    token = serializers.CharField(max_length=6, min_length=6)
    purpose = serializers.ChoiceField(
        choices=["email_verify", "password_reset", "mobile_verify"],
        default="email_verify",
    )


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for initiating password reset"""

    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for resetting password"""

    email = serializers.EmailField()
    token = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError("Passwords do not match.")
        return data


# ============= User Management Serializers =============


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer for admin user management"""

    departments = DepartmentSerializer(many=True, read_only=True)
    supervisor = serializers.SerializerMethodField()
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "mobile",
            "gender",
            "account_id",
            "role",
            "departments",
            "supervisor",
            "organization_name",
            "avatar",
            "is_active",
            "is_email_verified",
            "is_mobile_verified",
            "is_staff",
            "is_superuser",
            "created_at",
            "updated_at",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "account_id",
            "is_staff",
            "is_superuser",
            "created_at",
            "updated_at",
        ]

    def get_supervisor(self, obj):
        if obj.supervisor:
            return {
                "id": str(obj.supervisor.id),
                "email": obj.supervisor.email,
                "first_name": obj.supervisor.first_name,
                "last_name": obj.supervisor.last_name,
            }
        return None


class UserListSerializer(serializers.ModelSerializer):
    """Simplified user serializer for list views"""

    departments = DepartmentSerializer(many=True, read_only=True)
    supervisor_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "mobile",
            "gender",
            "account_id",
            "role",
            "departments",
            "supervisor_name",
            "is_active",
            "is_email_verified",
            "last_login",
            "created_at",
        ]
        read_only_fields = fields

    def get_supervisor_name(self, obj):
        if obj.supervisor:
            return f"{obj.supervisor.first_name} {obj.supervisor.last_name}".strip()
        return None


class AssignableUserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for assignment dropdowns"""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users by admin"""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    department_ids = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source="departments",
        many=True,
        required=False,
    )
    supervisor_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="supervisor",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "mobile",
            "password",
            "password_confirm",
            "role",
            "gender",
            "department_ids",
            "supervisor_id",
        ]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "role": {"required": True},
        }

    def validate(self, data):
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        if data.get("supervisor"):
            # Ensure supervisor is not the same as the user being created
            if data["supervisor"].email == data["email"]:
                raise serializers.ValidationError(
                    {"supervisor_id": "User cannot be their own supervisor."}
                )
        return data

    def create(self, validated_data):
        departments = validated_data.pop("departments", [])
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data.pop("password"),
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            mobile=validated_data.get("mobile"),
            role=validated_data.get("role", "User"),
            gender=validated_data.get("gender"),
            supervisor=validated_data.get("supervisor"),
        )
        if departments:
            user.departments.add(*departments)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing users"""

    department_ids = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source="departments",
        many=True,
        required=False,
    )
    supervisor_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="supervisor",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "mobile",
            "gender",
            "role",
            "department_ids",
            "supervisor_id",
            "is_active",
            "avatar",
        ]

    def validate(self, data):
        if data.get("supervisor"):
            # Prevent user from being their own supervisor
            if data["supervisor"].id == self.instance.id:
                raise serializers.ValidationError(
                    {"supervisor_id": "User cannot be their own supervisor."}
                )
        return data

    def update(self, instance, validated_data):
        # Track changes for audit logging
        changes = {}

        departments = validated_data.pop("departments", None)

        for field, value in validated_data.items():
            old_value = getattr(instance, field)
            if old_value != value:
                if field == "supervisor" and value:
                    old_name = (
                        f"{old_value.first_name} {old_value.last_name}".strip()
                        if old_value
                        else None
                    )
                    new_name = f"{value.first_name} {value.last_name}".strip()
                    changes[field] = {"old": old_name, "new": new_name}
                else:
                    changes[field] = {"old": old_value, "new": value}
                setattr(instance, field, value)

        instance.save()

        if departments is not None:
            old_departments = list(instance.departments.all())
            instance.departments.set(departments)
            new_departments = list(instance.departments.all())
            if old_departments != new_departments:
                changes["departments"] = {
                    "old": [d.name for d in old_departments],
                    "new": [d.name for d in new_departments],
                }

        # Store changes in context for view to use
        self.context["changes"] = changes
        return instance


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit log entries"""

    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    action_target_email = serializers.CharField(
        source="action_target.email", read_only=True, allow_null=True
    )
    action_target_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "user_email",
            "user_name",
            "action_target_email",
            "action_target_name",
            "ip_address",
            "user_agent",
            "status",
            "details",
            "target_changes",
            "created_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email

    def get_action_target_name(self, obj):
        if obj.action_target:
            return (
                f"{obj.action_target.first_name} {obj.action_target.last_name}".strip()
                or obj.action_target.email
            )
        return None


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activities (filtered audit logs)"""

    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "user_name",
            "ip_address",
            "status",
            "details",
            "target_changes",
            "created_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
