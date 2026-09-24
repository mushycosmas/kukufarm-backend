from django.db import transaction
from rest_framework import serializers
from .models import Sale, SaleItem

class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ["id","product","quantity","unit_price","total"]
        read_only_fields = ["id","total"]

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, required=False)
    class Meta:
        model = Sale
        fields = ["id","customer","date","invoice_no","payment_method","subtotal","discount","total","notes","items","created_at","updated_at"]
        read_only_fields = ["id","subtotal","total","created_at","updated_at"]

    def _calculate(self, sale, items):
        subtotal = sum((item["quantity"] * item["unit_price"] for item in items), start=0)
        sale.subtotal = subtotal
        sale.total = max(0, subtotal - sale.discount)
        sale.save(update_fields=["subtotal","total","updated_at"])

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items", [])
        sale = Sale.objects.create(**validated_data)
        for item in items:
            SaleItem.objects.create(sale=sale, total=item["quantity"] * item["unit_price"], **item)
        self._calculate(sale, items)
        return sale

    @transaction.atomic
    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for key, value in validated_data.items(): setattr(instance, key, value)
        instance.save()
        if items is not None:
            instance.items.all().delete()
            for item in items:
                SaleItem.objects.create(sale=instance, total=item["quantity"] * item["unit_price"], **item)
            self._calculate(instance, items)
        else:
            instance.total = max(0, instance.subtotal - instance.discount)
            instance.save(update_fields=["total","updated_at"])
        return instance
