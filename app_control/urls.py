from django.urls import path, include
from .views import (
    DianResolutionView, InventoryView, SummaryView, InvoiceView, PurchaseView,
    InventoryGroupView, SalePerformance, InventoryCSVLoaderView, UpdateInvoiceView,
    PaymentTerminalView, ReportExporter, ProviderView, SalesByUsersView, InventoriesReportExporter, ItemsReportExporter,
    InvoicesReportExporter, CustomerView, InvoicePainterView
)

from rest_framework.routers import DefaultRouter

router = DefaultRouter(trailing_slash=False)

router.register('inventory', InventoryView, "inventory")
router.register('provider', ProviderView, "provider")
router.register('inventory-csv', InventoryCSVLoaderView, "inventory-csv")
router.register('summary', SummaryView, "summary")
router.register('invoice-painter', InvoicePainterView, "invoice-painter")
router.register('purchase-summary', PurchaseView, "purchase-summary")
router.register('group', InventoryGroupView, "group")
router.register('top-selling', SalePerformance, "top-selling")
router.register('invoice', InvoiceView, "invoice")
router.register('dian-resolution', DianResolutionView, "dian-resolution")
router.register('payment-terminal', PaymentTerminalView, "payment-terminal")
router.register('sales-by-user', SalesByUsersView, "sales-by-user")
router.register('customer', CustomerView, "customer")

urlpatterns = [
    path("", include(router.urls)),
    path('update-invoice/<str:invoice_number>/',
         UpdateInvoiceView.as_view(), name='update-invoice'),
    path('provider/<int:pk>/', ProviderView.as_view({'put': 'update', 'delete': 'destroy'}), name='provider-detail'),
    path('inventory/<int:pk>/', InventoryView.as_view({'put': 'update', 'delete': 'destroy'}), name='inventory-detail'),
    path('payment-terminal/<int:pk>/', PaymentTerminalView.as_view({'put': 'update', 'delete': 'destroy'}),
         name='payment-terminal-detail'),
    path('daily_report_export/', ReportExporter.as_view(), name='daily_report_export'),
    path('inventories_report_export/', InventoriesReportExporter.as_view(), name='inventories_report_export'),
    path('dian-resolution/<int:pk>/', DianResolutionView.as_view({'put': 'update', 'delete': 'destroy'}),
         name='dian-resolution-detail'),
    path('group/<int:pk>/', InventoryGroupView.as_view({'put': 'update', 'delete': 'destroy'}), name='group-detail'),
    path('customer/<int:pk>/', CustomerView.as_view({'put': 'update', 'delete': 'destroy'}), name='customer-detail'),
    path('invoice/<int:pk>/', InvoiceView.as_view({'put': 'update', 'delete': 'destroy'}), name='invoice-detail'),
    path('product_sales_report_export/', ItemsReportExporter.as_view(), name='product_sales_report_export'),
    path('invoices_report_export/', InvoicesReportExporter.as_view(), name='invoices_report_export'),
]
