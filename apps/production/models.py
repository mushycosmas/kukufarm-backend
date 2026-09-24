from django.db import models
from django.core.validators import MinValueValidator
from common.models import TimeStampedModel
from apps.flocks.models import Flock

class EggProduction(TimeStampedModel):
    flock = models.ForeignKey(Flock, on_delete=models.CASCADE, related_name="egg_productions")
    date = models.DateField()
    eggs_collected = models.PositiveIntegerField(default=0)
    broken_eggs = models.PositiveIntegerField(default=0)
    rejected_eggs = models.PositiveIntegerField(default=0)
    trays = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True)
    class Meta: ordering = ["-date"]
