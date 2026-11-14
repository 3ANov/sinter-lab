from io import BytesIO
from openpyxl import Workbook
from openpyxl.chart import ScatterChart, Reference, Series
from .research import result_sections
from .calculation import MODEL_EXPRESSION


def build_excel(run):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Исходные данные"
    data = run.input_snapshot
    for row in [
        ("Эксперимент", data["title"]),
        ("Материал", data["material"]),
        ("Формула", MODEL_EXPRESSION),
        ("Давление min, атм", float(data["pressure_min"])),
        ("Давление max, атм", float(data["pressure_max"])),
        ("Шаг давления, атм", float(data["pressure_step"])),
        ("Температура min, °C", float(data["temperature_min"])),
        ("Температура max, °C", float(data["temperature_max"])),
        ("Шаг температуры, °C", float(data["temperature_step"])),
    ]:
        sheet.append(row)
    sheet["B1"].data_type = sheet["B2"].data_type = "s"
    for name, value in data["coefficients"].items():
        sheet.append([name, float(value)])
    for section in result_sections(run):
        table = workbook.create_sheet(section["label"])
        table.append(
            [f"{section['label']}, {section['unit']}"]
            + [
                f"ρ, г/см³ ({section['fixed_label']} = {level.normalize():f})"
                for level in section["levels"]
            ]
        )
        for x, values in section["rows"]:
            table.append([float(x)] + [float(value) for value in values])
        chart = ScatterChart()
        chart.title = "Зависимость плотности"
        chart.x_axis.title = f"{section['label']}, {section['unit']}"
        chart.y_axis.title = "Плотность, г/см³"
        for column in range(2, 5):
            chart.series.append(
                Series(
                    Reference(table, min_col=column, min_row=1, max_row=table.max_row),
                    Reference(table, min_col=1, min_row=2, max_row=table.max_row),
                    title_from_data=True,
                )
            )
        table.add_chart(chart, "F2")
    metrics = workbook.create_sheet("Экономичность")
    for row in [
        ("Время вычисления, с", run.computation_seconds),
        ("Подготовка графиков на сервере, с", run.visualization_seconds),
        ("Пиковые выделения Python при расчёте, байт", run.peak_memory_bytes),
        ("Арифметических операций на точку", run.operations_per_evaluation),
    ]:
        metrics.append(row)
    for page in workbook:
        page.freeze_panes = "A2"
        for column in ("A", "B", "C", "D"):
            page.column_dimensions[column].width = 35
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
