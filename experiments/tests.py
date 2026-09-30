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


from django.contrib.auth import get_user_model

class ResearchModelTests(TestCase):
    def setUp(self):
        from .models import CoefficientSet, Experiment
        self.coefficients = CoefficientSet.objects.get(version=1)
        self.experiment = Experiment(
            title='Контрольный эксперимент',
            researcher=get_user_model().objects.create_user(username='scientist'),
            coefficients=self.coefficients,
            pressure_min=40, pressure_max=80, pressure_step=2,
            temperature_min=1300, temperature_max=1500, temperature_step=10,
        )

    def test_seed_and_snapshot_preserve_small_coefficient(self):
        from decimal import Decimal
        self.assertEqual(self.coefficients.a5, Decimal('-5e-9'))
        self.experiment.save()
        self.coefficients.a5 = Decimal('0')
        self.coefficients.save()
        self.experiment.refresh_from_db()
        self.assertEqual(Decimal(self.experiment.coefficient_snapshot['a5']), Decimal('-5e-9'))

    def test_invalid_ranges_are_rejected(self):
        from django.core.exceptions import ValidationError
        self.experiment.save()
        for field, value in [('pressure_min', 0), ('temperature_step', -1),
                             ('pressure_max', 40), ('pressure_step', 41),
                             ('temperature_min', None), ('pressure_step', 'abc')]:
            with self.subTest(field=field, value=value):
                original = getattr(self.experiment, field)
                setattr(self.experiment, field, value)
                with self.assertRaises(ValidationError) as caught:
                    self.experiment.full_clean()
                self.assertIn(field, caught.exception.message_dict)
                setattr(self.experiment, field, original)


class DensityCalculationTests(TestCase):
    def test_assignment_reference_values(self):
        from decimal import Decimal
        from .models import CoefficientSet
        from .services.calculation import calculate_density
        coefficients = CoefficientSet.objects.get(version=1)
        for pressure, temperature, expected in [
            (40, 1300, '14.8822'), (60, 1400, '15.5008'), (80, 1500, '15.8374'),
        ]:
            with self.subTest(pressure=pressure, temperature=temperature):
                self.assertEqual(calculate_density(pressure, temperature, coefficients), Decimal(expected))

    def test_each_formula_term(self):
        from .services.calculation import calculate_density
        for index, expected in enumerate([1, 2, 3, 6, 9, 18]):
            coefficients = {f'a{i}': int(i == index) for i in range(6)}
            with self.subTest(coefficient=index):
                self.assertEqual(calculate_density(2, 3, coefficients), expected)

    def test_invalid_inputs(self):
        from .services.calculation import calculate_density
        coefficients = {f'a{i}': '0' for i in range(6)}
        for value in [None, '', 'abc', 0, -1, 'NaN', 'Infinity']:
            for pressure, temperature in [(value, 1400), (60, value)]:
                with self.subTest(pressure=pressure, temperature=temperature):
                    with self.assertRaises(ValueError):
                        calculate_density(pressure, temperature, coefficients)
        with self.assertRaises(ValueError):
            calculate_density(60, 1400, {})
        coefficients['a5'] = 'NaN'
        with self.assertRaises(ValueError):
            calculate_density(60, 1400, coefficients)


