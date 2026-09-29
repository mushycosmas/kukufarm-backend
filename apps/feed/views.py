from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import permissions, serializers, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import (
    Feed,
    FeedStock,
    FeedStockMovement,
    FeedConsumption,
)

from .serializers import (
    FeedSerializer,
    FeedStockSerializer,
    FeedStockMovementSerializer,
    FeedConsumptionSerializer,
)


# ============================================================
# FEED
# ============================================================

class FeedViewSet(viewsets.ModelViewSet):

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
        "description",
        "unit",
    ]

    filterset_fields = [
        "unit",
        "active",
    ]

    ordering_fields = [
        "id",
        "name",
        "minimum_stock",
    ]

    ordering = [
        "name",
    ]

    def perform_create(self, serializer):

        with transaction.atomic():

            feed = serializer.save()

            FeedStock.objects.get_or_create(
                feed=feed,
                defaults={
                    "quantity": Decimal("0"),
                },
            )


# ============================================================
# FEED STOCK
# ============================================================

class FeedStockViewSet(viewsets.ModelViewSet):

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
    ]

    ordering_fields = [
        "quantity",
        "last_updated",
    ]

    ordering = [
        "feed__name",
    ]

    # --------------------------------------------------------
    # ADD STOCK
    # POST /api/feed/stock/
    # --------------------------------------------------------

    def create(self, request, *args, **kwargs):

        with transaction.atomic():

            feed_id = request.data.get("feed")
            quantity = request.data.get("quantity")

            # ------------------------------------------------
            # VALIDATE FEED
            # ------------------------------------------------

            if not feed_id:

                raise serializers.ValidationError({
                    "feed": "Feed is required."
                })

            try:

                feed = Feed.objects.get(
                    pk=feed_id
                )

            except Feed.DoesNotExist:

                raise serializers.ValidationError({
                    "feed": "Selected feed does not exist."
                })

            # ------------------------------------------------
            # VALIDATE QUANTITY
            # ------------------------------------------------

            if quantity in [None, ""]:

                raise serializers.ValidationError({
                    "quantity": "Quantity is required."
                })

            try:

                quantity = Decimal(
                    str(quantity)
                )

            except Exception:

                raise serializers.ValidationError({
                    "quantity": "Enter a valid quantity."
                })

            if quantity <= 0:

                raise serializers.ValidationError({
                    "quantity": (
                        "Quantity must be greater than zero."
                    )
                })

            # ------------------------------------------------
            # GET / CREATE STOCK
            # ------------------------------------------------

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
            # ADD STOCK
            # ------------------------------------------------

            stock.quantity += quantity

            stock.save()

            # ------------------------------------------------
            # CREATE MOVEMENT
            # ------------------------------------------------

            movement_date = request.data.get("date")

            if not movement_date:
                movement_date = timezone.now().date()

            FeedStockMovement.objects.create(
                feed=feed,
                movement_type="STOCK_IN",
                date=movement_date,
                quantity=quantity,
                reference=request.data.get(
                    "reference",
                    "",
                ),
                notes=request.data.get(
                    "notes",
                    "",
                ),
                created_by=request.user,
            )

            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            serializer = self.get_serializer(
                stock
            )

            return Response(
                serializer.data,
                status=201,
            )

    # --------------------------------------------------------
    # UPDATE STOCK
    # --------------------------------------------------------

    def update(
        self,
        request,
        *args,
        **kwargs
    ):

        with transaction.atomic():

            stock = (
                FeedStock.objects
                .select_for_update()
                .select_related("feed")
                .get(
                    pk=kwargs.get("pk")
                )
            )

            quantity = request.data.get(
                "quantity"
            )

            if quantity in [None, ""]:

                raise serializers.ValidationError({
                    "quantity": "Quantity is required."
                })

            try:

                new_quantity = Decimal(
                    str(quantity)
                )

            except Exception:

                raise serializers.ValidationError({
                    "quantity": (
                        "Enter a valid quantity."
                    )
                })

            if new_quantity < 0:

                raise serializers.ValidationError({
                    "quantity": (
                        "Quantity cannot be negative."
                    )
                })

            old_quantity = stock.quantity

            # Nothing changed
            if new_quantity == old_quantity:

                serializer = self.get_serializer(
                    stock
                )

                return Response(
                    serializer.data
                )

            difference = (
                new_quantity -
                old_quantity
            )

            # ------------------------------------------------
            # STOCK IN
            # ------------------------------------------------

            if difference > 0:

                FeedStockMovement.objects.create(
                    feed=stock.feed,
                    movement_type="STOCK_IN",
                    date=request.data.get(
                        "date"
                    ) or timezone.now().date(),
                    quantity=difference,
                    reference=request.data.get(
                        "reference",
                        "",
                    ),
                    notes=request.data.get(
                        "notes",
                        "Stock quantity increased.",
                    ),
                    created_by=request.user,
                )

            # ------------------------------------------------
            # STOCK ADJUSTMENT
            # ------------------------------------------------

            else:

                adjustment_quantity = abs(
                    difference
                )

                FeedStockMovement.objects.create(
                    feed=stock.feed,
                    movement_type="ADJUSTMENT",
                    date=request.data.get(
                        "date"
                    ) or timezone.now().date(),
                    quantity=adjustment_quantity,
                    reference=request.data.get(
                        "reference",
                        "",
                    ),
                    notes=request.data.get(
                        "notes",
                        "Stock quantity adjusted downward.",
                    ),
                    created_by=request.user,
                )

            stock.quantity = new_quantity

            stock.save()

            serializer = self.get_serializer(
                stock
            )

            return Response(
                serializer.data
            )

    # --------------------------------------------------------
    # PATCH
    # --------------------------------------------------------

    def partial_update(
        self,
        request,
        *args,
        **kwargs
    ):

        return self.update(
            request,
            *args,
            **kwargs
        )

    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    def perform_destroy(self, instance):

        with transaction.atomic():

            stock = (
                FeedStock.objects
                .select_for_update()
                .get(
                    pk=instance.pk
                )
            )

            if stock.quantity != 0:

                raise serializers.ValidationError({
                    "quantity": (
                        "Stock record cannot be deleted "
                        "while quantity is greater than zero."
                    )
                })

            stock.delete()


# ============================================================
# FEED STOCK MOVEMENTS
# ============================================================

class FeedStockMovementViewSet(
    viewsets.ModelViewSet
):

    queryset = (
        FeedStockMovement.objects
        .select_related(
            "feed",
            "flock",
            "created_by",
        )
        .all()
        .order_by(
            "-date",
            "-id",
        )
    )

    serializer_class = FeedStockMovementSerializer

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
        "movement_type",
        "flock",
        "date",
    ]

    search_fields = [
        "feed__name",
        "reference",
        "notes",
        "flock__name",
        "flock__code",
    ]

    ordering_fields = [
        "id",
        "date",
        "quantity",
        "movement_type",
    ]

    ordering = [
        "-date",
        "-id",
    ]

    # --------------------------------------------------------
    # CREATE MOVEMENT
    # --------------------------------------------------------

    def perform_create(self, serializer):

        with transaction.atomic():

            feed = serializer.validated_data[
                "feed"
            ]

            movement_type = serializer.validated_data[
                "movement_type"
            ]

            quantity = serializer.validated_data[
                "quantity"
            ]

            if quantity <= 0:

                raise serializers.ValidationError({
                    "quantity": (
                        "Quantity must be greater than zero."
                    )
                })

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
            # CONSUMPTION
            # ------------------------------------------------

            if movement_type == "CONSUMPTION":

                if stock.quantity < quantity:

                    raise serializers.ValidationError({
                        "quantity": (
                            f"Insufficient stock. "
                            f"Available: "
                            f"{stock.quantity} "
                            f"{feed.unit}."
                        )
                    })

                stock.quantity -= quantity

            # ------------------------------------------------
            # STOCK ADDITIONS
            # ------------------------------------------------

            elif movement_type in [
                "STOCK_IN",
                "OPENING_STOCK",
            ]:

                stock.quantity += quantity

            # ------------------------------------------------
            # ADJUSTMENT
            # ------------------------------------------------

            elif movement_type == "ADJUSTMENT":

                stock.quantity += quantity

            else:

                raise serializers.ValidationError({
                    "movement_type": (
                        "Invalid stock movement type."
                    )
                })

            stock.save()

            serializer.save(
                created_by=self.request.user
            )

    # --------------------------------------------------------
    # UPDATE MOVEMENT
    # --------------------------------------------------------

    def perform_update(self, serializer):

        with transaction.atomic():

            old_movement = self.get_object()

            old_feed = old_movement.feed
            old_type = old_movement.movement_type
            old_quantity = old_movement.quantity

            new_feed = serializer.validated_data.get(
                "feed",
                old_feed,
            )

            new_type = serializer.validated_data.get(
                "movement_type",
                old_type,
            )

            new_quantity = serializer.validated_data.get(
                "quantity",
                old_quantity,
            )

            if new_quantity <= 0:

                raise serializers.ValidationError({
                    "quantity": (
                        "Quantity must be greater than zero."
                    )
                })

            # =================================================
            # RESTORE OLD MOVEMENT
            # =================================================

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

            if old_type == "CONSUMPTION":

                old_stock.quantity += old_quantity

            else:

                if old_stock.quantity < old_quantity:

                    raise serializers.ValidationError({
                        "quantity": (
                            "Cannot update this movement "
                            "because current stock is lower "
                            "than the original movement."
                        )
                    })

                old_stock.quantity -= old_quantity

            old_stock.save()

            # =================================================
            # APPLY NEW MOVEMENT
            # =================================================

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

            if new_type == "CONSUMPTION":

                if new_stock.quantity < new_quantity:

                    raise serializers.ValidationError({
                        "quantity": (
                            f"Insufficient stock. "
                            f"Available: "
                            f"{new_stock.quantity} "
                            f"{new_feed.unit}."
                        )
                    })

                new_stock.quantity -= new_quantity

            elif new_type in [
                "STOCK_IN",
                "OPENING_STOCK",
                "ADJUSTMENT",
            ]:

                new_stock.quantity += new_quantity

            else:

                raise serializers.ValidationError({
                    "movement_type": (
                        "Invalid stock movement type."
                    )
                })

            new_stock.save()

            serializer.save()

    # --------------------------------------------------------
    # DELETE MOVEMENT
    # --------------------------------------------------------

    def perform_destroy(self, instance):

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

            if instance.movement_type == "CONSUMPTION":

                stock.quantity += instance.quantity

            else:

                if stock.quantity < instance.quantity:

                    raise serializers.ValidationError({
                        "quantity": (
                            "Cannot delete this movement "
                            "because current stock is lower "
                            "than the movement quantity."
                        )
                    })

                stock.quantity -= instance.quantity

            stock.save()

            instance.delete()


# ============================================================
# FEED CONSUMPTION
# ============================================================

class FeedConsumptionViewSet(
    viewsets.ModelViewSet
):

    queryset = (
        FeedConsumption.objects
        .select_related(
            "feed",
            "flock",
            "created_by",
        )
        .all()
        .order_by(
            "-date",
            "-id",
        )
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

    # --------------------------------------------------------
    # CREATE CONSUMPTION
    # --------------------------------------------------------

    def perform_create(self, serializer):

        with transaction.atomic():

            feed = serializer.validated_data[
                "feed"
            ]

            quantity = serializer.validated_data[
                "quantity"
            ]

            if quantity <= 0:

                raise serializers.ValidationError({
                    "quantity": (
                        "Quantity must be greater than zero."
                    )
                })

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

                raise serializers.ValidationError({
                    "quantity": (
                        f"Insufficient stock. "
                        f"Available: "
                        f"{stock.quantity} "
                        f"{feed.unit}."
                    )
                })

            # ------------------------------------------------
            # SAVE CONSUMPTION
            # ------------------------------------------------

            serializer.save(
                created_by=self.request.user
            )

            # ------------------------------------------------
            # REDUCE STOCK
            # ------------------------------------------------

            stock.quantity -= quantity

            stock.save()

    # --------------------------------------------------------
    # UPDATE CONSUMPTION
    # --------------------------------------------------------

    def perform_update(self, serializer):

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

            if new_quantity <= 0:

                raise serializers.ValidationError({
                    "quantity": (
                        "Quantity must be greater than zero."
                    )
                })

            # =================================================
            # RESTORE OLD CONSUMPTION
            # =================================================

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

            # =================================================
            # APPLY NEW CONSUMPTION
            # =================================================

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

            if new_stock.quantity < new_quantity:

                raise serializers.ValidationError({
                    "quantity": (
                        f"Insufficient stock. "
                        f"Available: "
                        f"{new_stock.quantity} "
                        f"{new_feed.unit}."
                    )
                })

            new_stock.quantity -= new_quantity

            new_stock.save()

            serializer.save()

    # --------------------------------------------------------
    # DELETE CONSUMPTION
    # --------------------------------------------------------

    def perform_destroy(self, instance):

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

            # Restore consumed stock
            stock.quantity += instance.quantity

            stock.save()

            instance.delete()