from django.db import models
from user_control.models import CustomUser
from user_control.views import add_user_activity

PaymentMethods = (("cash", "cash"), ("creditCard", "creditCard"), ("debitCard",
                                                                   "debitCard"), ("nequi", "nequi"), ("bankTransfer", "bankTransfer"))


class InventoryGroup(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="inventory_groups",
        on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=100, unique=True)
    belongs_to = models.ForeignKey(
        'self', null=True, on_delete=models.SET_NULL,
        related_name="group_relation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = self.name

    def save(self, *args, **kwargs):
        action = f"added new group - '{self.name}'"
        if self.pk is not None:
            action = f"updated group from - '{self.old_name}' to '{self.name}'"
        super().save(*args, **kwargs)
        add_user_activity(self.created_by, action=action)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted group - '{self.name}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)

    def __str__(self):
        return self.name


class Provider(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="providers",
        on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=50, unique=True)
    legal_name = models.CharField(max_length=100, null=True)
    nit = models.CharField(max_length=20, null=True)
    phone = models.CharField(max_length=20, null=True)
    email = models.EmailField(null=True)
    bank_account = models.CharField(max_length=50, null=True)
    account_type = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = self.name

    def save(self, *args, **kwargs):
        action = f"added new provider - '{self.name}'"
        if self.pk is not None:
            action = f"updated provider from - '{self.old_name}' to '{self.name}'"
        super().save(*args, **kwargs)
        add_user_activity(self.created_by, action=action)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted provider - '{self.name}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)

    def __str__(self):
        return self.name


class Inventory(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="inventory_items",
        on_delete=models.SET_NULL
    )
    code = models.CharField(max_length=10, unique=True, null=True)
    photo = models.TextField(blank=True, null=True)
    provider = models.ForeignKey(
        Provider, related_name="providers", null=True, on_delete=models.SET_NULL
    )
    group = models.ForeignKey(
        InventoryGroup, related_name="inventories", null=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=255)
    total_in_shops = models.PositiveIntegerField(default=0)
    total_in_storage = models.PositiveIntegerField(default=0)
    selling_price = models.FloatField(default=0)
    buying_price = models.FloatField(default=0)
    usd_price = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("code",)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)

        action = f"added new inventory item with code - '{self.code}'"

        if not is_new:
            action = f"updated inventory item with code - '{self.code}'"

        add_user_activity(self.created_by, action=action)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted inventory - '{self.code}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)

    def __str__(self):
        return f"{self.name} - {self.code}"


class Shop(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="shops",
        on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = self.name

    def save(self, *args, **kwargs):
        action = f"added new shop - '{self.name}'"
        if self.pk is not None:
            action = f"updated shop from - '{self.old_name}' to '{self.name}'"
        super().save(*args, **kwargs)
        add_user_activity(self.created_by, action=action)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted shop - '{self.name}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)

    def __str__(self):
        return self.name


class PaymentTerminal(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="payment_terminals",
        on_delete=models.SET_NULL
    )
    account_code = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=100, unique=True)
    is_wireless = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        action = f"added new payment terminal with name - '{self.name}'"
        if not is_new:
            action = f"updated payment terminal item with name - '{self.name}'"
        add_user_activity(self.created_by, action=action)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted payment terminal with name - '{self.name}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)


class Invoice(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="invoices",
        on_delete=models.SET_NULL
    )
    payment_terminal = models.ForeignKey(
        PaymentTerminal, related_name="payment_terminal", null=True, on_delete=models.SET_NULL)
    is_dollar = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    customer_name = models.CharField(max_length=255, null=True)
    customer_id = models.CharField(max_length=255, null=True)
    customer_email = models.CharField(max_length=255, null=True)
    customer_phone = models.CharField(max_length=255, null=True)
    sale_by = models.ForeignKey(
        CustomUser, related_name="sale_by", null=True, on_delete=models.SET_NULL)
    invoice_number = models.CharField(max_length=255, unique=True, null=True)
    dian_document_number = models.CharField(max_length=255, null=True)
    is_override = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted invoice - '{self.id}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)


class PaymentMethod(models.Model):
    invoice = models.ForeignKey(
        Invoice, related_name="payment_methods", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255, choices=PaymentMethods)
    paid_amount = models.FloatField()
    back_amount = models.FloatField()
    received_amount = models.FloatField()
    transaction_code = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, related_name="invoice_items", on_delete=models.CASCADE
    )
    item = models.ForeignKey(
        Inventory, null=True, related_name="inventory_invoices",
        on_delete=models.SET_NULL
    )
    item_name = models.CharField(max_length=255, null=True)
    item_code = models.CharField(max_length=20, null=True)
    quantity = models.PositiveIntegerField()
    amount = models.FloatField(null=True)
    usd_amount = models.FloatField(null=True)
    discount = models.FloatField(default=0)
    original_amount = models.FloatField(null=True)
    original_usd_amount = models.FloatField(null=True)

    def save(self, *args, **kwargs):
        if self.item.total_in_shops < self.quantity:
            raise Exception(
                f"item with code {self.item.code} does not have enough quantity")

        self.item_name = self.item.name
        self.item_code = self.item.code

        self.amount = self.quantity * self.item.selling_price * (1 - self.discount)
        self.usd_amount = self.quantity * self.item.usd_price * (1 - self.discount)
        self.original_amount = self.quantity * self.item.selling_price
        self.original_usd_amount = self.quantity * self.item.usd_price
        self.item.total_in_shops = self.item.total_in_shops - self.quantity
        self.item.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_code} - {self.quantity}"


class DianResolution(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="dian_resolution",
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    document_number = models.CharField(max_length=255, unique=True)
    from_date = models.DateField()
    to_date = models.DateField()
    from_number = models.PositiveIntegerField()
    to_number = models.PositiveIntegerField()
    current_number = models.PositiveIntegerField(default=None)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if self.pk is None:  # se está creando un nuevo objeto
            self.current_number = self.from_number
        super().save(*args, **kwargs)