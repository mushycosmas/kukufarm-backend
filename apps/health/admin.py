from django.contrib import admin
from .models import HealthRecord, Vaccination, Mortality
admin.site.register([HealthRecord, Vaccination, Mortality])
