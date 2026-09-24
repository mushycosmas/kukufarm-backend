from django.contrib.auth.models import Permission, User

from rest_framework import serializers

from .models import Role, UserProfile


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only representation of a KukuFarm user.

    Returns the user's dynamic Role as an object and also
    exposes role_id for frontend form handling.
    """

    role = serializers.SerializerMethodField()

    role_id = serializers.SerializerMethodField()

    phone = serializers.SerializerMethodField()

    job_title = serializers.SerializerMethodField()

    active = serializers.SerializerMethodField()

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
        ]

    def get_role(self, obj):
        """
        Return the user's role as an object.
        """

        profile = getattr(obj, "profile", None)

        if not profile or not profile.role:
            return None

        return {
            "id": profile.role.id,
            "name": profile.role.name,
            "code": profile.role.code,
        }

    def get_role_id(self, obj):
        """
        Return the database Role ID.
        """

        profile = getattr(obj, "profile", None)

        if not profile:
            return None

        return profile.role_id

    def get_phone(self, obj):
        """
        Return user's phone number.
        """

        profile = getattr(obj, "profile", None)

        if not profile:
            return ""

        return profile.phone

    def get_job_title(self, obj):
        """
        Return user's job title.
        """

        profile = getattr(obj, "profile", None)

        if not profile:
            return ""

        return profile.job_title

    def get_active(self, obj):
        """
        Return UserProfile active status.
        """

        profile = getattr(obj, "profile", None)

        if not profile:
            return False

        return profile.active


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer used when creating or updating KukuFarm users.

    The frontend sends:

        role_id: 1

    which is mapped to:

        UserProfile.role
    """

    password = serializers.CharField(
        write_only=True,
        min_length=6,
        required=False,
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
        """
        Create a User together with UserProfile.
        """

        profile_data = validated_data.pop(
            "profile",
            {},
        )

        password = validated_data.pop(
            "password",
            None,
        )

        user = User.objects.create(
            **validated_data
        )

        if password:
            user.set_password(password)

        user.save()

        UserProfile.objects.create(
            user=user,
            **profile_data,
        )

        return user

    def update(self, instance, validated_data):
        """
        Update User and UserProfile.
        """

        profile_data = validated_data.pop(
            "profile",
            {},
        )

        password = validated_data.pop(
            "password",
            None,
        )

        # Update Django User fields
        for key, value in validated_data.items():
            setattr(
                instance,
                key,
                value,
            )

        # Update password correctly
        if password:
            instance.set_password(password)

        instance.save()

        # Get or create UserProfile
        profile, _ = UserProfile.objects.get_or_create(
            user=instance,
        )

        # Update profile fields
        for key, value in profile_data.items():
            setattr(
                profile,
                key,
                value,
            )

        profile.save()

        return instance


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer for dynamic KukuFarm roles.

    CREATE / UPDATE request:

        {
            "name": "Farm Manager",
            "code": "farm_manager",
            "description": "Manages farm operations",
            "active": true,
            "permissions": [1, 2, 3, 4]
        }

    The frontend sends permission IDs.

    API response returns detailed permission objects.
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
        """
        Convert permission IDs into detailed permission
        objects when returning data to React.
        """

        representation = super().to_representation(
            instance
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
            for permission in instance.permissions.select_related(
                "content_type"
            ).all()
        ]

        return representation
