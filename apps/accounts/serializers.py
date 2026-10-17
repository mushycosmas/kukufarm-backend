from django.contrib.auth.models import Permission, User

from rest_framework import serializers

from .models import Role, UserProfile


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only representation of a KukuFarm user.

    Returns user details, assigned role, profile information,
    and the permission codes assigned to the user's role.
    """

    role = serializers.SerializerMethodField()
    role_id = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "role",
            "role_id",
            "phone",
            "job_title",
            "active",
            "date_joined",
            "permissions",
        ]

        read_only_fields = fields

    def get_role(self, obj):
        """Return the assigned role as an object."""

        profile = getattr(obj, "profile", None)

        if not profile or not profile.role:
            return None

        return {
            "id": profile.role.id,
            "name": profile.role.name,
            "code": profile.role.code,
        }

    def get_role_id(self, obj):
        """Return the assigned role's database ID."""

        profile = getattr(obj, "profile", None)

        if not profile:
            return None

        return profile.role_id

    def get_phone(self, obj):
        """Return the user's phone number."""

        profile = getattr(obj, "profile", None)

        if not profile:
            return ""

        return profile.phone or ""

    def get_job_title(self, obj):
        """Return the user's job title."""

        profile = getattr(obj, "profile", None)

        if not profile:
            return ""

        return profile.job_title or ""

    def get_active(self, obj):
        """Return the UserProfile active status."""

        profile = getattr(obj, "profile", None)

        if not profile:
            return False

        return profile.active

    def get_permissions(self, obj):
        """
        Return permission codes assigned to the user's role.

        Example:
            [
                "customers.view_customer",
                "customers.add_customer"
            ]
        """

        profile = getattr(obj, "profile", None)

        if not profile or not profile.role:
            return []

        permissions = (
            profile.role.permissions
            .select_related("content_type")
            .all()
        )

        return sorted(
            f"{permission.content_type.app_label}."
            f"{permission.codename}"
            for permission in permissions
        )


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating KukuFarm users.

    The frontend sends role_id, which maps to UserProfile.role.
    Profile fields are saved to the associated UserProfile.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=6,
        required=False,
        allow_blank=False,
    )

    role_id = serializers.PrimaryKeyRelatedField(
        source="profile.role",
        queryset=Role.objects.filter(active=True),
        required=False,
        allow_null=True,
    )

    phone = serializers.CharField(
        source="profile.phone",
        required=False,
        allow_blank=True,
    )

    job_title = serializers.CharField(
        source="profile.job_title",
        required=False,
        allow_blank=True,
    )

    active = serializers.BooleanField(
        source="profile.active",
        required=False,
        default=True,
    )

    class Meta:
        model = User

        fields = [
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "role_id",
            "phone",
            "job_title",
            "active",
        ]

    def create(self, validated_data):
        """Create a user and its associated profile."""

        profile_data = validated_data.pop("profile", {})
        password = validated_data.pop("password", None)

        user = User(**validated_data)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save()

        UserProfile.objects.create(
            user=user,
            **profile_data,
        )

        return user

    def update(self, instance, validated_data):
        """Update user details and associated profile fields."""

        profile_data = validated_data.pop("profile", {})
        password = validated_data.pop("password", None)

        # Update Django User fields.
        for field, value in validated_data.items():
            setattr(instance, field, value)

        # Update the password only when a new one is supplied.
        if password:
            instance.set_password(password)

        instance.save()

        # Get or create the user's profile.
        profile, _ = UserProfile.objects.get_or_create(
            user=instance,
        )

        # Update supplied profile fields only.
        for field, value in profile_data.items():
            setattr(profile, field, value)

        profile.save()

        return instance


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer for dynamic KukuFarm roles.

    Incoming requests use permission IDs:

        {
            "name": "Farm Manager",
            "code": "farm_manager",
            "description": "Manages farm operations",
            "active": true,
            "permissions": [1, 2, 3, 4]
        }

    API responses return detailed permission objects.
    """

    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Role

        fields = [
            "id",
            "name",
            "code",
            "description",
            "active",
            "permissions",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        """Return detailed permission information to React."""

        representation = super().to_representation(instance)

        permissions = (
            instance.permissions
            .select_related("content_type")
            .all()
        )

        representation["permissions"] = [
            {
                "id": permission.id,
                "code": (
                    f"{permission.content_type.app_label}."
                    f"{permission.codename}"
                ),
                "name": permission.name,
                "codename": permission.codename,
                "app_label": permission.content_type.app_label,
            }
            for permission in permissions
        ]

        return representation
