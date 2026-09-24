from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models

from common.models import TimeStampedModel
from apps.flocks.models import Flock
from apps.suppliers.models import Supplier


class Feed(TimeStampedModel):
    name = models.CharField(max_length=120)
    feed_type = models.CharField(max_length=80)
    unit = models.CharField(max_length=30, default="kg")

    minimum_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class FeedStock(TimeStampedModel):
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

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.feed.name} - {self.quantity} {self.feed.unit}"


class FeedPurchase(TimeStampedModel):
    feed = models.ForeignKey(
        Feed,
        on_delete=models.PROTECT,
        related_name="purchases",
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feed_purchases",
    )

    date = models.DateField()

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    reference = models.CharField(
        max_length=80,
        blank=True,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feed_purchases_created",
    )

    def __str__(self):
        return f"{self.feed.name} - {self.quantity}"


class FeedConsumption(TimeStampedModel):
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

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feed_consumptions_created",
    )

    def __str__(self):
        return f"{self.feed.name} - {self.quantity} - {self.flock}"
