from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from rest_framework import serializers

from .models import (
    Sale,
    SaleItem,
    SalePayment,
)


# ==============================================================
# SALE ITEM SERIALIZER
# ==============================================================

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

    Handles:

    - Sale creation
    - Sale updates
    - Invoice generation
    - Subtotal calculation
    - Total calculation
    - Balance calculation
    - Payment status
    - Egg stock validation
    - Initial payment validation

    IMPORTANT PAYMENT RULE:

    Sale.amount_paid represents the TOTAL amount paid so far.

    Example:

        Sale total = 2,500
        Initial payment = 500

        amount_paid = 500
        balance = 2,000

        Additional payment = 1,000

        amount_paid = 1,500
        balance = 1,000
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

        total = Decimal(
            obj.total or 0
        )

        amount_paid = Decimal(
            obj.amount_paid or 0
        )

        balance = total - amount_paid

        return max(
            balance,
            Decimal("0"),
        )

    # ==========================================================
    # GENERATE INVOICE NUMBER
    # ==========================================================

    def _generate_invoice_number(self):

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
    # PAYMENT STATUS
    # ==========================================================

    def _calculate_payment_status(self, sale):

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
    # ==============================================================

    def _calculate(self, sale, items):

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
    # EGG QUANTITY
    # ==========================================================

    def _egg_quantity_in_eggs(self, item):

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

        # When editing a sale,
        # return its existing eggs first.
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
    # VALIDATE INITIAL PAYMENT
    # ==========================================================

    def _validate_payment(
        self,
        amount_paid,
        total,
    ):

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
        # VALIDATE EGG STOCK
        # ------------------------------------------------------

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
        # CREATE ITEMS
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
        # CALCULATE TOTAL
        # ------------------------------------------------------

        self._calculate(
            sale,
            items,
        )

        # ------------------------------------------------------
        # VALIDATE PAYMENT
        # ------------------------------------------------------

        self._validate_payment(
            sale.amount_paid,
            sale.total,
        )

        # ------------------------------------------------------
        # UPDATE STATUS
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

        items = validated_data.pop(
            "items",
            None,
        )

        # Never allow invoice number changes.
        validated_data.pop(
            "invoice_no",
            None,
        )

        # IMPORTANT:
        # Do not accidentally reset amount_paid
        # when editing the sale.
        validated_data.pop(
            "amount_paid",
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
        # UPDATE ITEMS
        # ------------------------------------------------------

        if items is not None:

            self._validate_egg_stock(
                items,
                current_sale=instance,
            )

            instance.items.all().delete()

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

            self._calculate(
                instance,
                items,
            )

        else:

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
        # VALIDATE CURRENT CUMULATIVE PAYMENT
        # ------------------------------------------------------

        self._validate_payment(
            instance.amount_paid,
            instance.total,
        )

        # ------------------------------------------------------
        # FINAL STATUS
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
    Serializer for additional payments.

    IMPORTANT:

    Sale.amount_paid already contains the cumulative
    amount paid.

    Example:

        Sale total = 2,500
        amount_paid = 500

        New payment = 1,000

        New amount_paid = 1,500

        Balance = 1,000
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

        sale = attrs.get("sale")

        # When editing an existing payment,
        # use its existing sale.
        if sale is None and self.instance:

            sale = self.instance.sale

        if sale is None:

            raise serializers.ValidationError({
                "sale": (
                    "A sale is required for this payment."
                )
            })

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
        # CURRENT SALE PAYMENT
        # ------------------------------------------------------

        current_paid = Decimal(
            sale.amount_paid or 0
        )

        # ------------------------------------------------------
        # WHEN EDITING PAYMENT
        # ------------------------------------------------------

        if self.instance:

            old_amount = Decimal(
                self.instance.amount or 0
            )

            # Remove the old payment from the
            # cumulative amount before adding
            # the new amount.

            current_paid -= old_amount

        # ------------------------------------------------------
        # SALE TOTAL
        # ------------------------------------------------------

        sale_total = Decimal(
            sale.total or 0
        )

        # ------------------------------------------------------
        # OUTSTANDING BALANCE
        # ------------------------------------------------------

        outstanding = (
            sale_total
            - current_paid
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