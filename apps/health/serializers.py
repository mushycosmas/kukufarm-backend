
from django.db import transaction

from rest_framework import serializers

from .models import (
    HealthRecord,
    Vaccination,
    Mortality,
)


# ============================================================
# HEALTH RECORD
# ============================================================

class HealthRecordSerializer(serializers.ModelSerializer):

    flock_code = serializers.CharField(
        source="flock.code",
        read_only=True,
    )

    flock_name = serializers.CharField(
        source="flock.name",
        read_only=True,
    )

    class Meta:
        model = HealthRecord

        fields = [
            "id",

            "flock",
            "flock_code",
            "flock_name",

            "date",
            "condition",
            "symptoms",
            "treatment",
            "medicine",
            "dosage",
            "veterinarian",
            "notes",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "flock_code",
            "flock_name",
            "created_at",
            "updated_at",
        ]


# ============================================================
# VACCINATION
# ============================================================

class VaccinationSerializer(serializers.ModelSerializer):

    flock_code = serializers.CharField(
        source="flock.code",
        read_only=True,
    )

    flock_name = serializers.CharField(
        source="flock.name",
        read_only=True,
    )

    class Meta:
        model = Vaccination

        fields = [
            "id",

            "flock",
            "flock_code",
            "flock_name",

            "vaccine",
            "date",
            "next_due_date",
            "dosage",
            "administered_by",
            "notes",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "flock_code",
            "flock_name",
            "created_at",
            "updated_at",
        ]


# ============================================================
# MORTALITY
# ============================================================

class MortalitySerializer(serializers.ModelSerializer):

    flock_code = serializers.CharField(
        source="flock.code",
        read_only=True,
    )

    flock_name = serializers.CharField(
        source="flock.name",
        read_only=True,
    )

    class Meta:
        model = Mortality

        fields = [
            "id",

            "flock",
            "flock_code",
            "flock_name",

            "date",
            "quantity",
            "cause",
            "notes",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "flock_code",
            "flock_name",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Create mortality and reduce flock current quantity.
        """

        with transaction.atomic():

            flock = validated_data["flock"]
            quantity = validated_data["quantity"]

            if quantity > flock.current_quantity:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "Mortality cannot exceed current flock "
                            f"quantity of {flock.current_quantity}."
                        )
                    }
                )

            obj = Mortality.objects.create(
                **validated_data
            )

            flock.current_quantity -= quantity

            flock.save(
                update_fields=[
                    "current_quantity",
                    "updated_at",
                ]
            )

            return obj

    def update(self, instance, validated_data):
        """
        Safely update mortality.

        The old mortality quantity is returned to the flock first,
        then the new mortality quantity is applied.
        """

        with transaction.atomic():

            old_flock = instance.flock
            old_quantity = instance.quantity

            new_flock = validated_data.get(
                "flock",
                old_flock,
            )

            new_quantity = validated_data.get(
                "quantity",
                old_quantity,
            )

            # Return previous mortality to old flock.
            old_flock.current_quantity += old_quantity

            old_flock.save(
                update_fields=[
                    "current_quantity",
                    "updated_at",
                ]
            )

            # Check new flock quantity.
            if new_quantity > new_flock.current_quantity:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "Mortality cannot exceed current flock "
                            f"quantity of {new_flock.current_quantity}."
                        )
                    }
                )

            # Apply new mortality.
            new_flock.current_quantity -= new_quantity

            new_flock.save(
                update_fields=[
                    "current_quantity",
                    "updated_at",
                ]
            )

            return super().update(
                instance,
                validated_data,
            )

    def delete(self, instance):
        """
        Not used directly by DRF.
        Mortality deletion is handled by the view.
        """
        return super().delete(instance)
