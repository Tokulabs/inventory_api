import jwt
from datetime import datetime, timedelta
from django.conf import settings
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from inventory_api.excel_manager import add_values_to_row_multiple_columns, apply_styles_to_cells, sum_formula_text, \
    add_values_to_col_multiple_rows
from user_control.models import CustomUser
from rest_framework.pagination import PageNumberPagination
import re
from django.db.models import Q

# Excel styles
title_report_font: Font = Font(color="FFFFFF", bold=True)
title_report_fill = PatternFill(start_color="0000FF", end_color="0000FF", fill_type="solid")
headers_font = Font(color="000000", bold=True)
headers_fill = PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid")
totals_fill = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
date_font = Font(color="FFFFFF", bold=True)
alignment = Alignment(horizontal='center', vertical='center')


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
    users = sorted(set([item[1].upper() for item in report_data]))
    second_row_text = ["CANT", "DATAFONO"] + list(users) + ["TOTAL DIA"]

    # add report title and date and their styles
    ws['A1'] = "VENTA EN TARJETAS"
    ws[get_column_letter(second_row_text.index("TOTAL DIA") + 1) + '1'] = current_date
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=2 + len(users))
    apply_styles_to_cells(start_column=1, start_row=1, end_column=2 + len(users), end_row=1,
                          ws=ws, font=title_report_font, alignment=alignment, fill=title_report_fill)
    # apply style to date
    apply_styles_to_cells(start_column=second_row_text.index("TOTAL DIA") + 1, start_row=1,
                          end_column=second_row_text.index("TOTAL DIA") + 1, end_row=1,
                            ws=ws, font=date_font, alignment=alignment, fill=totals_fill)

    # add values and styles to headers
    add_values_to_row_multiple_columns(1, 2, second_row_text, ws)
    apply_styles_to_cells(start_column=1, start_row=2, end_column=len(second_row_text), end_row=2, ws=ws,
                          font=headers_font, alignment=alignment, fill=headers_fill)

    # add dynamic values based in the report data
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

    # compute new rows to write to
    new_created_rows = []
    if updated_rows:
        for row in created_rows:
            for to_delete_column in updated_rows:
                if row > to_delete_column:
                    new_created_rows.append(row - 1)
                else:
                    new_created_rows.append(row)
    else:
        new_created_rows = created_rows

    # delete rows that were updated
    for row_idx in updated_rows:
        ws.delete_rows(row_idx)

    # add values to total column
    total_formulas_total_column = []
    for row in new_created_rows:
        total_formulas_total_column.append(sum_formula_text(row, row, 3, second_row_text.index("TOTAL DIA")))
    add_values_to_col_multiple_rows(second_row_text.index("TOTAL DIA") + 1, new_created_rows[0],
                                    total_formulas_total_column, ws)

    # add values to total rows
    total_formulas_last_row = ["TOTAL VENTA TARJETAS"]
    for index, user in enumerate(second_row_text[2:], start=2):
        start_column = index + 1
        total_formulas_last_row.append(
            sum_formula_text(new_created_rows[0], new_created_rows[-1], start_column, start_column))

    totals_start_column = second_row_text.index("DATAFONO") + 1
    add_values_to_row_multiple_columns(totals_start_column, new_created_rows[-1] + 1, total_formulas_last_row, ws)

    # apply styles to totals row
    apply_styles_to_cells(start_column=1, start_row=new_created_rows[-1] + 1, end_column=len(second_row_text),
                          end_row=new_created_rows[-1] + 1, ws=ws,
                          font=headers_font, alignment=alignment, fill=totals_fill)

    return new_created_rows[-1] + 2


def create_dollars_report(ws, report_data, last_row):
    beginning_row = last_row + 1
    current_date = datetime.now().strftime("%Y-%m-%d")
    users = sorted([item[0].upper() for item in report_data])
    second_row_text = ["CANT", "NOMBRE"] + users + ["TOTAL DIA"]

    # add report title and date
    ws[f'A{beginning_row}'] = "VENTAS EN DOLARES"
    ws[get_column_letter(second_row_text.index("TOTAL DIA") + 1) + f'{beginning_row}'] = current_date
    ws.merge_cells(start_row=beginning_row, start_column=1, end_row=beginning_row, end_column=2 + len(users))

    # apply styles to title and date
    apply_styles_to_cells(start_column=1, start_row=beginning_row, end_column=2 + len(users), end_row=beginning_row,
                          ws=ws, font=title_report_font, alignment=alignment, fill=title_report_fill)
    apply_styles_to_cells(start_column=second_row_text.index("TOTAL DIA") + 1, start_row=beginning_row,
                          end_column=second_row_text.index("TOTAL DIA") + 1, end_row=beginning_row,
                          ws=ws, font=date_font, alignment=alignment, fill=totals_fill)

    # add values and styles to headers
    add_values_to_row_multiple_columns(1, beginning_row + 1, second_row_text, ws)
    apply_styles_to_cells(start_column=1, start_row=beginning_row + 1, end_column=len(second_row_text),
                          end_row=beginning_row + 1, ws=ws, font=headers_font, alignment=alignment, fill=headers_fill)

    # add row titles to column 2
    row_titles = ["TOTAL VENTA DOLARES", "FALTANTE (MENOS)", "SOBRANTE (MAS)", "TOTAL ENTREGADO DOLARES"]
    add_values_to_col_multiple_rows(2, beginning_row + 2, row_titles, ws)

    # add dynamic values based in the report data depending on amount of users
    for item in report_data:
        ws.cell(row=beginning_row + 2, column=second_row_text.index(item[0].upper()) + 1, value=item[1])

    # add formulas to total column
    total_formulas_total_column = []
    for row in range(beginning_row + 2, beginning_row + 6):
        total_formulas_total_column.append(sum_formula_text(row, row, 3, second_row_text.index("TOTAL DIA")))
    add_values_to_col_multiple_rows(second_row_text.index("TOTAL DIA") + 1, beginning_row + 2,
                                    total_formulas_total_column, ws)

    # add formulas to total row
    total_formulas_last_row = []
    for index, user in enumerate(second_row_text[2:], start=2):
        start_column = index + 1
        total_formulas_last_row.append(
            sum_formula_text(beginning_row + 2, beginning_row + 4, start_column, start_column))
    add_values_to_row_multiple_columns(3, beginning_row + 5, total_formulas_last_row, ws)

    # apply styles to totals row
    apply_styles_to_cells(start_column=1, start_row=beginning_row + 5, end_column=len(second_row_text),
                          end_row=beginning_row + 5, ws=ws,
                          font=headers_font, alignment=alignment, fill=totals_fill)

    return beginning_row + 6


def create_cash_report(ws, last_row, report_data):
    beginning_row = last_row + 1
    current_date = datetime.now().strftime("%Y-%m-%d")
    users = sorted([item[0].upper() for item in report_data])
    second_row_text = ["ITEM", "NOMBRE"] + users + ["TOTAL DIA"]

    # add report title and date
    ws[f'A{beginning_row}'] = "VENTAS DIARIAS"
    ws[get_column_letter(second_row_text.index("TOTAL DIA") + 1) + f'{beginning_row}'] = current_date
    ws.merge_cells(start_row=beginning_row, start_column=1, end_row=beginning_row, end_column=2 + len(users))

    # apply styles to title and date
    apply_styles_to_cells(start_column=1, start_row=beginning_row, end_column=2 + len(users), end_row=beginning_row,
                          ws=ws, font=title_report_font, alignment=alignment, fill=title_report_fill)
    apply_styles_to_cells(start_column=second_row_text.index("TOTAL DIA") + 1, start_row=beginning_row,
                          end_column=second_row_text.index("TOTAL DIA") + 1, end_row=beginning_row,
                          ws=ws, font=date_font, alignment=alignment, fill=totals_fill)

    # add values and styles to headers
    add_values_to_row_multiple_columns(1, beginning_row + 1, second_row_text, ws)
    apply_styles_to_cells(start_column=1, start_row=beginning_row + 1, end_column=len(second_row_text),
                          end_row=beginning_row + 1, ws=ws, font=headers_font, alignment=alignment, fill=headers_fill)


