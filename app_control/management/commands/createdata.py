from db.factories import (PaymentTerminalFactory, ProviderFactory, InventoryFactory, InventoryGroupFactory, 
                          PaymentMethodFactory, DianResolutionFactory, InvoiceFactory, InvoiceItemFactory, CustomerFactory)
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Command Information"

    def handle(self, *args, **kwargs):

        ProviderFactory.create_batch(10)
        InventoryFactory.create_batch(10)
        InventoryGroupFactory.create_batch(10)
        PaymentTerminalFactory.create_batch(10)
        PaymentMethodFactory.create_batch(10)
        DianResolutionFactory.create_batch(10)
        InvoiceFactory.create_batch(10)
        InvoiceItemFactory.create_batch(10)
        CustomerFactory.create_batch(10)