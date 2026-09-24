from django.core.validators import MinValueValidator
from django.db import models

from common.models import TimeStampedModel


class FarmSettings(TimeStampedModel):
    """
    Global KukuFarm configuration.

    The system is designed to have one settings record
    for the farm.
    """

    class Currency(models.TextChoices):
        TZS = "TZS", "TZS - Tanzanian Shilling"
        USD = "USD", "USD - US Dollar"
        KES = "KES", "KES - Kenyan Shilling"
        UGX = "UGX", "UGX - Ugandan Shilling"

    class DateFormat(models.TextChoices):
        DD_MM_YYYY = "DD/MM/YYYY", "DD/MM/YYYY"
        MM_DD_YYYY = "MM/DD/YYYY", "MM/DD/YYYY"
        YYYY_MM_DD = "YYYY-MM-DD", "YYYY-MM-DD"

    # ---------------------------------------------------------
    # Farm Profile
    # ---------------------------------------------------------

    farm_name = models.CharField(
        max_length=200,
        default="KukuFarm",
    )

    owner_name = models.CharField(
        max_length=200,
        default="",
        blank=True,
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    location = models.CharField(
        max_length=200,
        blank=True,
    )

    address = models.CharField(
        max_length=300,
        blank=True,
    )

    # ---------------------------------------------------------
    # System Preferences
    # ---------------------------------------------------------

    currency = models.CharField(
        max_length=10,
        choices=Currency.choices,
        default=Currency.TZS,
    )

    timezone = models.CharField(
        max_length=100,
        default="Africa/Dar_es_Salaam",
    )

    date_format = models.CharField(
        max_length=20,
        choices=DateFormat.choices,
        default=DateFormat.DD_MM_YYYY,
    )

    # ---------------------------------------------------------
    # Alert Preferences
    # ---------------------------------------------------------

    low_stock_alerts = models.BooleanField(
        default=True,
    )

    mortality_alerts = models.BooleanField(
        default=True,
    )

    vaccination_alerts = models.BooleanField(
        default=True,
    )

    production_alerts = models.BooleanField(
        default=True,
    )

    # ---------------------------------------------------------
    # Notification Preferences
    # ---------------------------------------------------------

    email_notifications = models.BooleanField(
        default=True,
    )

    sms_notifications = models.BooleanField(
        default=False,
    )

    class Meta:
        verbose_name = "Farm Settings"
        verbose_name_plural = "Farm Settings"
        ordering = ["id"]

    def __str__(self):
        return self.farm_name or "KukuFarm Settings"
