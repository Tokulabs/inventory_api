from datetime import datetime, timedelta

from openpyxl.styles import Font, Alignment
from openpyxl.styles.fills import PatternFill
from openpyxl.utils import get_column_letter
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from app_control.models import DianResolution, PaymentTerminal

from .serializers import (
    Inventory, InventorySerializer, InventoryGroupSerializer, InventoryGroup,
    Shop, ShopSerializer, Invoice, InvoiceSerializer, InventoryWithSumSerializer,
    ShopWithAmountSerializer, InvoiceItem, DianSerializer, PaymentTerminalSerializer
)
from rest_framework.response import Response
from rest_framework import status
from inventory_api.custom_methods import IsAuthenticatedCustom
from inventory_api.utils import CustomPagination, get_query, create_terminals_report, create_dollars_report, \
    create_cash_report
from django.db.models import Count, Sum, F, Q
from django.db.models.functions import Coalesce, TruncMonth
from user_control.models import CustomUser
import csv
import codecs
from django.http import HttpResponse
from openpyxl import Workbook


class InventoryView(ModelViewSet):
    http_method_names = ('get', 'put', 'delete', 'post')
    queryset = Inventory.objects.select_related("group", "created_by")
    serializer_class = InventorySerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset

        data = self.request.query_params.dict()
        data.pop("page", None)
        keyword = data.pop("keyword", None)

        results = self.queryset.filter(**data)

        if keyword:
            search_fields = (
                "code", "created_by__fullname", "created_by__email",
                "group__name", "name"
            )
            query = get_query(keyword, search_fields)
            return results.filter(query)

        return results

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        return super().create(request, *args, **kwargs)

    def update(self, request, pk=None):
        inventory = Inventory.objects.filter(pk=pk).first()
        serializer = self.serializer_class(inventory, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        inventory = Inventory.objects.filter(pk=pk).first()
        inventory.delete()
        return Response({"message": "Inventory deleted successfully"}, status=status.HTTP_200_OK)


class InventoryGroupView(ModelViewSet):
    queryset = InventoryGroup.objects.select_related(
        "belongs_to", "created_by").prefetch_related("inventories")
    serializer_class = InventoryGroupSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset
        data = self.request.query_params.dict()
        page = data.pop("page", None)

        if page is not None:
            keyword = data.pop("keyword", None)

            results = self.queryset.filter(**data).order_by('id')

            if keyword:
                search_fields = (
                    "created_by__fullname", "created_by__email",
                )
                query = get_query(keyword, search_fields)
                results = results.filter(query)

            return results.order_by('id').annotate(
                total_items=Count('inventories')
            )

        return self.queryset.order_by('id').annotate(
            total_items=Count('inventories')
        )

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        return super().create(request, *args, **kwargs)


class ShopView(ModelViewSet):
    http_method_names = ('get', 'post', 'put', 'delete')
    queryset = Shop.objects.select_related("created_by")
    serializer_class = ShopSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset
        data = self.request.query_params.dict()
        page = data.pop("page", None)

        if page is not None:
            keyword = data.pop("keyword", None)

            results = self.queryset.filter(**data)

            if keyword:
                search_fields = (
                    "created_by__fullname", "created_by__email", "name"
                )
                query = get_query(keyword, search_fields)
                results = results.filter(query)

            return results

        return self.queryset.order_by('id')

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        return super().create(request, *args, **kwargs)


class PaymentTerminalView(ModelViewSet):
    http_method_names = ('get', 'post', 'put', 'delete')
    queryset = PaymentTerminal.objects.select_related("created_by")
    serializer_class = PaymentTerminalSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset
        data = self.request.query_params.dict()
        page = data.pop("page", None)

        if page is not None:
            keyword = data.pop("keyword", None)

            results = self.queryset.filter(**data)

            if keyword:
                search_fields = (
                    "created_by__fullname", "created_by__email", "name"
                )
                query = get_query(keyword, search_fields)
                results = results.filter(query)

            return results

        return self.queryset.order_by('id')

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        return super().create(request, *args, **kwargs)

    def update(self, request, pk=None):
        terminal = PaymentTerminal.objects.filter(pk=pk).first()
        serializer = self.serializer_class(terminal, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        terminal = PaymentTerminal.objects.filter(pk=pk).first()
        terminal.delete()
        return Response({"message": "Inventory deleted successfully"}, status=status.HTTP_200_OK)


class InvoiceView(ModelViewSet):
    queryset = Invoice.objects.select_related(
        "created_by", "shop", "sale_by", "payment_terminal").prefetch_related("invoice_items")
    serializer_class = InvoiceSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset

        data = self.request.query_params.dict()
        data.pop("page", None)
        keyword = data.pop("keyword", None)

        results = self.queryset.filter(**data)

        if keyword:
            search_fields = (
                "created_by__fullname", "created_by__email", "shop__name"
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        dian_resolution = DianResolution.objects.first()
        new_current_number = dian_resolution.current_number + 1
        dian_resolution.current_number = new_current_number
        dian_resolution.save()

        return super().create(request, *args, **kwargs)


class UpdateInvoiceView(APIView):
    def patch(self, request, invoice_number):
        try:
            invoice = Invoice.objects.get(invoice_number=invoice_number)
        except Invoice.DoesNotExist:
            return Response({"error": "Invoice not found"}, status=status.HTTP_404_NOT_FOUND)

        if invoice.is_override:
            return Response({"error": "Invoice already overrided"}, status=status.HTTP_400_BAD_REQUEST)

        # Actualizar el estado is_override de la factura a True
        invoice.is_override = True

        # Restaurar la cantidad de elementos en el inventario para los InvoiceItems correspondientes
        for item in invoice.invoice_items.all():
            inventory_item = item.item
            inventory_item.total_in_shops += item.quantity
            inventory_item.save()

        # Guardar los cambios en la base de datos
        invoice.save()

        return Response({"message": "Invoice updated successfully"}, status=status.HTTP_200_OK)


class SummaryView(ModelViewSet):
    http_method_names = ('get',)
    permission_classes = (IsAuthenticatedCustom,)
    queryset = InventoryView.queryset

    def list(self, request, *args, **kwargs):
        total_inventory = InventoryView.queryset.filter(
            total_in_storage__gt=0
        ).count()
        total_group = InventoryGroupView.queryset.count()
        total_shop = ShopView.queryset.count()
        total_users = CustomUser.objects.filter(is_superuser=False).count()

        return Response({
            "total_inventory": total_inventory,
            "total_group": total_group,
            "total_shop": total_shop,
            "total_users": total_users
        })


class SalePerformance(ModelViewSet):
    http_method_names = ('get',)
    permission_classes = (IsAuthenticatedCustom,)
    queryset = InventoryView.queryset

    def list(self, request, *args, **kwargs):
        query_data = request.query_params.dict()
        total = query_data.get('total', None)
        query = self.queryset

        if not total:
            start_date = query_data.get("start_date", None)
            end_date = query_data.get("end_date", None)

            if start_date:
                query = query.filter(
                    inventory_invoices__created_at__range=[
                        start_date, end_date]
                )
        items = query.filter(inventory_invoices__invoice__is_override=False).annotate(
            sum_of_item=Coalesce(
                Sum("inventory_invoices__quantity"), 0
            )
        ).order_by('-sum_of_item')[0:10]

        response_data = InventoryWithSumSerializer(items, many=True).data
        return Response(response_data)


class SaleByShopView(ModelViewSet):
    http_method_names = ('get',)
    permission_classes = (IsAuthenticatedCustom,)
    queryset = InventoryView.queryset

    def list(self, request, *args, **kwargs):
        query_data = request.query_params.dict()
        total = query_data.get('total', None)
        monthly = query_data.get('monthly', None)
        query = ShopView.queryset

        if not total:
            start_date = query_data.get("start_date", None)
            end_date = query_data.get("end_date", None)

            if start_date:
                query = query.filter(
                    sale_shop__create_at__range=[start_date, end_date]
                )

        if monthly:
            shops = query.filter(sale_shop__invoice_items__invoice__is_override=False).annotate(month=TruncMonth(
                'created_at')).values('month', 'name').annotate(amount_total=Sum(
                F("sale_shop__invoice_items__quantity") *
                F("sale_shop__invoice_items__amount")
            ))

        else:
            shops = query.filter(sale_shop__invoice_items__invoice__is_override=False).annotate(amount_total=Sum(
                F("sale_shop__invoice_items__quantity") *
                F("sale_shop__invoice_items__amount")
            )).order_by("-amount_total")

        response_data = ShopWithAmountSerializer(shops, many=True).data
        return Response(response_data)


class PurchaseView(ModelViewSet):
    http_method_names = ('get',)
    permission_classes = (IsAuthenticatedCustom,)
    queryset = InvoiceView.queryset

    def list(self, request, *args, **kwargs):
        query_data = request.query_params.dict()
        total = query_data.get('total', None)
        query = InvoiceItem.objects.select_related("invoice", "item")
        start_date = query_data.get("start_date", None)
        end_date = query_data.get("end_date", None)

        if not total and start_date:
            query = query.filter(
                Q(create_at__range=[start_date, end_date]) & Q(
                    invoice__is_override=False)
            )
        else:
            query = query.exclude(invoice__is_override=True)

        results = query.aggregate(
            amount_total=Sum(F('amount') * F('quantity')),
            total=Sum('quantity'),
            amount_total_usd=Sum(F('usd_amount') * F('quantity'),
                                 filter=Q(invoice__is_dolar=True, invoice__is_override=False))
        )

        selling_price = results.get("amount_total", 0.0)
        count = results.get("total", 0)
        price_dolar = results.get("amount_total_usd", 0.0)

        response_data = {
            "count": count,
        }

        if selling_price is not None:
            response_data["selling_price"] = "{:.2f}".format(selling_price)

        if price_dolar is not None:
            response_data["price_dolar"] = "{:.2f}".format(price_dolar)

        return Response(response_data)


class InventoryCSVLoaderView(ModelViewSet):
    http_method_names = ('post',)
    queryset = InventoryView.queryset
    permission_classes = (IsAuthenticatedCustom,)
    serializer_class = InventorySerializer

    def create(self, request, *args, **kwargs):
        try:
            data = request.FILES['data']
        except Exception as e:
            raise Exception("you need to provide inventory CSV data")

        inventory_items = []

        try:
            csv_reader = csv.reader(
                codecs.iterdecode(data, 'utf-8'), delimiter=';')
            for row in csv_reader:
                if not row[0]:
                    continue
                inventory_items.append({
                    "group_id": row[0],
                    "total": row[1],
                    "name": row[2],
                    "price": row[3],
                    "photo": row[4],
                    "created_by_id": request.user.id
                })
        except csv.Error as e:
            raise Exception(e)

        if not inventory_items:
            raise Exception("CSV file cannot be empty")

        data_validation = self.serializer_class(
            data=inventory_items, many=True)
        data_validation.is_valid(raise_exception=True)
        data_validation.save()

        return Response({
            "success": "Inventory items added succesfully"
        })


class DianResolutionView(ModelViewSet):
    queryset = DianResolution.objects.all()
    serializer_class = DianSerializer
    permission_classes = (IsAuthenticatedCustom,)

    def get_queryset(self):
        if self.request.method.lower() != 'get':
            return self.queryset

        data = self.request.query_params.dict()
        results = self.queryset.filter(**data)

        return results

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        return super().create(request, *args, **kwargs)


def daily_report_export(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_diario.xlsx"'

    wb = Workbook()
    ws = wb.active
    ws.title = "REPORTE DIARIO"
    ws.column_dimensions[get_column_letter(2)].width = 27

    terminals_report_data = (
        Invoice.objects.select_related("PaymentMethods", "payment_terminal", "created_by")
        .all()
        # .filter(created_at__date=datetime.now().date())
        .filter(payment_methods__name="creditCard")
        .values_list("payment_terminal__name", "created_by__fullname")
        .annotate(
            quantity=Count("id"),
            total=Sum("payment_methods__paid_amount")
        )
    )

    last_row = create_terminals_report(ws, terminals_report_data)

    dollar_report_data = (
        Invoice.objects.select_related("InvoiceItems", "created_by")
        .all()
        # .filter(created_at__date=datetime.now().date())
        .filter(is_dolar=True)
        .values_list("created_by__fullname")
        .annotate(
            quantity=Sum("invoice_items__usd_amount")
        )
    )

    last_row = create_dollars_report(ws, dollar_report_data, last_row)

    cash_report_data = (
        Invoice.objects.select_related("InvoiceItems", "created_by")
        .all()
        # .filter(created_at__date=datetime.now().date())
        .values_list("created_by__fullname")
        .annotate(
            quantity=Sum("invoice_items__amount")
        )
    )

    dollar_report_data_in_pesos = (
        Invoice.objects.select_related("InvoiceItems", "created_by")
        .all()
        # .filter(created_at__date=datetime.now().date())
        .filter(is_dolar=True)
        .values_list("created_by__fullname")
        .annotate(
            quantity=Sum("invoice_items__amount")
        )
    )



    print(cash_report_data)

    create_cash_report(ws, last_row, cash_report_data)

    wb.save(response)
    return response
