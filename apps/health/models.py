from django.db import models
from common.models import TimeStampedModel
from apps.flocks.models import Flock

class HealthRecord(TimeStampedModel):
    flock = models.ForeignKey(Flock, on_delete=models.CASCADE, related_name="health_records")
    date = models.DateField()
    condition = models.CharField(max_length=150)
    symptoms = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    medicine = models.CharField(max_length=150, blank=True)
    dosage = models.CharField(max_length=100, blank=True)
    veterinarian = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)

class Vaccination(TimeStampedModel):
    flock = models.ForeignKey(Flock, on_delete=models.CASCADE, related_name="vaccinations")
    vaccine = models.CharField(max_length=150)
    date = models.DateField()
    next_due_date = models.DateField(null=True, blank=True)
    dosage = models.CharField(max_length=100, blank=True)
    administered_by = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)

class Mortality(TimeStampedModel):
    flock = models.ForeignKey(Flock, on_delete=models.CASCADE, related_name="mortalities")
    date = models.DateField()
    quantity = models.PositiveIntegerField()
    cause = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
