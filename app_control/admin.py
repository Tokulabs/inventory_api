from django.contrib import admin
from .models import Inventory, InventoryGroup, PaymentMethod, Invoice, InvoiceItem, DianResolution

admin.site.register((Inventory, InventoryGroup,
                    PaymentMethod, Invoice, InvoiceItem, DianResolution))
