from .models import (Inventory, InventoryGroup, PaymentMethod, Shop, Invoice, InvoiceItem, DianResolution,
                     PaymentTerminal, Provider)
from .models import Inventory, InventoryGroup, PaymentMethod, Shop, Invoice, InvoiceItem, DianResolution, Provider, PaymentTerminal
from user_control.serializers import CustomUserSerializer
from rest_framework import serializers


class InventoryGroupSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    belongs_to = serializers.SerializerMethodField(read_only=True)
    belongs_to_id = serializers.CharField(write_only=True, required=False)
    total_items = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = InventoryGroup
        fields = "__all__"

    def get_belongs_to(self, obj):
        if obj.belongs_to is not None:
            return InventoryGroupSerializer(obj.belongs_to).data
        return None


class ProviderSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Provider
        fields = "__all__"


class InventorySerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    group = InventoryGroupSerializer(read_only=True)
    group_id = serializers.CharField(write_only=True)
    provider = ProviderSerializer(read_only=True)
    provider_id = serializers.CharField(write_only=True)

    class Meta:
        model = Inventory
        fields = "__all__"


class InventoryWithSumSerializer(InventorySerializer):
    sum_of_item = serializers.IntegerField()


class ShopSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    amount_total = serializers.CharField(read_only=True, required=False)
    count_total = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Shop
        fields = "__all__"

class UserWithAmounSerializer(serializers.Serializer):
    user = CustomUserSerializer()
    amount = serializers.FloatField()

class InvoiceItemSerializer(serializers.ModelSerializer):
    invoice = serializers.CharField(read_only=True)
    invoice_id = serializers.CharField(write_only=True)
    item = InventorySerializer(read_only=True)
    item_id = serializers.CharField(write_only=True)

    class Meta:
        model = InvoiceItem
        fields = "__all__"


class InvoiceItemDataSerializer(serializers.Serializer):
    item_id = serializers.CharField()
    quantity = serializers.IntegerField()


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["name", "paid_amount", "received_amount",
                  "back_amount", "transaction_code"]


class PaymentTerminalSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = PaymentTerminal
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    payment_terminal = PaymentTerminalSerializer(read_only=True)
    payment_terminal_id = serializers.CharField(write_only=True)
    invoice_items = InvoiceItemSerializer(read_only=True, many=True)
    invoice_item_data = InvoiceItemDataSerializer(write_only=True, many=True)
    payment_methods = PaymentMethodSerializer(many=True)
    sale_by = CustomUserSerializer(read_only=True)
    sale_by_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Invoice
        fields = "__all__"

    def create(self, validated_data):
        invoice_item_data = validated_data.pop("invoice_item_data")
        payment_methods_data = validated_data.pop("payment_methods", [])

        if not invoice_item_data:
            raise Exception("You need to provide at least one Invoice item")

        if not payment_methods_data:
            raise Exception("You need to provide at least one Payment method")

        invoice = super().create(validated_data)

        invoice_item_serializer = InvoiceItemSerializer(data=[
            {"invoice_id": invoice.id, **item} for item in invoice_item_data
        ], many=True)

        if invoice_item_serializer.is_valid():
            invoice_item_serializer.save()
        else:
            invoice.delete()
            raise Exception(invoice_item_serializer.errors)

        for payment_method_data in payment_methods_data:
            PaymentMethod.objects.create(
                invoice=invoice, **payment_method_data)

        return invoice


class DianSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = DianResolution
        fields = "__all__"
