from django.db import models
from common.models import TimeStampedModel
class Supplier(TimeStampedModel):
    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=250, blank=True)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name
