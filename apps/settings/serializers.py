from rest_framework import serializers

from .models import FarmSettings


class FarmSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmSettings

        fields = [
            "id",

            # Farm Profile
            "farm_name",
            "owner_name",
            "phone",
            "email",
            "location",
            "address",

            # Preferences
            "currency",
            "timezone",
            "date_format",

            # Alerts
            "low_stock_alerts",
            "mortality_alerts",
            "vaccination_alerts",
            "production_alerts",

            # Notifications
            "email_notifications",
            "sms_notifications",

            # Timestamps
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_farm_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Farm name is required."
            )

        return value

    def validate_owner_name(self, value):
        return value.strip()

    def validate_timezone(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Timezone is required."
            )

        return value
