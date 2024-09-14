from django.db.models import Sum

from .models import (Goals, Inventory, InventoryGroup, PaymentMethod, Invoice, InvoiceItem, DianResolution,
                     PaymentTerminal, Provider, Customer, Document_types, InventoryMovement, InventoryMovementItem)
from .models import Inventory, InventoryGroup, PaymentMethod, Invoice, InvoiceItem, DianResolution, Provider, \
    PaymentTerminal
from user_control.serializers import CustomUserSerializer, CustomUserNamesSerializer, CompanySerializer
from rest_framework import serializers


class InventoryGroupSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    belongs_to = serializers.SerializerMethodField(read_only=True)
    belongs_to_id = serializers.CharField(write_only=True, required=False, allow_null=True)
    total_items = serializers.CharField(read_only=True, required=False)
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = InventoryGroup
        exclude = ("company",)

    def get_belongs_to(self, obj):
        if obj.belongs_to is not None:
            return InventoryGroupSerializer(obj.belongs_to).data
        return None


class ProviderSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = Provider
        exclude = ("company",)


class InventorySerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    group = InventoryGroupSerializer(read_only=True)
    group_id = serializers.CharField(write_only=True)
    provider = ProviderSerializer(read_only=True)
    provider_id = serializers.CharField(write_only=True)
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = Inventory
        exclude = ("company",)


class UserWithAmountSerializer(serializers.Serializer):
    user = CustomUserSerializer()
    total_invoice = serializers.FloatField()


class CustomerSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    document_type = serializers.ChoiceField(Document_types)
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = Customer
        exclude = ("company",)


class InvoiceItemSerializer(serializers.ModelSerializer):
    invoice = serializers.CharField(read_only=True)
    invoice_id = serializers.CharField(write_only=True)
    item = InventorySerializer(read_only=True)
    item_id = serializers.CharField(write_only=True)
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = InvoiceItem
        exclude = ("company",)


class InvoiceItemDataSerializer(serializers.Serializer):
    item_id = serializers.CharField()
    quantity = serializers.IntegerField()
    discount = serializers.FloatField()
    amount = serializers.FloatField()
    usd_amount = serializers.FloatField()
    is_gift = serializers.BooleanField()


class PaymentMethodSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = PaymentMethod
        fields = ["name", "paid_amount", "received_amount",
                  "back_amount", "transaction_code", "company_id"]


class PaymentTerminalSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = PaymentTerminal
        exclude = ("company",)


class DianSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = DianResolution
        exclude = ("company",)


class InvoiceSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_id = serializers.CharField(write_only=True, required=False)
    payment_terminal = PaymentTerminalSerializer(read_only=True)
    payment_terminal_id = serializers.CharField(write_only=True, required=False, allow_null=True)
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.CharField(write_only=True)
    invoice_items = InvoiceItemSerializer(read_only=True, many=True)
    invoice_item_data = InvoiceItemDataSerializer(write_only=True, many=True)
    payment_methods = PaymentMethodSerializer(many=True)
    sale_by = CustomUserSerializer(read_only=True)
    sale_by_id = serializers.CharField(write_only=True, required=False)
    dian_resolution = DianSerializer(read_only=True)
    dian_resolution_id = serializers.CharField(write_only=True, required=False)
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = Invoice
        exclude = ("company",)

    def create(self, validated_data):
        invoice_item_data = validated_data.pop("invoice_item_data")
        payment_methods_data = validated_data.pop("payment_methods", [])

        if not invoice_item_data:
            raise Exception("You need to provide at least one Invoice item")

        if not payment_methods_data:
            raise Exception("You need to provide at least one Payment method")

        invoice = super().create(validated_data)

        invoice_item_serializer = InvoiceItemSerializer(data=[
            {"invoice_id": invoice.id,
             "company_id": validated_data["company_id"],
             **item} for item in invoice_item_data
        ], many=True)

        if invoice_item_serializer.is_valid():
            invoice_item_serializer.save()
        else:
            invoice.delete()
            raise Exception(invoice_item_serializer.errors)

        for payment_method_data in payment_methods_data:
            PaymentMethod.objects.create(
                invoice=invoice,
                company_id=validated_data["company_id"],
                **payment_method_data)

        return invoice

    def update(self, instance, validated_data):
        invoice_item_data = validated_data.pop("invoice_item_data")
        payment_methods_data = validated_data.pop("payment_methods", [])

        if not invoice_item_data:
            raise Exception("You need to provide at least one Invoice item")

        if not payment_methods_data:
            raise Exception("You need to provide at least one Payment method")

        invoice = super().update(instance, validated_data)

        InvoiceItem.objects.filter(invoice=invoice).delete()
        PaymentMethod.objects.filter(invoice=invoice).delete()

        invoice_item_serializer = InvoiceItemSerializer(data=[
            {"invoice_id": invoice.id, **item} for item in invoice_item_data
        ], many=True)

        if invoice_item_serializer.is_valid():
            invoice_item_serializer.save()
        else:
            raise Exception(invoice_item_serializer.errors)

        for payment_method_data in payment_methods_data:
            PaymentMethod.objects.create(
                invoice=invoice, **payment_method_data)

        return invoice


class PaymentMethodNamesSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ("name",)


class PaymentTerminalSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTerminal
        fields = ("name", "account_code")


class InvoiceSimpleSerializer(serializers.ModelSerializer):
    payment_terminal = PaymentTerminalSimpleSerializer(read_only=True)
    payment_methods = PaymentMethodNamesSerializer(many=True)
    sale_by = CustomUserNamesSerializer(read_only=True)
    total_sum = serializers.FloatField()
    total_sum_usd = serializers.FloatField()
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = Invoice
        fields = ("invoice_number", "is_dollar", "is_override", "created_at",
                  "payment_terminal", "payment_methods", "sale_by", "total_sum", "total_sum_usd", "company_id")


class GoalSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = Goals
        fields = ['id', 'goal_type', 'goal_value', 'company_id']


class InventoryMovementItemSerializer(serializers.ModelSerializer):
    inventory_id = serializers.CharField(write_only=True)
    inventory = InventorySerializer(read_only=True)
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = InventoryMovementItem
        exclude = ("company", "inventory_movement")


class InventoryMovementSerializer(serializers.ModelSerializer):
    created_by_id = serializers.CharField(write_only=True, required=False)
    created_by = CustomUserSerializer(read_only=True)
    provider_id = serializers.CharField(write_only=True, required=False)
    provider = ProviderSerializer(read_only=True, required=False)
    company_id = serializers.IntegerField(required=False)
    inventory_movement_items = InventoryMovementItemSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = InventoryMovement
        exclude = ("company",)

    def create(self, validated_data):
        movement_items = validated_data.pop("inventory_movement_items", [])

        if not movement_items:
            raise Exception("You need to provide at least one item to the movement")

        movement = super().create(validated_data)

        for movement_items_data in movement_items:
            InventoryMovementItem.objects.create(
                inventory_movement=movement,
                company_id=validated_data["company_id"],
                **movement_items_data)

        return movement

    def update(self, instance, validated_data):
        movement_items = validated_data.pop("inventory_movement_items", [])

        movement = super().update(instance, validated_data)

        if movement_items:
            InventoryMovementItem.objects.filter(inventory_movement=movement).delete()
            for movement_items_data in movement_items:
                InventoryMovementItem.objects.create(
                    inventory_movement=movement,
                    company_id=validated_data["company_id"],
                    **movement_items_data)

        return movement
