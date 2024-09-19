from django.urls import path, include

from .reports import ReportExporter, InventoriesReportExporter, ItemsReportExporter, InvoicesReportExporter, \
    ElectronicInvoiceExporter
from .stats import SummaryView, HourlySalesQuantities, SalesBySelectedTimeframeSummary, PurchaseView, SalePerformance, \
    SalesByUsersView
from .views import (
    DianResolutionView, GoalView, InventoryView, InvoiceView,
    InventoryGroupView, InventoryCSVLoaderView, UpdateInvoiceView,
    PaymentTerminalView, ProviderView, CustomerView, InvoicePainterView, InvoiceSimpleListView,
    InvoicePaymentMethodsView, UploadFileView
)

from rest_framework.routers import DefaultRouter

router = DefaultRouter(trailing_slash=False)

router.register('inventory', InventoryView, "inventory")
router.register('provider', ProviderView, "provider")
router.register('inventory-csv', InventoryCSVLoaderView, "inventory-csv")
router.register('summary', SummaryView, "summary")
router.register('invoice-painter', InvoicePainterView, "invoice-painter")
router.register('group', InventoryGroupView, "group")
router.register('invoice', InvoiceView, "invoice")
router.register('dian-resolution', DianResolutionView, "dian-resolution")
router.register('payment-terminal', PaymentTerminalView, "payment-terminal")
router.register('customer', CustomerView, "customer")
router.register('invoice-simple-list', InvoiceSimpleListView, "invoice-simple-list")
router.register('hourly-quantities', HourlySalesQuantities, "hourly-quantities")
router.register('sales-by-timeframe', SalesBySelectedTimeframeSummary, "sales-by-timeframe")
router.register('goals', GoalView, "goals")

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
    path('invoice/<int:pk>/', InvoiceView.as_view({'delete': 'destroy'}), name='invoice-detail'),
    path('product_sales_report_export/', ItemsReportExporter.as_view(), name='product_sales_report_export'),
    path('invoices_report_export/', InvoicesReportExporter.as_view(), name='invoices_report_export'),
    path('electronic_invoice_export/', ElectronicInvoiceExporter.as_view(), name='electronic_invoice_export'),
    path('inventory/<int:pk>/toggle-active/',
         InventoryView.as_view({'post': 'toggle_active'}), name='inventory-toggle'),
    path('provider/<int:pk>/toggle-active/',
         ProviderView.as_view({'post': 'toggle_active'}), name='provider-toggle'),
    path('payment-terminal/<int:pk>/toggle-active/',
         PaymentTerminalView.as_view({'post': 'toggle_active'}), name='terminal-toggle'),
    path('dian-resolution/<int:pk>/toggle-active/',
         DianResolutionView.as_view({'post': 'toggle_active'}), name='resolution-toggle'),
    path('group/<int:pk>/toggle-active/',
         InventoryGroupView.as_view({'post': 'toggle_active'}), name='resolution-toggle'),
    path('purchase-summary', PurchaseView.as_view({'post': 'purchase_data'}), name='purchase-summary'),
    path('top-selling', SalePerformance.as_view({'post': 'top_selling'}), name='top-selling'),
    path('sales-by-user', SalesByUsersView.as_view({'post': 'sales_by_user'}), name='sales-by-user'),
    path('goals/<int:pk>/', GoalView.as_view({'put': 'update', 'delete': 'destroy'}), name='goal-detail'),
    path('update-payment-methods', InvoicePaymentMethodsView.as_view(), name='invoice-payment-methods'),
    path('upload-photo/', UploadFileView.as_view({'post': 'upload_photo'}), name='upload-photo')
]
