from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from .views import DEMO_ROWS


class StarterTests(TestCase):
    def test_home_renders_chart_and_export_link(self):
        response = self.client.get(reverse("experiments:index"))
        self.assertContains(response, "Plotly.newPlot")
        self.assertContains(response, reverse("experiments:export_excel"))

    def test_excel_contains_displayed_data(self):
        response = self.client.get(reverse("experiments:export_excel"))
        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content))
        rows = list(workbook.active.values)
        self.assertEqual(rows[0], ("Время, мин", "Температура, °C"))
        self.assertEqual(rows[1:], DEMO_ROWS)
