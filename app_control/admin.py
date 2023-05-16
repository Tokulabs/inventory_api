from django.contrib import admin
from .models import Inventory, InventoryGroup, Shop, PaymentMethod, Invoice, InvoiceItem, DianResolution

admin.site.register((Inventory, InventoryGroup, Shop,
                    PaymentMethod, Invoice, InvoiceItem, DianResolution))
