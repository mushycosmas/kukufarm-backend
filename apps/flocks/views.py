from rest_framework import permissions, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Flock
from .serializers import FlockSerializer


class FlockViewSet(viewsets.ModelViewSet):
    queryset = (
        Flock.objects
        .all()
        .order_by("-id")
    )

    serializer_class = FlockSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "code",
        "name",
        "breed",
        "source",
        "house",
        "notes",
    ]

    filterset_fields = [
        "status",
        "breed",
        "house",
    ]

    ordering_fields = [
        "id",
        "code",
        "name",
        "arrival_date",
        "initial_quantity",
        "current_quantity",
        "age_weeks",
        "status",
    ]

    ordering = [
        "-id"
    ]
