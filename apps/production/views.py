from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import EggProduction
from .serializers import EggProductionSerializer


class EggProductionViewSet(viewsets.ModelViewSet):
    queryset = (
        EggProduction.objects
        .select_related("flock")
        .all()
        .order_by("-date", "-id")
    )

    serializer_class = EggProductionSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_fields = [
        "flock",
        "date",
    ]

    search_fields = [
        "flock__code",
        "flock__name",
    ]

    ordering_fields = [
        "id",
        "date",
        "good",
        "broken",
        "dirty",
    ]

    ordering = [
        "-date",
        "-id",
    ]
