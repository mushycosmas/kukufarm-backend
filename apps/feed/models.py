from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models

from common.models import TimeStampedModel
from apps.flocks.models import Flock


# ============================================================
# FEED TYPE / MASTER
# ============================================================

class Feed(TimeStampedModel):
    """
    Feed master record.

    This only defines the type of feed.

    Financial information such as purchase price,
    supplier and purchase cost belongs to Expenses/Purchases.
    """

    name = models.CharField(
        max_length=120,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    unit = models.CharField(
        max_length=30,
        default="kg",
    )

    minimum_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name


# ============================================================
# CURRENT FEED STOCK
# ============================================================

class FeedStock(TimeStampedModel):
    """
    Stores the current physical quantity of each feed.

    Example:

        Broiler Starter = 450 kg
        Layer Mash      = 820 kg
    """

    feed = models.OneToOneField(
        Feed,
        on_delete=models.CASCADE,
        related_name="stock",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    last_updated = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.feed.name} - {self.quantity} {self.feed.unit}"


# ============================================================
# FEED STOCK MOVEMENT
# ============================================================

class FeedStockMovement(TimeStampedModel):
    """
    Records physical feed stock movements.

    Movement types:

        STOCK_IN
        OPENING_STOCK
        ADJUSTMENT
        CONSUMPTION

    Financial purchase information does NOT belong here.
    """

    MOVEMENT_TYPES = [
        ("STOCK_IN", "Stock In"),
        ("OPENING_STOCK", "Opening Stock"),
        ("ADJUSTMENT", "Adjustment"),
        ("CONSUMPTION", "Consumption"),
    ]

    feed = models.ForeignKey(
        Feed,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )

    movement_type = models.CharField(
        max_length=30,
        choices=MOVEMENT_TYPES,
    )

    date = models.DateField()

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    flock = models.ForeignKey(
        Flock,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="feed_stock_movements",
    )

    reference = models.CharField(
        max_length=80,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feed_stock_movements_created",
    )

    def __str__(self):
        return (
            f"{self.feed.name} - "
            f"{self.movement_type} - "
            f"{self.quantity}"
        )


# ============================================================
# FEED CONSUMPTION
# ============================================================

class FeedConsumption(TimeStampedModel):
    """
    Records feed consumed by a flock.

    Consumption automatically decreases FeedStock.
    """

    feed = models.ForeignKey(
        Feed,
        on_delete=models.PROTECT,
        related_name="consumptions",
    )

    flock = models.ForeignKey(
        Flock,
        on_delete=models.PROTECT,
        related_name="feed_consumptions",
    )

    date = models.DateField()

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feed_consumptions_created",
    )

    def __str__(self):
        return (
            f"{self.feed.name} - "
            f"{self.quantity} - "
            f"{self.flock}"
        )