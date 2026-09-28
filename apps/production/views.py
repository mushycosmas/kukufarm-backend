from decimal import Decimal

from django.db.models import Sum
from rest_framework import permissions, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

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
        permissions.IsAuthenticated
    ]


class EggInventoryView(APIView):
    permission_classes = [
        permissions.IsAuthenticated
    ]

    TRAY_SIZE = Decimal("30")

    def get(self, request):
        production = EggProduction.objects.aggregate(
            total_collected=Sum("eggs_collected"),
            total_broken=Sum("broken_eggs"),
            total_rejected=Sum("rejected_eggs"),
            total_trays=Sum("trays"),
        )

        total_collected = (
            production["total_collected"]
            or Decimal("0")
        )

        total_broken = (
            production["total_broken"]
            or Decimal("0")
        )

        total_rejected = (
            production["total_rejected"]
            or Decimal("0")
        )

        total_trays = (
            production["total_trays"]
            or Decimal("0")
        )

        from apps.sales.models import SaleItem

        egg_items = SaleItem.objects.filter(
            is_egg=True
        )

        total_sold_pieces = Decimal("0")

        for item in egg_items:
            quantity = (
                item.quantity
                or Decimal("0")
            )

            if item.unit == SaleItem.Unit.TRAY:
                quantity *= self.TRAY_SIZE

            total_sold_pieces += quantity

        total_eggs = (
            total_collected
            + total_broken
            + total_rejected
        )

        current_stock = max(
            Decimal("0"),
            total_collected - total_sold_pieces,
        )

        return Response({
            "total_collected": total_collected,
            "total_broken": total_broken,
            "total_rejected": total_rejected,
            "total_eggs": total_eggs,
            "total_trays": total_trays,
            "total_sold": total_sold_pieces,
            "available_eggs": current_stock,
            "current_stock": current_stock,
        })