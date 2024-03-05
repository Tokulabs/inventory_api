import jwt
from datetime import datetime, timedelta
from django.conf import settings
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from user_control.models import CustomUser
from rest_framework.pagination import PageNumberPagination
import re
from django.db.models import Q


def get_access_token(payload, days):
    token = jwt.encode(
        {"exp": datetime.now() + timedelta(days=days), **payload},
        settings.SECRET_KEY,
        algorithm="HS256"
    )

    return token


def decodeJWT(bearer):
    if not bearer:
        return None

    token = bearer[7:]

    try:
        decoded = jwt.decode(
            token, key=settings.SECRET_KEY, algorithms="HS256"
        )

    except Exception:
        return None

    if decoded:
        try:
            return CustomUser.objects.get(id=decoded["user_id"])
        except Exception:
            return None


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = None

    def get_page_size(self, request):
        """
        Return the page size to use for this request.
        """
        if 'page' in request.query_params:
            # If a specific page is requested, return the configured page size
            return self.page_size
        else:
            # If no page is requested, return a large value to return all results
            return 10000


def normalize_query(query_string, findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]


def get_query(query_string, search_fields):
    query = None  # Query to search for every search term
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None  # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
        return query


def create_terminals_report(ws, report_data):
    current_date = datetime.now().strftime("%Y-%m-%d")

    ws['A1'] = "VENTA EN TARJETAS"

    ws.merge_cells('A1:C1')
    font_ventas_title = Font(color="FFFFFF", bold=True)
    fill_ventas_title = PatternFill(start_color="0000FF", end_color="0000FF", fill_type="solid")

    for cell in ws['A1:C1']:
        for c in cell:
            c.font = font_ventas_title
            c.fill = fill_ventas_title
            c.alignment = Alignment(horizontal='center', vertical='center')

    ws['D1'] = current_date
    ws.merge_cells('D1:E1')
    font_date = Font(color="FFFFFF", bold=True)
    fill_date = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
    ws['D1'].font = font_date
    ws['D1'].fill = fill_date
    ws['D1'].alignment = Alignment(horizontal='center', vertical='center')

    users = sorted(set([item[1].upper() for item in report_data]))
    second_row_text = ["CANT", "DATAFONO"]
    second_row_text = second_row_text + list(users)
    second_row_text.append("TOTAL DIA")
    ws.append(second_row_text)
    font_headers = Font(color="000000", bold=True)
    fill_headers = PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid")
    for col in range(1, second_row_text.__len__() + 1):
        cell = ws.cell(row=2, column=col)
        cell.font = font_headers
        cell.fill = fill_headers
        cell.alignment = Alignment(horizontal='center', vertical='center')

    updated_rows = []
    created_rows = []
    terminals_drawn = {}
    for row_idx, item in enumerate(report_data, start=3):
        if item[0] not in terminals_drawn.keys():
            ws.cell(row=row_idx, column=1, value=item[2])
            ws.cell(row=row_idx, column=2, value=item[0].upper())
            ws.cell(row=row_idx, column=second_row_text.index(item[1].upper()) + 1, value=item[3])
            created_rows.append(row_idx)
        else:
            ws.cell(row=terminals_drawn.get(item[0]), column=1, value=report_data[row_idx - 4][2] + item[2])
            ws.cell(row=terminals_drawn.get(item[0]), column=2, value=item[0].upper())
            ws.cell(row=terminals_drawn.get(item[0]), column=second_row_text.index(item[1].upper()) + 1, value=item[3])
            ws.cell(row=terminals_drawn.get(item[0]), column=second_row_text.index("TOTAL DIA") + 1, value="function")
            updated_rows.append(row_idx)

        terminals_drawn[item[0]] = row_idx

    new_created_rows = []
    for row in created_rows:
        for to_delete_column in updated_rows:
            if row > to_delete_column:
                new_created_rows.append(row - 1)
            else:
                new_created_rows.append(row)

    for row_idx in updated_rows:
        ws.delete_rows(row_idx)

    ws.cell(row=new_created_rows[-1] + 1, column=2, value="TOTAL VENTA TARJETAS")
    ws.cell(row=new_created_rows[-1] + 1, column=3, value=f'=SUM(C{new_created_rows[0]}:C{new_created_rows[-1]})')
    ws.cell(row=new_created_rows[-1] + 1, column=4, value=f'=SUM(D{new_created_rows[0]}:D{new_created_rows[-1]})')
    ws.cell(row=new_created_rows[-1] + 1, column=5,
            value=f'=SUM(C{new_created_rows[-1] + 1}:D{new_created_rows[-1] + 1})')

    for row_idx in range(new_created_rows[0], new_created_rows[-1] + 1):
        ws.cell(row=row_idx, column=second_row_text.index("TOTAL DIA") + 1,
                value=f'=SUM(C{row_idx}:{get_column_letter(second_row_text.index("TOTAL DIA"))}{row_idx})')

    for col_idx in range(1, 6):
        ws.cell(row=new_created_rows[-1] + 1, column=col_idx).font = Font(bold=True)
        ws.cell(row=new_created_rows[-1] + 1, column=col_idx).fill = fill_date

    return new_created_rows[-1] + 2


def create_dollars_report(ws, report_data, last_row):
    beginning_row = last_row + 1
    current_date = datetime.now().strftime("%Y-%m-%d")
    ws[f'A{beginning_row}'] = "VENTAS EN DOLARES"
    ws.merge_cells(f'A{beginning_row}:C{beginning_row}')
    font = Font(color="FFFFFF", bold=True)
    fill = PatternFill(start_color="0000FF", end_color="0000FF", fill_type="solid")

    for cell in ws[f'A{beginning_row}:C{beginning_row}']:
        for c in cell:
            c.font = font
            c.fill = fill
            c.alignment = Alignment(horizontal='center', vertical='center')

    ws[f'D{beginning_row}'] = current_date
    ws.merge_cells(f'D{beginning_row}:E{beginning_row}')
    font_date = Font(color="FFFFFF", bold=True)
    fill_date = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
    for cell in ws[f'D{beginning_row}:E{beginning_row}']:
        for c in cell:
            c.font = font_date
            c.fill = fill_date
            c.alignment = Alignment(horizontal='center', vertical='center')

    users = sorted([item[0].upper() for item in report_data])
    second_row_text = ["CANT", "NOMBRE"]
    second_row_text = second_row_text + users
    second_row_text.append("TOTAL DIA")

    ws.append(second_row_text)

    font_headers = Font(color="000000", bold=True)
    fill_headers = PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid")
    for col in range(1, 6):
        cell = ws.cell(row=beginning_row+1, column=col)
        cell.font = font_headers
        cell.fill = fill_headers
        cell.alignment = Alignment(horizontal='center', vertical='center')

    values = [
        ("", "TOTAL VENTA DOLARES"),
        ("", "FALTANTE (MENOS)"),
        ("", "SOBRANTE (MAS)"),
        ("", "TOTAL ENTREGADO DOLARES")
    ]

    for row_idx, (value1, value2) in enumerate(values, start=beginning_row+2):
        ws.cell(row=row_idx, column=1, value=value1)
        ws.cell(row=row_idx, column=2, value=value2)
        if row_idx in (14, 17):
            for col_idx in range(1, 6):
                ws.cell(row=row_idx, column=col_idx).font = Font(bold=True)
                ws.cell(row=row_idx, column=col_idx).fill = fill_date

    for item in report_data:
        ws.cell(row=beginning_row+2, column=second_row_text.index(item[0].upper()) + 1, value=item[1])

    column_for_functions = get_column_letter(second_row_text.index("TOTAL DIA"))
    column_for_functions_begin = get_column_letter(second_row_text.index("NOMBRE") + 2)
    column_for_functions_index_begin = second_row_text.index("NOMBRE") + 2
    column_for_functions_index = second_row_text.index("TOTAL DIA") + 1

    ws.cell(row=beginning_row+2, column=column_for_functions_index,
            value=f'=SUM({column_for_functions_begin}{beginning_row+2}:{column_for_functions}{beginning_row+2})')
    ws.cell(row=beginning_row+3, column=column_for_functions_index,
            value=f'=SUM({column_for_functions_begin}{beginning_row+3}:{column_for_functions}{beginning_row+3})')
    ws.cell(row=beginning_row+4, column=column_for_functions_index,
            value=f'=SUM({column_for_functions_begin}{beginning_row+4}:{column_for_functions}{beginning_row+4})')
    ws.cell(row=beginning_row + 5, column=column_for_functions_index,
            value=f'=SUM({column_for_functions_begin}{beginning_row + 5}:{column_for_functions}{beginning_row + 5})')

    for col_idx, user in enumerate(users, start=column_for_functions_index_begin):
        column_letter = get_column_letter(col_idx)
        ws.cell(row=beginning_row + 5, column=col_idx,
                value=f'=SUM({column_letter}{beginning_row + 2}:{column_letter}{beginning_row + 4})')


def create_cash_report(ws):
    current_date = datetime.now().strftime("%Y-%m-%d")
    ws['A19'] = "VENTAS DIARIAS"
    ws.merge_cells('A19:C19')
    font = Font(color="FFFFFF", bold=True)
    fill = PatternFill(start_color="0000FF", end_color="0000FF", fill_type="solid")

    for cell in ws['A19:C19']:
        for c in cell:
            c.font = font
            c.fill = fill
            c.alignment = Alignment(horizontal='center', vertical='center')

    ws['D19'] = current_date
    ws.merge_cells('D19:E19')
    font_date = Font(color="FFFFFF", bold=True)
    fill_date = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
    for cell in ws['D19:E19']:
        for c in cell:
            c.font = font_date
            c.fill = fill_date
            c.alignment = Alignment(horizontal='center', vertical='center')

    second_row_text = ["ITEM", "NOMBRE", "CAJA 1", "CAJA 2", "TOTAL DIA"]
    for i, value in enumerate(second_row_text):
        cell = ws.cell(row=20, column=i + 1)
        cell.value = value

    font_headers = Font(color="000000", bold=True)
    fill_headers = PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid")
    for col in range(1, 6):
        cell = ws.cell(row=20, column=col)
        cell.font = font_headers
        cell.fill = fill_headers
        cell.alignment = Alignment(horizontal='center', vertical='center')

    values = [
        ("1", "TOTAL DIA POS"),
        ("2", "DOLAR EQUIVALENTE $ (MENOS)"),
        ("3", "VENTAS TARJETAS (MENOS)"),
        ("4", "VENTAS DATAF INALAMBRICO AZUL"),
        ("5", "TRANSFERENCIA QR CTA AHORROS"),
        ("6", "OTROS DCTOS"),
        ("", "SUBTOTAL"),
        ("7", "PAGO APOYO VENTAS (MENOS)"),
        ("", "TOTAL EN PESOS"),
        ("8", "FALTANTE (MENOS)"),
        ("9", "SOBRANTE (MAS)"),
        ("", "TOTAL ENTREGADO PESOS")
    ]

    for row_idx, (value1, value2) in enumerate(values, start=21):
        ws.cell(row=row_idx, column=1, value=value1)
        ws.cell(row=row_idx, column=2, value=value2)
        if row_idx in (21, 27, 29, 32):
            for col_idx in range(1, 6):  # Columns 1 and 2
                ws.cell(row=row_idx, column=col_idx).font = Font(bold=True)
                ws.cell(row=row_idx, column=col_idx).fill = fill_date
