from django.db import models
from django.core.validators import MinValueValidator

from common.models import TimeStampedModel
from apps.customers.models import Customer


class Sale(TimeStampedModel):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE = "mobile", "Mobile Money"
        BANK = "bank", "Bank"
        CREDIT = "credit", "Credit"

    class PaymentStatus(models.TextChoices):
        PAID = "paid", "Paid"
        PARTIAL = "partial", "Partial"
        UNPAID = "unpaid", "Unpaid"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )

    date = models.DateField()

    invoice_no = models.CharField(
        max_length=40,
        unique=True,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )

    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    discount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    amount_paid = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )

    notes = models.TextField(
        blank=True,
    )

    @property
    def balance(self):
        return max(
            self.total - self.amount_paid,
            0,
        )

    def __str__(self):
        return self.invoice_no


class SaleItem(models.Model):
    class Unit(models.TextChoices):
        PIECE = "piece", "Piece"
        TRAY = "tray", "Tray"

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.CharField(
        max_length=120,
    )

    is_egg = models.BooleanField(
        default=False,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.PIECE,
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    def __str__(self):
        return f"{self.product} - {self.quantity} {self.unit}"
class SalePayment(TimeStampedModel):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    date = models.DateField()

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )

    payment_method = models.CharField(
        max_length=20,
        choices=Sale.PaymentMethod.choices,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )