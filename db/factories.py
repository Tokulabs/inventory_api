from decimal import Decimal
import locale
import factory
import factory.fuzzy
import random

from datetime import datetime

from random import randint, uniform

from django.contrib.auth import get_user_model
User = get_user_model()

from app_control.models import (Provider, Inventory, InventoryGroup, PaymentTerminal, PaymentMethod, DianResolution, Invoice, InvoiceItem, Customer)

class ProviderFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Provider
        exclude = ("provider_suffix")

    created_by = User.objects.get_or_create(id="1")[0]
    name = factory.Faker("company", locale="es_MX")
    provider_suffix = factory.Faker("company_suffix", locale="es_MX")
    legal_name = factory.LazyAttribute(lambda p: '{} {}'.format(p.name, p.provider_suffix))
    nit = factory.Faker("pyint")
    phone = factory.LazyAttribute("phone_number")
    email = factory.Faker("company_email")
    bank_account = factory.Faker("credit_card_number")
    account_type = factory.fuzzy.FuzzyChoice(choices=["Type 1", "Type 2", "Type 3", "Type 4"])
    active = factory.Faker("boolean")

class InventoryGroupFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = InventoryGroup
    
    created_by = User.objects.get_or_create(id="1")[0]
    name = factory.Faker("word", locale="es_MX")


class InventoryFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Inventory

    created_by = User.objects.get_or_create(id="1")[0]
    code = factory.Faker("ean", length=8)
    photo = factory.Faker("image_url")
    provider = factory.SubFactory(ProviderFactory)
    group = factory.SubFactory(InventoryGroupFactory)
    name = factory.Faker("word", locale="es_MX")
    total_in_shops = factory.LazyAttribute(lambda _: randint(0, 100))
    total_in_storage = factory.LazyAttribute(lambda _: randint(0, 1000))
    selling_price = factory.LazyAttribute(lambda _: randint(1000, 1000000))
    buying_price = factory.LazyAttribute(lambda obj: obj.selling_price * 0.9)
    usd_price = factory.LazyAttribute(lambda obj: obj.buying_price / 3900)
    active = factory.Faker("boolean")

class CustomerFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Customer

    created_by = User.objects.get_or_create(id="1")[0]
    document_id = factory.Faker("passport_number")
    name = factory.Faker("company", locale="es_MX")
    phone = factory.LazyAttribute("phone_number")
    email = factory.Faker("company_email")
    address = factory.Faker("address")

class PaymentTerminalFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = PaymentTerminal
    
    created_by = User.objects.get_or_create(id="1")[0]
    account_code = factory.Faker("bban")
    name = factory.Faker("word", locale="es_MX")
    is_wireless = factory.Faker("boolean")
    active = factory.Faker("boolean")

class DianResolutionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = DianResolution
        exclude = ("start_date","end_date")
    
    created_by = User.objects.get_or_create(id="1")[0]
    document_number = factory.LazyAttribute(lambda _: randint(8000000000000, 9999999999999))
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime.now()
    from_date = factory.Faker("date_between", start_date=start_date, end_date=end_date)
 
    to_date = factory.Faker("date_this_year", after_today=True)
 
    from_number = factory.LazyAttribute(lambda _: randint(100000, 900000))
    to_number = factory.LazyAttribute(lambda obj: obj.from_number + 100000)
    current_number = factory.LazyAttribute(lambda obj: randint(obj.from_number, obj.to_number))
    active = factory.Faker("boolean")

class InvoiceFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Invoice
    
    created_by = User.objects.get_or_create(id="1")[0]
    payment_terminal = factory.SubFactory(PaymentTerminalFactory)
    customer = factory.SubFactory(CustomerFactory)
    is_dollar = factory.Faker("boolean")
    sale_by = User.objects.get_or_create(id="1")[0]
    invoice_number = factory.LazyAttribute(lambda _: random.randint(0, 1000000))
    dian_document_number = factory.LazyAttribute(lambda _: randint(8000000000000, 9999999999999))
    is_override = factory.Faker("boolean")


class PaymentMethodFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = PaymentMethod
    
    invoice = factory.SubFactory(InvoiceFactory)
    name = factory.fuzzy.FuzzyChoice(choices=["Cash", "Credit Card", "Debit Card", "ACH"])
    paid_amount = factory.LazyAttribute(lambda _: random.uniform(1000, 1000000))
    back_amount = factory.LazyAttribute(lambda obj: obj.paid_amount * 0.2 * random.uniform(0, 1))
    received_amount = factory.LazyAttribute(lambda obj: obj.paid_amount - obj.back_amount)
    transaction_code = factory.Faker("bban")
    
class InvoiceItemFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = InvoiceItem
    
    invoice = factory.SubFactory(InvoiceFactory)
    item = factory.SubFactory(InventoryFactory)
    item_name = factory.Faker("word", locale="es_MX")
    item_code = factory.Faker("ean", length=8)
    quantity = factory.LazyAttribute(lambda _: randint(0, 100))
    original_amount = factory.LazyAttribute(lambda _: randint(1000, 1000000))
    original_usd_amount = factory.LazyAttribute(lambda obj: obj.amount / 3900)
    discount = factory.LazyAttribute(lambda _: Decimal(random.uniform(0.00, 100.00)))
    amount = factory.LazyAttribute(lambda obj: (obj.original_amount * obj.discount) / 100)
    usd_amount = factory.LazyAttribute(lambda obj: (obj.original_usd_amount * obj.discount) / 100)
    is_gift = is_override = factory.Faker("boolean")