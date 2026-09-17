"""Формирование Excel без зависимости от HTTP."""

from io import BytesIO

from openpyxl import Workbook


def build_excel(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Демонстрационные данные"
    sheet.append(["Время, мин", "Температура, °C"])
    for row in rows:
        sheet.append(row)
    sheet.freeze_panes = "A2"
    sheet.column_dimensions["A"].width = 20
    sheet.column_dimensions["B"].width = 24
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
