from django.db import models
from django.db.models import UniqueConstraint

from user_control.models import CustomUser, Company
from user_control.views import add_user_activity

PaymentMethods = (("cash", "cash"), ("creditCard", "creditCard"), ("debitCard",
                                                                   "debitCard"), ("nequi", "nequi"),
                  ("bankTransfer", "bankTransfer"))

Document_types = (("CC", "CC"), ("PA", "PA"), ("NIT", "NIT"),
                  ("CE", "CC"), ("TI", "TI"), ("DIE", "DIE"))


class InventoryGroup(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="inventory_groups",
        on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=100)
    belongs_to = models.ForeignKey(
        'self', null=True, on_delete=models.SET_NULL,
        related_name="group_relation"
    )
    active = models.BooleanField(default=True, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey(
        Company, null=True, related_name="inventory_group_company",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            UniqueConstraint(fields=["name", "company"], name="unique_group_name")
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = self.name

    def save(self, *args, **kwargs):
        action = f"added new group - '{self.name}'"
        if self.pk is not None:
            action = f"updated group from - '{self.old_name}' to '{self.name}'"
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted group - '{self.name}'"
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class Provider(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="providers",
        on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=50)
    legal_name = models.CharField(max_length=100, null=True)
    nit = models.CharField(max_length=20, null=True)
    phone = models.CharField(max_length=20, null=True)
    email = models.EmailField(null=True)
    bank_account = models.CharField(max_length=50, null=True)
    account_type = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True, null=False)
    company = models.ForeignKey(
        Company, null=True, related_name="provider_company",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            UniqueConstraint(fields=["name", "company"], name="unique_provider_name")
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = self.name

    def save(self, *args, **kwargs):
        action = f"added new provider - '{self.name}'"
        if self.pk is not None:
            action = f"updated provider from - '{self.old_name}' to '{self.name}'"
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted provider - '{self.name}'"
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class Inventory(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="inventory_items",
        on_delete=models.SET_NULL
    )
    code = models.CharField(max_length=10, null=True)
    photo = models.TextField(blank=True, null=True)
    provider = models.ForeignKey(
        Provider, related_name="providers", null=True, on_delete=models.SET_NULL
    )
    group = models.ForeignKey(
        InventoryGroup, related_name="inventories", null=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=255)
    cost_center = models.CharField(max_length=255, null=True)
    total_in_shops = models.PositiveIntegerField(default=0)
    total_in_storage = models.PositiveIntegerField(default=0)
    selling_price = models.FloatField(default=0)
    buying_price = models.FloatField(default=0)
    usd_price = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True, null=False)
    company = models.ForeignKey(
        Company, null=True, related_name="inventory_company",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        ordering = ("code",)
        constraints = [
            UniqueConstraint(fields=["code", "company"], name="unique_code")
        ]

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)

        action = f"added new inventory item with code - '{self.code}'"

        if not is_new:
            action = f"updated inventory item with code - '{self.code}'"

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted inventory - '{self.code}'"
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.code}"


class Customer(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="customers",
        on_delete=models.SET_NULL
    )
    document_id = models.CharField(max_length=20)
    document_type = models.CharField(max_length=3, choices=Document_types, default="CC")
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, null=True)
    email = models.EmailField(null=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey(
        Company, null=True, related_name="customer_company",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            UniqueConstraint(fields=["document_id", "company"], name="unique_customer_document_id")
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = self.name

    def save(self, *args, **kwargs):
        action = f"added new customer - '{self.name}'"
        if self.pk is not None:
            action = f"updated customer from - '{self.old_name}' to '{self.name}'"
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted customer - '{self.name}'"
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class PaymentTerminal(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="payment_terminals",
        on_delete=models.SET_NULL
    )
    account_code = models.CharField(max_length=200)
    name = models.CharField(max_length=100)
    is_wireless = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True, null=False)
    company = models.ForeignKey(
        Company, null=True, related_name="payment_terminal_company",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            UniqueConstraint(fields=["name", "company"], name="unique_name+")
        ]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        action = f"added new payment terminal with name - '{self.name}'"
        if not is_new:
            action = f"updated payment terminal item with name - '{self.name}'"

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted payment terminal with name - '{self.name}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)


class DianResolution(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="dian_resolution",
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    document_number = models.CharField(max_length=255)
    from_date = models.DateField()
    to_date = models.DateField()
    from_number = models.PositiveIntegerField()
    to_number = models.PositiveIntegerField()
    current_number = models.PositiveIntegerField(default=None)
    active = models.BooleanField(default=True, null=False)
    company = models.ForeignKey(
        Company, null=True, related_name="resolution_company",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            UniqueConstraint(fields=["document_number", "company"], name="unique_dian_document_number")
        ]

    def save(self, *args, **kwargs):
        if self.pk is None:  # se está creando un nuevo objeto
            self.current_number = self.from_number
        super().save(*args, **kwargs)


class Invoice(models.Model):
    created_by = models.ForeignKey(
        CustomUser, null=True, related_name="invoices",
        on_delete=models.SET_NULL
    )
    payment_terminal = models.ForeignKey(
        PaymentTerminal, related_name="payment_terminal", null=True, on_delete=models.SET_NULL)
    customer = models.ForeignKey(
        Customer, related_name="customer", null=True, on_delete=models.SET_NULL)
    is_dollar = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sale_by = models.ForeignKey(
        CustomUser, related_name="sale_by", null=True, on_delete=models.SET_NULL)
    invoice_number = models.CharField(max_length=255, null=True)
    dian_resolution = models.ForeignKey(
        DianResolution, related_name="dian_resolution", null=True, on_delete=models.SET_NULL)
    is_override = models.BooleanField(default=False)
    company = models.ForeignKey(
        Company, null=True, related_name="invoice_company",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            UniqueConstraint(fields=["invoice_number", "company"], name="unique_invoice")
        ]

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"deleted invoice - '{self.id}'"
        super().delete(*args, **kwargs)


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
    company = models.ForeignKey(
        Company, null=True, related_name="payment_method_company",
        on_delete=models.DO_NOTHING
    )

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
    is_gift = models.BooleanField(default=False)
    company = models.ForeignKey(
        Company, null=True, related_name="invoice_item_company",
        on_delete=models.DO_NOTHING
    )

    def save(self, *args, **kwargs):
        if self.item.total_in_shops < self.quantity:
            raise Exception(
                f"item with code {self.item.code} does not have enough quantity")

        self.item_name = self.item.name
        self.item_code = self.item.code
        self.amount = self.amount
        self.usd_amount = self.usd_amount

        self.original_amount = self.quantity * self.item.selling_price
        self.original_usd_amount = self.quantity * self.item.usd_price
        self.item.total_in_shops = self.item.total_in_shops - self.quantity
        self.item.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_code} - {self.quantity}"


class Goals(models.Model):
    DIARY = 'diary'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    ANNUAL = 'annual'

    GOAL_TYPE_CHOICES = [
        (DIARY, 'Diary'),
        (WEEKLY, 'Weekly'),
        (MONTHLY, 'Monthly'),
        (ANNUAL, 'Annual'),
    ]

    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES)
    goal_value = models.FloatField()
    company = models.ForeignKey(
        Company, null=True, related_name="goals_company",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        constraints = [
            UniqueConstraint(fields=["goal_type", "company"], name="unique_goal_type")
        ]

    def __str__(self):
        return f"{self.get_goal_type_display()} - {self.goal_value}"
