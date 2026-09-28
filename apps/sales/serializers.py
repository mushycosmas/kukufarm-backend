from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from rest_framework import serializers

from .models import (
    Sale,
    SaleItem,
    SalePayment,
)


class SaleItemSerializer(serializers.ModelSerializer):
    """
    Serializer for individual sale items.
    """

    class Meta:
        model = SaleItem

        fields = [
            "id",
            "product",
            "is_egg",
            "quantity",
            "unit",
            "unit_price",
            "total",
        ]

        read_only_fields = [
            "id",
            "total",
        ]

    def validate(self, attrs):
        quantity = Decimal(
            attrs.get(
                "quantity",
                Decimal("0"),
            )
        )

        unit_price = Decimal(
            attrs.get(
                "unit_price",
                Decimal("0"),
            )
        )

        if quantity < 0:
            raise serializers.ValidationError({
                "quantity": "Quantity cannot be negative."
            })

        if unit_price < 0:
            raise serializers.ValidationError({
                "unit_price": "Unit price cannot be negative."
            })

        return attrs


# ==============================================================
# SALE SERIALIZER
# ==============================================================

class SaleSerializer(serializers.ModelSerializer):
    """
    Serializer for sales.

    Responsibilities:
    - Create/update sales
    - Automatically generate invoice numbers
    - Calculate subtotal
    - Calculate total
    - Calculate balance
    - Calculate payment status
    - Validate egg stock
    - Validate initial payment
    """

    items = SaleItemSerializer(
        many=True,
        required=False,
    )

    balance = serializers.SerializerMethodField()

    class Meta:
        model = Sale

        fields = [
            "id",
            "customer",
            "date",
            "invoice_no",
            "payment_method",
            "subtotal",
            "discount",
            "total",
            "amount_paid",
            "balance",
            "payment_status",
            "notes",
            "items",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "invoice_no",
            "subtotal",
            "total",
            "balance",
            "payment_status",
            "created_at",
            "updated_at",
        ]

    # ==========================================================
    # BALANCE
    # ==========================================================

    def get_balance(self, obj):
        """
        Return the outstanding balance.
        """

        total = Decimal(
            obj.total or 0
        )

        amount_paid = Decimal(
            obj.amount_paid or 0
        )

        return max(
            total - amount_paid,
            Decimal("0"),
        )

    # ==========================================================
    # GENERATE INVOICE NUMBER
    # ==========================================================

    def _generate_invoice_number(self):
        """
        Generate invoice numbers in the format:

        INV-000001
        INV-000002
        INV-000003
        """

        highest = 0

        sales = (
            Sale.objects
            .select_for_update()
            .only("invoice_no")
        )

        for sale in sales:
            invoice = str(
                sale.invoice_no or ""
            )

            if not invoice.startswith("INV-"):
                continue

            try:
                number = int(
                    invoice.replace(
                        "INV-",
                        "",
                        1,
                    )
                )

                if number > highest:
                    highest = number

            except ValueError:
                continue

        return f"INV-{highest + 1:06d}"

    # ==========================================================
    # CALCULATE PAYMENT STATUS
    # ==========================================================

    def _calculate_payment_status(self, sale):
        """
        Determine payment status from:

        total
        amount_paid
        """

        total = Decimal(
            sale.total or 0
        )

        amount_paid = Decimal(
            sale.amount_paid or 0
        )

        if total <= 0:
            return Sale.PaymentStatus.PAID

        if amount_paid <= 0:
            return Sale.PaymentStatus.UNPAID

        if amount_paid >= total:
            return Sale.PaymentStatus.PAID

        return Sale.PaymentStatus.PARTIAL

    # ==========================================================
    # CALCULATE SALE TOTALS
    # ==========================================================

    def _calculate(self, sale, items):
        """
        Calculate:

        subtotal
        total
        payment_status
        """

        subtotal = sum(
            (
                Decimal(item["quantity"])
                * Decimal(item["unit_price"])
                for item in items
            ),
            start=Decimal("0"),
        )

        discount = Decimal(
            sale.discount or 0
        )

        sale.subtotal = subtotal

        sale.total = max(
            Decimal("0"),
            subtotal - discount,
        )

        sale.payment_status = (
            self._calculate_payment_status(
                sale
            )
        )

        sale.save(
            update_fields=[
                "subtotal",
                "total",
                "payment_status",
                "updated_at",
            ]
        )

    # ==========================================================
    # CONVERT EGG QUANTITY TO INDIVIDUAL EGGS
    # ==========================================================

    def _egg_quantity_in_eggs(self, item):
        """
        Convert an egg sale item into individual eggs.

        1 tray = 30 eggs.
        """

        if not item.get("is_egg"):
            return Decimal("0")

        quantity = Decimal(
            item.get("quantity") or 0
        )

        unit = item.get(
            "unit",
            SaleItem.Unit.PIECE,
        )

        if unit == SaleItem.Unit.TRAY:
            return quantity * Decimal("30")

        return quantity

    # ==========================================================
    # GET AVAILABLE EGG STOCK
    # ==========================================================

    def _get_available_eggs(self):
        """
        Available egg stock is:

        Total eggs collected
        -
        Total eggs already sold
        """

        from apps.production.models import EggProduction

        total_collected = (
            EggProduction.objects
            .aggregate(
                total=Sum("eggs_collected")
            )["total"]
            or Decimal("0")
        )

        total_sold = Decimal("0")

        sales = (
            Sale.objects
            .prefetch_related("items")
            .all()
        )

        for sale in sales:
            for item in sale.items.all():
                total_sold += (
                    self._egg_quantity_in_eggs(
                        {
                            "is_egg": item.is_egg,
                            "quantity": item.quantity,
                            "unit": item.unit,
                        }
                    )
                )

        return max(
            total_collected - total_sold,
            Decimal("0"),
        )

    # ==========================================================
    # VALIDATE EGG STOCK
    # ==========================================================

    def _validate_egg_stock(
        self,
        items,
        current_sale=None,
    ):
        """
        Validate that enough eggs are available.

        When editing an existing sale, the eggs
        from the current sale are returned to
        stock before validating the new quantity.
        """

        requested_eggs = Decimal("0")

        for item in items:
            requested_eggs += (
                self._egg_quantity_in_eggs(
                    item
                )
            )

        if requested_eggs <= 0:
            return

        available_eggs = (
            self._get_available_eggs()
        )

        # Return the current sale's eggs to
        # available stock while editing.
        if current_sale:
            for old_item in (
                current_sale.items.all()
            ):
                available_eggs += (
                    self._egg_quantity_in_eggs(
                        {
                            "is_egg": old_item.is_egg,
                            "quantity": old_item.quantity,
                            "unit": old_item.unit,
                        }
                    )
                )

        if requested_eggs > available_eggs:
            raise serializers.ValidationError({
                "items": (
                    "Insufficient egg stock. "
                    f"Available: {available_eggs} eggs. "
                    f"Requested: {requested_eggs} eggs."
                )
            })

    # ==========================================================
    # VALIDATE PAYMENT
    # ==========================================================

    def _validate_payment(
        self,
        amount_paid,
        total,
    ):
        """
        Validate initial payment amount.

        The payment cannot:
        - be negative
        - exceed the sale total
        """

        amount_paid = Decimal(
            amount_paid or 0
        )

        total = Decimal(
            total or 0
        )

        if amount_paid < 0:
            raise serializers.ValidationError({
                "amount_paid": (
                    "Amount paid cannot be negative."
                )
            })

        if amount_paid > total:
            raise serializers.ValidationError({
                "amount_paid": (
                    "Amount paid cannot be greater "
                    "than the sale total."
                )
            })

        return amount_paid

    # ==========================================================
    # CREATE SALE
    # ==========================================================

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a new sale.

        Invoice number is generated automatically.
        """

        items = validated_data.pop(
            "items",
            [],
        )

        amount_paid = validated_data.pop(
            "amount_paid",
            Decimal("0"),
        )

        amount_paid = Decimal(
            amount_paid or 0
        )

        # ------------------------------------------------------
        # CREATE TEMPORARY SALE DATA FOR PAYMENT VALIDATION
        # ------------------------------------------------------

        # Validate egg stock before creating anything.
        self._validate_egg_stock(
            items
        )

        # ------------------------------------------------------
        # GENERATE INVOICE
        # ------------------------------------------------------

        invoice_no = (
            self._generate_invoice_number()
        )

        # ------------------------------------------------------
        # CREATE SALE
        # ------------------------------------------------------

        sale = Sale.objects.create(
            invoice_no=invoice_no,
            amount_paid=amount_paid,
            **validated_data,
        )

        # ------------------------------------------------------
        # CREATE SALE ITEMS
        # ------------------------------------------------------

        for item in items:
            quantity = Decimal(
                item["quantity"]
            )

            unit_price = Decimal(
                item["unit_price"]
            )

            SaleItem.objects.create(
                sale=sale,
                total=quantity * unit_price,
                **item,
            )

        # ------------------------------------------------------
        # CALCULATE TOTALS
        # ------------------------------------------------------

        self._calculate(
            sale,
            items,
        )

        # ------------------------------------------------------
        # VALIDATE INITIAL PAYMENT
        # ------------------------------------------------------

        self._validate_payment(
            sale.amount_paid,
            sale.total,
        )

        # ------------------------------------------------------
        # UPDATE PAYMENT STATUS
        # ------------------------------------------------------

        sale.payment_status = (
            self._calculate_payment_status(
                sale
            )
        )

        sale.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )

        return sale

    # ==========================================================
    # UPDATE SALE
    # ==========================================================

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):
        """
        Update an existing sale.

        Invoice number cannot be changed.
        """

        items = validated_data.pop(
            "items",
            None,
        )

        # ------------------------------------------------------
        # PROTECT INVOICE NUMBER
        # ------------------------------------------------------

        validated_data.pop(
            "invoice_no",
            None,
        )

        # ------------------------------------------------------
        # UPDATE NORMAL FIELDS
        # ------------------------------------------------------

        for key, value in (
            validated_data.items()
        ):
            setattr(
                instance,
                key,
                value,
            )

        instance.save()

        # ------------------------------------------------------
        # UPDATE SALE ITEMS
        # ------------------------------------------------------

        if items is not None:
            # Validate egg stock before deleting
            # existing items.
            self._validate_egg_stock(
                items,
                current_sale=instance,
            )

            # Remove old items.
            instance.items.all().delete()

            # Create new items.
            for item in items:
                quantity = Decimal(
                    item["quantity"]
                )

                unit_price = Decimal(
                    item["unit_price"]
                )

                SaleItem.objects.create(
                    sale=instance,
                    total=quantity * unit_price,
                    **item,
                )

            # Recalculate totals.
            self._calculate(
                instance,
                items,
            )

        else:
            # --------------------------------------------------
            # ITEMS NOT CHANGED
            # --------------------------------------------------

            instance.total = max(
                Decimal("0"),
                Decimal(instance.subtotal or 0)
                - Decimal(instance.discount or 0),
            )

            instance.payment_status = (
                self._calculate_payment_status(
                    instance
                )
            )

            instance.save(
                update_fields=[
                    "total",
                    "payment_status",
                    "updated_at",
                ]
            )

        # ------------------------------------------------------
        # VALIDATE PAYMENT
        # ------------------------------------------------------

        self._validate_payment(
            instance.amount_paid,
            instance.total,
        )

        # ------------------------------------------------------
        # FINAL PAYMENT STATUS
        # ------------------------------------------------------

        instance.payment_status = (
            self._calculate_payment_status(
                instance
            )
        )

        instance.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )

        return instance


# ==============================================================
# SALE PAYMENT SERIALIZER
# ==============================================================

class SalePaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for additional payments made against
    an existing sale.

    Example:

    Sale:
        INV-000001
        Total: 100,000
        Already Paid: 40,000
        Balance: 60,000

    New SalePayment:
        Amount: 20,000

    New Sale:
        Total: 100,000
        Amount Paid: 60,000
        Balance: 40,000
    """

    invoice_no = serializers.CharField(
        source="sale.invoice_no",
        read_only=True,
    )

    customer_name = serializers.CharField(
        source="sale.customer.name",
        read_only=True,
    )

    class Meta:
        model = SalePayment

        fields = [
            "id",
            "sale",
            "invoice_no",
            "customer_name",
            "date",
            "amount",
            "payment_method",
            "reference",
            "notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "invoice_no",
            "customer_name",
            "created_at",
            "updated_at",
        ]

    # ==========================================================
    # VALIDATE PAYMENT
    # ==========================================================

    def validate(self, attrs):
        """
        Validate an additional payment against
        the sale's outstanding balance.
        """

        # ------------------------------------------------------
        # GET SALE
        # ------------------------------------------------------

        sale = attrs.get(
            "sale"
        )

        # When updating an existing payment,
        # sale may not be supplied in the request.
        if sale is None and self.instance:
            sale = self.instance.sale

        if sale is None:
            raise serializers.ValidationError({
                "sale": (
                    "A sale is required for this payment."
                )
            })

        # ------------------------------------------------------
        # GET PAYMENT AMOUNT
        # ------------------------------------------------------

        amount = attrs.get(
            "amount",
            self.instance.amount
            if self.instance
            else Decimal("0"),
        )

        amount = Decimal(
            amount or 0
        )

        # ------------------------------------------------------
        # PAYMENT MUST BE POSITIVE
        # ------------------------------------------------------

        if amount <= 0:
            raise serializers.ValidationError({
                "amount": (
                    "Payment amount must be greater than zero."
                )
            })

        # ------------------------------------------------------
        # GET PREVIOUS PAYMENTS
        # ------------------------------------------------------

        previous_payments = (
            SalePayment.objects
            .filter(
                sale=sale
            )
            .aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0")
        )

        # When editing an existing payment,
        # remove its old amount from the
        # calculation.
        if self.instance:
            previous_payments -= (
                Decimal(
                    self.instance.amount or 0
                )
            )

        # ------------------------------------------------------
        # CALCULATE OUTSTANDING BALANCE
        # ------------------------------------------------------

        sale_total = Decimal(
            sale.total or 0
        )

        outstanding = (
            sale_total
            - previous_payments
        )

        if outstanding < 0:
            outstanding = Decimal("0")

        # ------------------------------------------------------
        # PREVENT OVERPAYMENT
        # ------------------------------------------------------

        if amount > outstanding:
            raise serializers.ValidationError({
                "amount": (
                    "Payment amount cannot be greater "
                    f"than the outstanding balance "
                    f"of {outstanding}."
                )
            })

        return attrs