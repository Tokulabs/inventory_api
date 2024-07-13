from datetime import datetime, timedelta

from django.db.models.functions.datetime import ExtractHour, ExtractDay, ExtractMonth, ExtractWeek
from django.db.models.functions.text import Concat

from rest_framework.viewsets import ModelViewSet

from inventory_api.utils import filter_company
from .serializers import (
    Inventory, Invoice, InvoiceItem
)
from rest_framework.response import Response
from rest_framework import status
from inventory_api.custom_methods import IsAuthenticatedCustom
from django.db.models import Sum, F, Q, Value, CharField
from django.db.models.functions import Coalesce
from user_control.models import CustomUser
from .views import InventoryView, InventoryGroupView, InvoiceView


class SummaryView(ModelViewSet):
    http_method_names = ('get',)
    permission_classes = (IsAuthenticatedCustom,)

    def list(self, request, *args, **kwargs):
        total_inventory = filter_company(InventoryView.queryset, self.request.user.company_id).filter(active=True).count()
        total_group = filter_company(InventoryGroupView.queryset, self.request.user.company_id).filter(active=True).count()
        total_users = filter_company(CustomUser.objects, self.request.user.company_id).filter(is_superuser=False).filter(is_active=True).count()

        return Response({
            "total_inventory": total_inventory,
            "total_group": total_group,
            "total_users": total_users
        })


class SalePerformance(ModelViewSet):
    http_method_names = ('post',)
    permission_classes = (IsAuthenticatedCustom,)

    def top_selling(self, request, *args, **kwargs):
        query = filter_company(Inventory.objects.all(), self.request.user.company_id)
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)

        if start_date or end_date:
            if start_date and not end_date:
                return Response({"error": "Debe ingresar una fecha de fin"}, status=status.HTTP_400_BAD_REQUEST)
            if not start_date and end_date:
                return Response({"error": "Debe ingresar una fecha de inicio"}, status=status.HTTP_400_BAD_REQUEST)
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(inventory_invoices__invoice__created_at__date__gte=start_date,
                                 inventory_invoices__invoice__created_at__date__lte=end_date,
                                 inventory_invoices__invoice__is_override=False, inventory_invoices__is_gift=False)
        else:
            query = query.filter(inventory_invoices__invoice__is_override=False, inventory_invoices__is_gift=False)

        items = query.values("name", "photo").annotate(
            sum_top_ten_items=Coalesce(
                Sum("inventory_invoices__quantity"), 0
            )
        ).order_by('-sum_top_ten_items')[0:10]

        return Response(items)


class HourlySalesQuantities(ModelViewSet):
    http_method_names = ('get',)
    permission_classes = (IsAuthenticatedCustom,)

    def list(self, request, *args, **kwargs):
        hours = [{'time': hour, 'total_quantity': 0} for hour in range(24)]

        data = (
            filter_company(Invoice.objects.all(), self.request.user.company_id)
            .filter(is_override=False)
            .filter(invoice_items__is_gift=False)
            .filter(created_at__gte=datetime.now().date())
            .annotate(
                time=ExtractHour('created_at')
            ).values(
                'time'
            ).annotate(
                total_quantity=Sum('invoice_items__quantity')
            ).order_by('time')
        )

        sales_dict = {item['time']: item['total_quantity'] for item in data}

        # Update the hours list with sales data
        for hour in hours:
            if hour['time'] in sales_dict:
                hour['total_quantity'] = sales_dict[hour['time']]

        return Response(hours)


class SalesBySelectedTimeframeSummary(ModelViewSet):
    http_method_names = ('get',)
    permission_classes = (IsAuthenticatedCustom,)

    def list(self, request, *args, **kwargs):
        timeframe = request.GET.get('type', None)

        if timeframe == 'daily':
            days = []
            for i in range(7):
                date_begin = datetime.now() - timedelta(days=i)
                day = f'{date_begin.day}/{date_begin.month}'
                days.append({'day': day, 'total_amount': 0})

            days.reverse()

            data = (
                filter_company(Invoice.objects.all(), self.request.user.company_id)
                .filter(is_override=False)
                .filter(invoice_items__is_gift=False)
                .filter(created_at__gte=datetime.now().date() - timedelta(days=7))
                .annotate(
                    day=Concat(
                        ExtractDay('created_at'),
                        Value('/'),
                        ExtractMonth('created_at'),
                        output_field=CharField()
                    )
                ).values(
                    'day'
                ).annotate(
                    total_amount=Sum('invoice_items__amount')
                ).order_by('day')
            )

            sales_dict = {item['day']: item['total_amount'] for item in data}

            for day in days:
                if day['day'] in sales_dict:
                    day['total_amount'] = sales_dict[day['day']]

            return Response(days)

        elif timeframe == 'weekly':
            weeks = []
            for i in range(5):
                date_begin = datetime.now() - timedelta(weeks=i)
                week_number = f"Week {date_begin.strftime('%V')}"
                weeks.append({'week_number': week_number, 'total_amount': 0})

            weeks.reverse()

            data = (
                filter_company(Invoice.objects.all(), self.request.user.company_id)
                .filter(is_override=False)
                .filter(invoice_items__is_gift=False)
                .filter(created_at__gte=datetime.now().date() - timedelta(weeks=5))
                .annotate(
                    week_number=Concat(Value("Week "), ExtractWeek('created_at'), output_field=CharField())
                )
                .values('week_number')
                .annotate(
                    total_amount=Sum('invoice_items__amount')
                )
                .order_by('week_number')
            )

            sales_dict = {item['week_number']: item['total_amount'] for item in data}

            for week in weeks:
                if week['week_number'] in sales_dict:
                    week['total_amount'] = sales_dict[week['week_number']]

            return Response(weeks)

        elif timeframe == 'monthly':
            months = []
            month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre',
                           'Octubre', 'Noviembre', 'Diciembre']
            current_year = datetime.now().year

            for i in range(1, 13):
                date_begin = datetime(current_year, i, 1)
                month_name = month_names[date_begin.month - 1]
                months.append({'month': month_name, 'total_amount': 0})

            data = (
                filter_company(Invoice.objects.all(), self.request.user.company_id)
                .filter(is_override=False)
                .filter(invoice_items__is_gift=False)
                .filter(created_at__year=current_year)
                .annotate(
                    month=ExtractMonth('created_at'),
                )
                .values('month')
                .annotate(
                    total_amount=Sum('invoice_items__amount')
                )
                .order_by('month')
            )

            sales_dict = {month_names[item['month'] - 1]: item['total_amount'] for item in data}

            for month in months:
                if month['month'] in sales_dict:
                    month['total_amount'] = sales_dict[month['month']]

            return Response(months)

        elif timeframe == 'general':
            today = datetime.now().date()
            current_week_start = today - timedelta(days=today.weekday())
            current_month_start = today.replace(day=1)
            current_year_start = today.replace(month=1, day=1)

            invoices_queryset = filter_company(Invoice.objects.all(), self.request.user.company_id)

            total_day = invoices_queryset.filter(
                is_override=False,
                invoice_items__is_gift=False,
                created_at__date=today
            ).aggregate(total_amount=Sum('invoice_items__amount'))['total_amount'] or 0

            total_week = invoices_queryset.filter(
                is_override=False,
                invoice_items__is_gift=False,
                created_at__gte=current_week_start
            ).aggregate(total_amount=Sum('invoice_items__amount'))['total_amount'] or 0

            total_month = invoices_queryset.filter(
                is_override=False,
                invoice_items__is_gift=False,
                created_at__gte=current_month_start
            ).aggregate(total_amount=Sum('invoice_items__amount'))['total_amount'] or 0

            total_year = invoices_queryset.filter(
                is_override=False,
                invoice_items__is_gift=False,
                created_at__gte=current_year_start
            ).aggregate(total_amount=Sum('invoice_items__amount'))['total_amount'] or 0

            general_values = {
                'daily': total_day,
                'weekly': total_week,
                'monthly': total_month,
                'annual': total_year,
            }

            return Response(general_values)
        else:
            raise Exception("Param Timeframe necesario: daily, weekly or monthly")


class SalesByUsersView(ModelViewSet):
    http_method_names = ('post',)
    permission_classes = (IsAuthenticatedCustom,)

    def sales_by_user(self, request, *args, **kwargs):
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)

        if not start_date or not end_date:
            sales_by_user = (
                filter_company(Invoice.objects.all(), self.request.user.company_id)
                .select_related("InvoiceItems", "sale_by")
                .all()
                .filter(is_override=False)
                .filter(invoice_items__is_gift=False)
                .values(
                    "sale_by__id",
                    "sale_by__fullname",
                    "sale_by__daily_goal"
                )
                .annotate(
                    total_invoice=Sum("invoice_items__amount"),
                )
            )
        else:
            sales_by_user = (
                filter_company(Invoice.objects.all(), self.request.user.company_id)
                .select_related("InvoiceItems", "sale_by")
                .all()
                .filter(is_override=False)
                .filter(invoice_items__is_gift=False)
                .filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
                .values(
                    "sale_by__id",
                    "sale_by__fullname",
                    "sale_by__daily_goal"
                )
                .annotate(
                    total_invoice=Sum("invoice_items__amount"),
                )
            )

        return Response(sales_by_user)


class PurchaseView(ModelViewSet):
    http_method_names = ('post',)
    permission_classes = (IsAuthenticatedCustom,)
    queryset = InvoiceView.queryset

    def purchase_data(self, request, *args, **kwargs):
        query = filter_company(InvoiceItem.objects, self.request.user.company_id).select_related("invoice", "item")
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)

        if start_date or end_date:
            if start_date and not end_date:
                return Response({"error": "Debe ingresar una fecha de fin"}, status=status.HTTP_400_BAD_REQUEST)
            if not start_date and end_date:
                return Response({"error": "Debe ingresar una fecha de inicio"}, status=status.HTTP_400_BAD_REQUEST)
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(invoice__created_at__date__gte=start_date,
                                 invoice__created_at__date__lte=end_date).filter(invoice__is_override=False)
        else:
            query = query.filter(invoice__is_override=False)

        results = query.aggregate(
            amount_total_no_gifts=Sum(F('amount'), filter=Q(is_gift=False)),
            total=Coalesce(Sum(F('quantity'), filter=Q(is_gift=False)), 0),
            gift_total=Coalesce(Sum(F('quantity'), filter=Q(is_gift=True)), 0),
            amount_total_usd=Sum(F('usd_amount'), filter=Q(invoice__is_dollar=True, is_gift=False)),
            amount_total_gifts=Sum(F('amount'), filter=Q(is_gift=True))
        )

        selling_price = results.get("amount_total_no_gifts", 0)
        count = results.get("total", 0)
        gift_count = results.get("gift_total", 0)
        price_dolar = results.get("amount_total_usd", 0)
        selling_price_gifts = results.get("amount_total_gifts", 0)

        response_data = {
            "count": count,
            "gift_count": gift_count,
            "selling_price": selling_price or 0,
            "selling_price_gifts": selling_price_gifts or 0,
            "price_dolar": price_dolar or 0
        }

        return Response(response_data)
