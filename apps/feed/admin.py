from django.contrib import admin

from .models import (
    Feed,
    FeedStock,
    FeedStockMovement,
    FeedConsumption,
)


# ============================================================
# FEED
# ============================================================

@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "unit",
        "minimum_stock",
        "active",
        "created_at",
    )

    list_filter = (
        "unit",
        "active",
    )

    search_fields = (
        "name",
        "description",
    )

    ordering = (
        "name",
    )


# ============================================================
# FEED STOCK
# ============================================================

@admin.register(FeedStock)
class FeedStockAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "feed",
        "quantity",
        "last_updated",
    )

    search_fields = (
        "feed__name",
    )

    ordering = (
        "feed__name",
    )


# ============================================================
# FEED STOCK MOVEMENT
# ============================================================

@admin.register(FeedStockMovement)
class FeedStockMovementAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "feed",
        "movement_type",
        "quantity",
        "date",
        "flock",
        "reference",
        "created_by",
        "created_at",
    )

    list_filter = (
        "movement_type",
        "date",
    )

    search_fields = (
        "feed__name",
        "flock__name",
        "flock__code",
        "reference",
        "notes",
    )

    ordering = (
        "-date",
        "-id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


# ============================================================
# FEED CONSUMPTION
# ============================================================

@admin.register(FeedConsumption)
class FeedConsumptionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "feed",
        "flock",
        "quantity",
        "date",
        "created_by",
        "created_at",
    )

    list_filter = (
        "date",
    )

    search_fields = (
        "feed__name",
        "flock__name",
        "flock__code",
        "notes",
    )

    ordering = (
        "-date",
        "-id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )