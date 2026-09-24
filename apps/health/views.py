from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import (
    HealthRecord,
    Vaccination,
    Mortality,
)

from .serializers import (
    HealthRecordSerializer,
    VaccinationSerializer,
    MortalitySerializer,
)


class Base(viewsets.ModelViewSet):

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]


# ============================================================
# HEALTH RECORDS
# ============================================================

class HealthRecordViewSet(Base):

    queryset = (
        HealthRecord.objects
        .select_related("flock")
        .all()
        .order_by("-date", "-id")
    )

    serializer_class = HealthRecordSerializer

    filterset_fields = [
        "flock",
        "date",
    ]

    search_fields = [
        "condition",
        "symptoms",
        "treatment",
        "medicine",
        "veterinarian",
        "notes",
        "flock__code",
        "flock__name",
    ]

    ordering_fields = [
        "id",
        "date",
        "condition",
    ]

    ordering = [
        "-date",
        "-id",
    ]


# ============================================================
# VACCINATIONS
# ============================================================

class VaccinationViewSet(Base):

    queryset = (
        Vaccination.objects
        .select_related("flock")
        .all()
        .order_by("-date", "-id")
    )

    serializer_class = VaccinationSerializer

    filterset_fields = [
        "flock",
        "date",
        "next_due_date",
    ]

    search_fields = [
        "vaccine",
        "dosage",
        "administered_by",
        "notes",
        "flock__code",
        "flock__name",
    ]

    ordering_fields = [
        "id",
        "date",
        "vaccine",
        "next_due_date",
    ]

    ordering = [
        "-date",
        "-id",
    ]


# ============================================================
# MORTALITY
# ============================================================

class MortalityViewSet(Base):

    queryset = (
        Mortality.objects
        .select_related("flock")
        .all()
        .order_by("-date", "-id")
    )

    serializer_class = MortalitySerializer

    filterset_fields = [
        "flock",
        "date",
        "cause",
    ]

    search_fields = [
        "cause",
        "notes",
        "flock__code",
        "flock__name",
    ]

    ordering_fields = [
        "id",
        "date",
        "quantity",
        "cause",
    ]

    ordering = [
        "-date",
        "-id",
    ]
