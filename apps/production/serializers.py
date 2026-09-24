
from rest_framework import serializers

from .models import EggProduction


class EggProductionSerializer(serializers.ModelSerializer):
    flock_code = serializers.CharField(
        source="flock.code",
        read_only=True
    )

    flock_name = serializers.CharField(
        source="flock.name",
        read_only=True
    )

    total_eggs = serializers.SerializerMethodField()

    class Meta:
        model = EggProduction

        fields = [
            "id",
            "flock",
            "flock_code",
            "flock_name",
            "date",
            "eggs_collected",
            "broken_eggs",
            "rejected_eggs",
            "trays",
            "notes",
            "total_eggs",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "flock_code",
            "flock_name",
            "total_eggs",
            "created_at",
            "updated_at",
        ]

    def get_total_eggs(self, obj):
        return (
            (obj.eggs_collected or 0)
            + (obj.broken_eggs or 0)
            + (obj.rejected_eggs or 0)
        )
