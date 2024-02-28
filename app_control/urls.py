from django.urls import path, include
from .views import (
    DianResolutionView, InventoryView, ShopView, SummaryView, InvoiceView, PurchaseView, SaleByShopView,
    InventoryGroupView, SalePerformance, InventoryCSVLoaderView, UpdateInvoiceView, PaymentTerminalView
)

from rest_framework.routers import DefaultRouter

router = DefaultRouter(trailing_slash=False)

router.register('inventory', InventoryView, "inventory")
router.register('inventory-csv', InventoryCSVLoaderView, "inventory-csv")
router.register('shop', ShopView, "shop")
router.register('summary', SummaryView, "summary")
router.register('purchase-summary', PurchaseView, "purchase-summary")
router.register('sales-by-shop', SaleByShopView, "sales-by-shop")
router.register('group', InventoryGroupView, "group")
router.register('top-selling', SalePerformance, "top-selling")
router.register('invoice', InvoiceView, "invoice")
router.register('dian-resolution', DianResolutionView, "dian-resolution")
router.register('payment-terminal', PaymentTerminalView, "payment-terminal")

urlpatterns = [
    path("", include(router.urls)),
    path('update-invoice/<str:invoice_number>/',
         UpdateInvoiceView.as_view(), name='update-invoice'),
    path('inventory/<int:pk>/', InventoryView.as_view({'put': 'update', 'delete': 'destroy'}), name='inventory-detail'),
    path('payment-terminal/<int:pk>/', PaymentTerminalView.as_view({'put': 'update', 'delete': 'destroy'}),
         name='payment-terminal-detail'),
]
