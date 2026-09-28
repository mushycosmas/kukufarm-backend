from decimal import Decimal

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import permissions, serializers, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Sale, SalePayment
from .serializers import (
    SaleSerializer,
    SalePaymentSerializer,
)


# ==============================================================
# SALE VIEWSET
# ==============================================================

class SaleViewSet(viewsets.ModelViewSet):

    queryset = (
        Sale.objects
        .select_related("customer")
        .prefetch_related(
            "items",
            "payments",
        )
        .all()
        .order_by(
            "-date",
            "-id",
        )
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


# ==============================================================
# SALE PAYMENT VIEWSET
# ==============================================================

class SalePaymentViewSet(viewsets.ModelViewSet):
    """
    Handles additional payments made against an existing sale.

    IMPORTANT PAYMENT STRUCTURE:

    Sale.amount_paid
        = cumulative amount paid for the sale.

    SalePayment.amount
        = individual additional payment transaction.

    Example:

        Sale total       = 2,500
        Initial payment  = 500

        Sale.amount_paid = 500
        Balance          = 2,000

        Additional payment = 1,000

        Sale.amount_paid = 1,500
        Balance          = 1,000
    """

    queryset = (
        SalePayment.objects
        .select_related(
            "sale",
            "sale__customer",
        )
        .all()
        .order_by(
            "-date",
            "-id",
        )
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

    # ==========================================================
    # HELPER: UPDATE SALE PAYMENT STATUS
    # ==========================================================

    def _update_sale_payment_status(
        self,
        sale,
    ):
        """
        Update payment status based on the cumulative
        amount already paid.

        Sale.amount_paid is treated as the complete
        cumulative amount paid for this sale.
        """

        sale_total = Decimal(
            sale.total or 0
        )

        amount_paid = Decimal(
            sale.amount_paid or 0
        )

        # Prevent negative amount paid.
        if amount_paid < 0:
            amount_paid = Decimal("0")

        # Never allow amount paid to exceed sale total.
        if amount_paid > sale_total:
            amount_paid = sale_total

        sale.amount_paid = amount_paid

        # ------------------------------------------------------
        # PAYMENT STATUS
        # ------------------------------------------------------

        if sale_total <= 0:

            sale.payment_status = (
                Sale.PaymentStatus.PAID
            )

        elif amount_paid <= 0:

            sale.payment_status = (
                Sale.PaymentStatus.UNPAID
            )

        elif amount_paid >= sale_total:

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

        return sale

    # ==========================================================
    # CREATE PAYMENT
    # ==========================================================

    @transaction.atomic
    def perform_create(
        self,
        serializer,
    ):
        """
        Add a new payment to the existing cumulative
        amount_paid.

        Example:

            Existing amount_paid = 500
            New payment           = 1,000

            New amount_paid       = 1,500
        """

        # ------------------------------------------------------
        # LOCK SALE
        # ------------------------------------------------------

        sale_id = serializer.validated_data.get(
            "sale"
        ).id

        sale = (
            Sale.objects
            .select_for_update()
            .get(
                pk=sale_id
            )
        )

        # ------------------------------------------------------
        # PAYMENT AMOUNT
        # ------------------------------------------------------

        payment_amount = Decimal(
            serializer.validated_data.get(
                "amount",
                Decimal("0"),
            )
        )

        if payment_amount <= 0:

            raise serializers.ValidationError({
                "amount": (
                    "Payment amount must be greater "
                    "than zero."
                )
            })

        # ------------------------------------------------------
        # CURRENT CUMULATIVE PAYMENT
        # ------------------------------------------------------

        current_paid = Decimal(
            sale.amount_paid or 0
        )

        sale_total = Decimal(
            sale.total or 0
        )

        # ------------------------------------------------------
        # CURRENT BALANCE
        # ------------------------------------------------------

        current_balance = (
            sale_total
            - current_paid
        )

        if current_balance < 0:

            current_balance = Decimal("0")

        # ------------------------------------------------------
        # PREVENT OVERPAYMENT
        # ------------------------------------------------------

        if payment_amount > current_balance:

            raise serializers.ValidationError({
                "amount": (
                    "Payment amount cannot be greater "
                    f"than the outstanding balance "
                    f"of {current_balance}."
                )
            })

        # ------------------------------------------------------
        # CREATE PAYMENT
        # ------------------------------------------------------

        payment = serializer.save(
            sale=sale
        )

        # ------------------------------------------------------
        # ADD NEW PAYMENT TO CUMULATIVE AMOUNT
        # ------------------------------------------------------

        sale.amount_paid = (
            current_paid
            + payment_amount
        )

        # ------------------------------------------------------
        # UPDATE STATUS
        # ------------------------------------------------------

        self._update_sale_payment_status(
            sale
        )

    # ==========================================================
    # UPDATE PAYMENT
    # ==========================================================

    @transaction.atomic
    def perform_update(
        self,
        serializer,
    ):
        """
        Update an existing payment.

        Example:

            Sale total = 2,500

            Existing:
                Initial payment = 500
                Payment = 1,000

            amount_paid = 1,500

            Change payment from:
                1,000 -> 700

            New amount_paid:
                500 + 700 = 1,200

            New balance:
                2,500 - 1,200 = 1,300
        """

        # ------------------------------------------------------
        # GET EXISTING PAYMENT
        # ------------------------------------------------------

        payment_instance = self.get_object()

        old_amount = Decimal(
            payment_instance.amount or 0
        )

        old_sale_id = (
            payment_instance.sale_id
        )

        # ------------------------------------------------------
        # LOCK SALE
        # ------------------------------------------------------

        sale = (
            Sale.objects
            .select_for_update()
            .get(
                pk=old_sale_id
            )
        )

        # ------------------------------------------------------
        # NEW PAYMENT AMOUNT
        # ------------------------------------------------------

        new_amount = Decimal(
            serializer.validated_data.get(
                "amount",
                old_amount,
            )
        )

        if new_amount <= 0:

            raise serializers.ValidationError({
                "amount": (
                    "Payment amount must be greater "
                    "than zero."
                )
            })

        # ------------------------------------------------------
        # CURRENT CUMULATIVE AMOUNT
        # ------------------------------------------------------

        current_paid = Decimal(
            sale.amount_paid or 0
        )

        sale_total = Decimal(
            sale.total or 0
        )

        # ------------------------------------------------------
        # REMOVE OLD PAYMENT
        # THEN ADD NEW PAYMENT
        # ------------------------------------------------------

        new_total_paid = (
            current_paid
            - old_amount
            + new_amount
        )

        if new_total_paid < 0:

            new_total_paid = Decimal("0")

        # ------------------------------------------------------
        # PREVENT OVERPAYMENT
        # ------------------------------------------------------

        if new_total_paid > sale_total:

            raise serializers.ValidationError({
                "amount": (
                    "Updated payment would exceed "
                    f"the sale total of {sale_total}."
                )
            })

        # ------------------------------------------------------
        # SAVE PAYMENT
        # ------------------------------------------------------

        payment = serializer.save(
            sale=sale
        )

        # ------------------------------------------------------
        # UPDATE SALE CUMULATIVE PAYMENT
        # ------------------------------------------------------

        sale.amount_paid = (
            new_total_paid
        )

        # ------------------------------------------------------
        # UPDATE PAYMENT STATUS
        # ------------------------------------------------------

        self._update_sale_payment_status(
            sale
        )

    # ==========================================================
    # DELETE PAYMENT
    # ==========================================================

    @transaction.atomic
    def perform_destroy(
        self,
        instance,
    ):
        """
        Delete an additional payment and subtract
        it from the cumulative amount_paid.

        Example:

            Sale total = 2,500
            amount_paid = 1,500

            Delete payment = 1,000

            New amount_paid = 500
            New balance = 2,000
        """

        # ------------------------------------------------------
        # LOCK SALE
        # ------------------------------------------------------

        sale = (
            Sale.objects
            .select_for_update()
            .get(
                pk=instance.sale_id
            )
        )

        # ------------------------------------------------------
        # PAYMENT TO REMOVE
        # ------------------------------------------------------

        deleted_amount = Decimal(
            instance.amount or 0
        )

        current_paid = Decimal(
            sale.amount_paid or 0
        )

        # ------------------------------------------------------
        # DELETE PAYMENT
        # ------------------------------------------------------

        instance.delete()

        # ------------------------------------------------------
        # SUBTRACT PAYMENT
        # ------------------------------------------------------

        new_total_paid = (
            current_paid
            - deleted_amount
        )

        if new_total_paid < 0:

            new_total_paid = Decimal("0")

        sale.amount_paid = (
            new_total_paid
        )

        # ------------------------------------------------------
        # UPDATE PAYMENT STATUS
        # ------------------------------------------------------

        self._update_sale_payment_status(
            sale
        )