
from rest_framework import serializers

from .models import (
    Feed,
    FeedPurchase,
    FeedStock,
    FeedConsumption,
)


class FeedSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Feed
        fields = [
            "id",
            "name",
            "feed_type",
            "unit",
            "minimum_stock",
            "unit_cost",
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
        return stock.quantity if stock else 0

    def get_stock_status(self, obj):
        stock = getattr(obj, "stock", None)
        quantity = stock.quantity if stock else 0

        if quantity <= 0:
            return "out_of_stock"

        if quantity <= obj.minimum_stock:
            return "low_stock"

        return "normal"


class FeedPurchaseSerializer(serializers.ModelSerializer):
    feed_name = serializers.CharField(
        source="feed.name",
        read_only=True,
    )

    feed_unit = serializers.CharField(
        source="feed.unit",
        read_only=True,
    )

    supplier_name = serializers.SerializerMethodField()

    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FeedPurchase

        fields = [
            "id",
            "feed",
            "feed_name",
            "feed_unit",
            "supplier",
            "supplier_name",
            "date",
            "quantity",
            "unit_cost",
            "total",
            "reference",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "feed_name",
            "feed_unit",
            "supplier_name",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def get_supplier_name(self, obj):
        if not obj.supplier:
            return "-"

        return str(obj.supplier)

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return "-"

        full_name = obj.created_by.get_full_name()

        return full_name or obj.created_by.username


class FeedConsumptionSerializer(serializers.ModelSerializer):
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


class FeedStockSerializer(serializers.ModelSerializer):
    feed_name = serializers.CharField(
        source="feed.name",
        read_only=True,
    )

    feed_type = serializers.CharField(
        source="feed.feed_type",
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
            "feed_type",
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
            "feed_type",
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
