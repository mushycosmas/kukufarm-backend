from rest_framework import serializers

from .models import (
    Feed,
    FeedStock,
    FeedStockMovement,
    FeedConsumption,
)


# ============================================================
# FEED
# ============================================================

class FeedSerializer(serializers.ModelSerializer):

    stock_quantity = serializers.SerializerMethodField()

    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Feed

        fields = [
            "id",
            "name",
            "description",
            "unit",
            "minimum_stock",
            "active",
            "stock_quantity",
            "stock_status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "stock_quantity",
            "stock_status",
            "created_at",
            "updated_at",
        ]

    def get_stock_quantity(self, obj):

        stock = getattr(obj, "stock", None)

        if not stock:
            return 0

        return stock.quantity

    def get_stock_status(self, obj):

        stock = getattr(obj, "stock", None)

        quantity = stock.quantity if stock else 0

        if quantity <= 0:
            return "out_of_stock"

        if quantity <= obj.minimum_stock:
            return "low_stock"

        return "normal"


# ============================================================
# FEED STOCK
# ============================================================

class FeedStockSerializer(serializers.ModelSerializer):

    feed_name = serializers.CharField(
        source="feed.name",
        read_only=True,
    )

    unit = serializers.CharField(
        source="feed.unit",
        read_only=True,
    )

    minimum_stock = serializers.DecimalField(
        source="feed.minimum_stock",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = FeedStock

        fields = [
            "id",
            "feed",
            "feed_name",
            "unit",
            "quantity",
            "minimum_stock",
            "stock_status",
            "last_updated",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "feed_name",
            "unit",
            "minimum_stock",
            "stock_status",
            "last_updated",
            "created_at",
            "updated_at",
        ]

    def get_stock_status(self, obj):

        if obj.quantity <= 0:
            return "out_of_stock"

        if obj.quantity <= obj.feed.minimum_stock:
            return "low_stock"

        return "normal"


# ============================================================
# STOCK MOVEMENT
# ============================================================

class FeedStockMovementSerializer(
    serializers.ModelSerializer
):

    feed_name = serializers.CharField(
        source="feed.name",
        read_only=True,
    )

    feed_unit = serializers.CharField(
        source="feed.unit",
        read_only=True,
    )

    flock_name = serializers.CharField(
        source="flock.name",
        read_only=True,
        allow_null=True,
    )

    flock_code = serializers.CharField(
        source="flock.code",
        read_only=True,
        allow_null=True,
    )

    movement_type_display = serializers.CharField(
        source="get_movement_type_display",
        read_only=True,
    )

    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FeedStockMovement

        fields = [
            "id",
            "feed",
            "feed_name",
            "feed_unit",

            "movement_type",
            "movement_type_display",

            "date",
            "quantity",

            "flock",
            "flock_name",
            "flock_code",

            "reference",
            "notes",

            "created_by",
            "created_by_name",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "feed_name",
            "feed_unit",
            "movement_type_display",
            "flock_name",
            "flock_code",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):

        movement_type = attrs.get(
            "movement_type"
        )

        flock = attrs.get(
            "flock"
        )

        if movement_type == "CONSUMPTION" and not flock:
            raise serializers.ValidationError(
                {
                    "flock": (
                        "Flock is required for "
                        "feed consumption."
                    )
                }
            )

        if movement_type != "CONSUMPTION":
            attrs["flock"] = None

        return attrs

    def get_created_by_name(self, obj):

        if not obj.created_by:
            return "-"

        full_name = obj.created_by.get_full_name()

        return full_name or obj.created_by.username


# ============================================================
# FEED CONSUMPTION
# ============================================================

class FeedConsumptionSerializer(
    serializers.ModelSerializer
):

    feed_name = serializers.CharField(
        source="feed.name",
        read_only=True,
    )

    feed_unit = serializers.CharField(
        source="feed.unit",
        read_only=True,
    )

    flock_name = serializers.CharField(
        source="flock.name",
        read_only=True,
    )

    flock_code = serializers.CharField(
        source="flock.code",
        read_only=True,
    )

    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FeedConsumption

        fields = [
            "id",
            "feed",
            "feed_name",
            "feed_unit",
            "flock",
            "flock_name",
            "flock_code",
            "date",
            "quantity",
            "notes",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "feed_name",
            "feed_unit",
            "flock_name",
            "flock_code",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):

        if not obj.created_by:
            return "-"

        full_name = obj.created_by.get_full_name()

        return full_name or obj.created_by.username