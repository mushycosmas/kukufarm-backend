from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Sale, SalePayment
from .serializers import (
    SaleSerializer,
    SalePaymentSerializer,
)


class SaleViewSet(viewsets.ModelViewSet):
    queryset = (
        Sale.objects
        .select_related("customer")
        .prefetch_related("items", "payments")
        .all()
        .order_by("-date", "-id")
    )

    serializer_class = SaleSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    # ------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------

    search_fields = [
        "invoice_no",
        "customer__name",
        "items__product",
        "notes",
    ]

    # ------------------------------------------------------------
    # FILTERING
    # ------------------------------------------------------------

    filterset_fields = [
        "customer",
        "payment_method",
        "payment_status",
        "date",
        "amount_paid",
    ]

    # ------------------------------------------------------------
    # ORDERING
    # ------------------------------------------------------------

    ordering_fields = [
        "id",
        "date",
        "subtotal",
        "discount",
        "total",
        "amount_paid",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-date",
        "-id",
    ]


class SalePaymentViewSet(viewsets.ModelViewSet):
    """
    Handles individual payments made against sales.

    Example:

    Sale total:       100,000
    Payment 1:         40,000
    Payment 2:         30,000
    Payment 3:         30,000

    Final amount paid: 100,000
    Outstanding:             0
    Status:                PAID
    """

    queryset = (
        SalePayment.objects
        .select_related(
            "sale",
            "sale__customer",
        )
        .all()
        .order_by("-date", "-id")
    )

    serializer_class = SalePaymentSerializer

    permission_classes = [
        permissions.IsAuthenticated
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    # ------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------

    search_fields = [
        "sale__invoice_no",
        "sale__customer__name",
        "reference",
        "notes",
    ]

    # ------------------------------------------------------------
    # FILTERING
    # ------------------------------------------------------------

    filterset_fields = [
        "sale",
        "payment_method",
        "date",
    ]

    # ------------------------------------------------------------
    # ORDERING
    # ------------------------------------------------------------

    ordering_fields = [
        "id",
        "date",
        "amount",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-date",
        "-id",
    ]

    # ------------------------------------------------------------
    # CREATE PAYMENT
    # ------------------------------------------------------------

    @transaction.atomic
    def perform_create(self, serializer):
        payment = serializer.save()

        sale = payment.sale

        # Calculate total amount received
        # from all payments belonging to this sale.
        total_paid = (
            SalePayment.objects
            .filter(
                sale=sale
            )
            .aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0")
        )

        sale_total = Decimal(
            sale.total or 0
        )

        # Never allow amount paid to exceed
        # the sale total.
        total_paid = min(
            total_paid,
            sale_total,
        )

        sale.amount_paid = total_paid

        # Update payment status.
        if sale_total <= 0:
            sale.payment_status = (
                Sale.PaymentStatus.PAID
            )

        elif total_paid <= 0:
            sale.payment_status = (
                Sale.PaymentStatus.UNPAID
            )

        elif total_paid >= sale_total:
            sale.payment_status = (
                Sale.PaymentStatus.PAID
            )

        else:
            sale.payment_status = (
                Sale.PaymentStatus.PARTIAL
            )

        sale.save(
            update_fields=[
                "amount_paid",
                "payment_status",
                "updated_at",
            ]
        )

    # ------------------------------------------------------------
    # UPDATE PAYMENT
    # ------------------------------------------------------------

    @transaction.atomic
    def perform_update(self, serializer):
        payment = serializer.save()

        sale = payment.sale

        # Recalculate all payments after
        # editing an existing payment.
        total_paid = (
            SalePayment.objects
            .filter(
                sale=sale
            )
            .aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0")
        )

        sale_total = Decimal(
            sale.total or 0
        )

        total_paid = min(
            total_paid,
            sale_total,
        )

        sale.amount_paid = total_paid

        if sale_total <= 0:
            sale.payment_status = (
                Sale.PaymentStatus.PAID
            )

        elif total_paid <= 0:
            sale.payment_status = (
                Sale.PaymentStatus.UNPAID
            )

        elif total_paid >= sale_total:
            sale.payment_status = (
                Sale.PaymentStatus.PAID
            )

        else:
            sale.payment_status = (
                Sale.PaymentStatus.PARTIAL
            )

        sale.save(
            update_fields=[
                "amount_paid",
                "payment_status",
                "updated_at",
            ]
        )

    # ------------------------------------------------------------
    # DELETE PAYMENT
    # ------------------------------------------------------------

    @transaction.atomic
    def perform_destroy(self, instance):
        sale = instance.sale

        instance.delete()

        # Recalculate remaining payments.
        total_paid = (
            SalePayment.objects
            .filter(
                sale=sale
            )
            .aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0")
        )

        sale_total = Decimal(
            sale.total or 0
        )

        total_paid = min(
            total_paid,
            sale_total,
        )

        sale.amount_paid = total_paid

        if sale_total <= 0:
            sale.payment_status = (
                Sale.PaymentStatus.PAID
            )

        elif total_paid <= 0:
            sale.payment_status = (
                Sale.PaymentStatus.UNPAID
            )

        elif total_paid >= sale_total:
            sale.payment_status = (
                Sale.PaymentStatus.PAID
            )

        else:
            sale.payment_status = (
                Sale.PaymentStatus.PARTIAL
            )

        sale.save(
            update_fields=[
                "amount_paid",
                "payment_status",
                "updated_at",
            ]
        )