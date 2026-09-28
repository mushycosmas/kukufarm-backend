from django.db import models
from django.core.validators import MinValueValidator

from common.models import TimeStampedModel
from apps.flocks.models import Flock


class EggProduction(TimeStampedModel):

    flock = models.ForeignKey(
        Flock,
        on_delete=models.CASCADE,
        related_name="egg_productions"
    )

    date = models.DateField()

    # Good / sellable eggs collected
    eggs_collected = models.PositiveIntegerField(
        default=0
    )

    # Eggs that were broken during collection
    broken_eggs = models.PositiveIntegerField(
        default=0
    )

    # Eggs that were rejected
    rejected_eggs = models.PositiveIntegerField(
        default=0
    )

    # Automatically calculated:
    # 30 eggs = 1 tray
    # 615 eggs = 20.50 trays
    trays = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ]
    )

    notes = models.TextField(
        blank=True
    )

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.flock} - {self.date} - {self.eggs_collected} eggs"