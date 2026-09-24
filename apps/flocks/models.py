from django.db import models
from common.models import TimeStampedModel

class Flock(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SOLD = "sold", "Sold"
        CLOSED = "closed", "Closed"
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    breed = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=150, blank=True)
    arrival_date = models.DateField()
    initial_quantity = models.PositiveIntegerField(default=0)
    current_quantity = models.PositiveIntegerField(default=0)
    age_weeks = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    house = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    def __str__(self): return f"{self.code} - {self.name}"
