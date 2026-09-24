from decimal import Decimal

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import (
    Feed,
    FeedPurchase,
    FeedStock,
    FeedConsumption,
)

from .serializers import (
    FeedSerializer,
    FeedPurchaseSerializer,
    FeedStockSerializer,
    FeedConsumptionSerializer,
)


# ============================================================
# FEED
# ============================================================

class FeedViewSet(viewsets.ModelViewSet):
    """
    Manage feed master records.

    Endpoints:
        GET     /api/feed/feeds/
        POST    /api/feed/feeds/
        GET     /api/feed/feeds/{id}/
        PATCH   /api/feed/feeds/{id}/
        PUT     /api/feed/feeds/{id}/
        DELETE  /api/feed/feeds/{id}/

        GET     /api/feed/feeds/{id}/stock/
    """

    queryset = (
        Feed.objects
        .select_related("stock")
        .all()
        .order_by("name")
    )

    serializer_class = FeedSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "name",
        "feed_type",
        "unit",
    ]

    filterset_fields = [
        "feed_type",
        "unit",
        "active",
    ]

    ordering_fields = [
        "id",
        "name",
        "feed_type",
        "minimum_stock",
        "unit_cost",
    ]

    ordering = [
        "name",
    ]

    def perform_create(self, serializer):
        """
        Create feed and automatically create its stock record.
        """

        feed = serializer.save()

        FeedStock.objects.get_or_create(
            feed=feed,
            defaults={
                "quantity": Decimal("0"),
            },
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="stock",
    )
    def stock(self, request, pk=None):
        """
        Get stock for a specific feed.
        """

        feed = self.get_object()

        stock, _ = FeedStock.objects.get_or_create(
            feed=feed,
            defaults={
                "quantity": Decimal("0"),
            },
        )

        return Response(
            FeedStockSerializer(stock).data
        )


# ============================================================
# FEED PURCHASE
# ============================================================

class FeedPurchaseViewSet(viewsets.ModelViewSet):
    """
    Manage feed purchases.

    Creating a purchase increases feed stock.

    Endpoints:
        GET     /api/feed/purchases/
        POST    /api/feed/purchases/
        GET     /api/feed/purchases/{id}/
        PATCH   /api/feed/purchases/{id}/
        PUT     /api/feed/purchases/{id}/
        DELETE  /api/feed/purchases/{id}/
    """

    queryset = (
        FeedPurchase.objects
        .select_related(
            "feed",
            "supplier",
            "created_by",
        )
        .all()
        .order_by("-date", "-id")
    )

    serializer_class = FeedPurchaseSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_fields = [
        "feed",
        "supplier",
        "date",
    ]

    search_fields = [
        "feed__name",
        "reference",
    ]

    ordering_fields = [
        "id",
        "date",
        "quantity",
        "unit_cost",
        "total",
    ]

    ordering = [
        "-date",
        "-id",
    ]

    def perform_create(self, serializer):
        """
        Create purchase and increase stock.
        """

        with transaction.atomic():

            feed = serializer.validated_data["feed"]

            quantity = serializer.validated_data["quantity"]

            unit_cost = serializer.validated_data["unit_cost"]

            total = quantity * unit_cost

            serializer.save(
                total=total,
                created_by=self.request.user,
            )

            stock, _ = (
                FeedStock.objects
                .select_for_update()
                .get_or_create(
                    feed=feed,
                    defaults={
                        "quantity": Decimal("0"),
                    },
                )
            )

            stock.quantity += quantity

            stock.save()


    def perform_update(self, serializer):
        """
        Update purchase and correctly adjust stock.

        Example:

        Old:
            Layer Mash = 100kg

        Change purchase:
            100kg -> 150kg

        Stock becomes:
            Stock - 100 + 150
        """

        with transaction.atomic():

            old_purchase = self.get_object()

            old_feed = old_purchase.feed

            old_quantity = old_purchase.quantity

            new_feed = serializer.validated_data.get(
                "feed",
                old_feed,
            )

            new_quantity = serializer.validated_data.get(
                "quantity",
                old_quantity,
            )

            new_unit_cost = serializer.validated_data.get(
                "unit_cost",
                old_purchase.unit_cost,
            )

            # ------------------------------------------------
            # OLD FEED STOCK
            # ------------------------------------------------

            old_stock, _ = (
                FeedStock.objects
                .select_for_update()
                .get_or_create(
                    feed=old_feed,
                    defaults={
                        "quantity": Decimal("0"),
                    },
                )
            )

            # Prevent stock from becoming negative.
            if old_stock.quantity < old_quantity:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "Cannot edit this purchase because "
                            "current stock is lower than the "
                            "original purchase quantity."
                        )
                    }
                )

            # Remove old purchase quantity.
            old_stock.quantity -= old_quantity

            old_stock.save()

            # ------------------------------------------------
            # NEW FEED
            # ------------------------------------------------

            if new_feed != old_feed:

                new_stock, _ = (
                    FeedStock.objects
                    .select_for_update()
                    .get_or_create(
                        feed=new_feed,
                        defaults={
                            "quantity": Decimal("0"),
                        },
                    )
                )

                new_stock.quantity += new_quantity

                new_stock.save()

            else:

                old_stock.quantity += new_quantity

                old_stock.save()

            # ------------------------------------------------
            # UPDATE PURCHASE
            # ------------------------------------------------

            total = new_quantity * new_unit_cost

            serializer.save(
                total=total,
            )


    def perform_destroy(self, instance):
        """
        Delete purchase and remove its quantity from stock.
        """

        with transaction.atomic():

            stock, _ = (
                FeedStock.objects
                .select_for_update()
                .get_or_create(
                    feed=instance.feed,
                    defaults={
                        "quantity": Decimal("0"),
                    },
                )
            )

            if stock.quantity < instance.quantity:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "Cannot delete this purchase because "
                            "current stock is lower than the "
                            "purchase quantity."
                        )
                    }
                )

            stock.quantity -= instance.quantity

            stock.save()

            instance.delete()


# ============================================================
# FEED CONSUMPTION
# ============================================================

class FeedConsumptionViewSet(viewsets.ModelViewSet):
    """
    Manage feed consumption.

    Creating consumption decreases feed stock.

    Endpoints:
        GET     /api/feed/consumption/
        POST    /api/feed/consumption/
        GET     /api/feed/consumption/{id}/
        PATCH   /api/feed/consumption/{id}/
        PUT     /api/feed/consumption/{id}/
        DELETE  /api/feed/consumption/{id}/
    """

    queryset = (
        FeedConsumption.objects
        .select_related(
            "feed",
            "flock",
            "created_by",
        )
        .all()
        .order_by("-date", "-id")
    )

    serializer_class = FeedConsumptionSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_fields = [
        "feed",
        "flock",
        "date",
    ]

    search_fields = [
        "feed__name",
        "flock__name",
        "flock__code",
    ]

    ordering_fields = [
        "id",
        "date",
        "quantity",
    ]

    ordering = [
        "-date",
        "-id",
    ]

    def perform_create(self, serializer):
        """
        Create consumption and decrease stock.

        The system prevents consumption when there is
        insufficient feed stock.
        """

        with transaction.atomic():

            feed = serializer.validated_data["feed"]

            quantity = serializer.validated_data["quantity"]

            stock, _ = (
                FeedStock.objects
                .select_for_update()
                .get_or_create(
                    feed=feed,
                    defaults={
                        "quantity": Decimal("0"),
                    },
                )
            )

            # ------------------------------------------------
            # CHECK STOCK
            # ------------------------------------------------

            if stock.quantity < quantity:

                raise serializers.ValidationError(
                    {
                        "quantity": (
                            f"Insufficient stock. "
                            f"Available: {stock.quantity} "
                            f"{feed.unit}."
                        )
                    }
                )

            # ------------------------------------------------
            # CREATE CONSUMPTION
            # ------------------------------------------------

            serializer.save(
                created_by=self.request.user,
            )

            # ------------------------------------------------
            # REDUCE STOCK
            # ------------------------------------------------

            stock.quantity -= quantity

            stock.save()


    def perform_update(self, serializer):
        """
        Update consumption and correctly restore/reduce stock.

        Example:

        Existing:
            Layer Mash consumption = 10kg

        Change to:
            20kg

        The system:

            1. Returns old 10kg
            2. Checks availability for new 20kg
            3. Removes new 20kg
        """

        with transaction.atomic():

            old_consumption = self.get_object()

            old_feed = old_consumption.feed

            old_quantity = old_consumption.quantity

            new_feed = serializer.validated_data.get(
                "feed",
                old_feed,
            )

            new_quantity = serializer.validated_data.get(
                "quantity",
                old_quantity,
            )

            # ------------------------------------------------
            # RESTORE OLD CONSUMPTION
            # ------------------------------------------------

            old_stock, _ = (
                FeedStock.objects
                .select_for_update()
                .get_or_create(
                    feed=old_feed,
                    defaults={
                        "quantity": Decimal("0"),
                    },
                )
            )

            old_stock.quantity += old_quantity

            old_stock.save()

            # ------------------------------------------------
            # GET NEW FEED STOCK
            # ------------------------------------------------

            new_stock, _ = (
                FeedStock.objects
                .select_for_update()
                .get_or_create(
                    feed=new_feed,
                    defaults={
                        "quantity": Decimal("0"),
                    },
                )
            )

            # ------------------------------------------------
            # CHECK NEW STOCK
            # ------------------------------------------------

            if new_stock.quantity < new_quantity:

                raise serializers.ValidationError(
                    {
                        "quantity": (
                            f"Insufficient stock. "
                            f"Available: {new_stock.quantity} "
                            f"{new_feed.unit}."
                        )
                    }
                )

            # ------------------------------------------------
            # REMOVE NEW CONSUMPTION
            # ------------------------------------------------

            new_stock.quantity -= new_quantity

            new_stock.save()

            # ------------------------------------------------
            # UPDATE CONSUMPTION
            # ------------------------------------------------

            serializer.save()


    def perform_destroy(self, instance):
        """
        Delete consumption and return consumed quantity
        back to stock.
        """

        with transaction.atomic():

            stock, _ = (
                FeedStock.objects
                .select_for_update()
                .get_or_create(
                    feed=instance.feed,
                    defaults={
                        "quantity": Decimal("0"),
                    },
                )
            )

            stock.quantity += instance.quantity

            stock.save()

            instance.delete()


# ============================================================
# FEED STOCK
# ============================================================

class FeedStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only feed stock.

    Stock should be changed through purchases and consumption,
    not manually through this endpoint.

    Endpoints:
        GET /api/feed/stock/
        GET /api/feed/stock/{id}/
    """

    queryset = (
        FeedStock.objects
        .select_related("feed")
        .all()
        .order_by("feed__name")
    )

    serializer_class = FeedStockSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_fields = [
        "feed",
    ]

    search_fields = [
        "feed__name",
        "feed__feed_type",
    ]

    ordering_fields = [
        "quantity",
        "last_updated",
    ]

    ordering = [
        "feed__name",
    ]
