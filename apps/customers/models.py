from django.db import models
from common.models import TimeStampedModel
class Customer(TimeStampedModel):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=250, blank=True)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name
