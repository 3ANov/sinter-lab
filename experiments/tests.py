from io import BytesIO

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from openpyxl import load_workbook


class AuthenticationTests(TestCase):
    def test_login_and_logout(self):
        get_user_model().objects.create_user(
            username="researcher", password="test-password-123"
        )
        self.assertEqual(self.client.get(reverse("experiments:index")).status_code, 302)
        self.assertEqual(self.client.get(reverse("experiments:login")).status_code, 200)
        response = self.client.post(
            reverse("experiments:login"),
            {
                "username": "researcher",
                "password": "test-password-123",
            },
        )
        self.assertRedirects(response, reverse("experiments:index"))
        response = self.client.get(reverse("experiments:index"))
        self.assertContains(response, "researcher")
        self.assertNotContains(response, "Администрирование")
        self.assertEqual(
            self.client.get(reverse("experiments:logout")).status_code, 405
        )
        self.assertRedirects(
            self.client.post(reverse("experiments:logout")),
            reverse("experiments:index"),
            fetch_redirect_response=False,
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_invalid_password_and_external_redirect(self):
        get_user_model().objects.create_user(
            username="admin-test", password="test-password-123", is_staff=True
        )
        response = self.client.post(
            reverse("experiments:login"),
            {
                "username": "admin-test",
                "password": "wrong",
            },
        )
        self.assertContains(response, "Не удалось войти")
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(
            reverse("experiments:login"),
            {
                "username": "admin-test",
                "password": "test-password-123",
                "next": "https://example.com/",
            },
        )
        self.assertRedirects(response, reverse("experiments:index"))
        self.assertContains(
            self.client.get(reverse("experiments:index")), "Администрирование"
        )


class ResearchModelTests(TestCase):
    def setUp(self):
        from .models import CoefficientSet, Experiment

        self.coefficients = CoefficientSet.objects.get(version=1)
        self.experiment = Experiment(
            title="Контрольный эксперимент",
            researcher=get_user_model().objects.create_user(username="scientist"),
            coefficients=self.coefficients,
            pressure_min=40,
            pressure_max=80,
            pressure_step=2,
            temperature_min=1300,
            temperature_max=1500,
            temperature_step=10,
        )

    def test_seed_and_snapshot_preserve_small_coefficient(self):
        from decimal import Decimal

        self.assertEqual(self.coefficients.a5, Decimal("-5e-9"))
        self.experiment.save()
        self.coefficients.a5 = Decimal("0")
        self.coefficients.save()
        self.experiment.refresh_from_db()
        self.assertEqual(
            Decimal(self.experiment.coefficient_snapshot["a5"]), Decimal("-5e-9")
        )

    def test_invalid_ranges_are_rejected(self):
        from django.core.exceptions import ValidationError

        self.experiment.save()
        for field, value in [
            ("pressure_min", 0),
            ("temperature_step", -1),
            ("pressure_max", 40),
            ("pressure_step", 41),
            ("temperature_min", None),
            ("pressure_step", "abc"),
        ]:
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
            (40, 1300, "14.8822"),
            (60, 1400, "15.5008"),
            (80, 1500, "15.8374"),
        ]:
            with self.subTest(pressure=pressure, temperature=temperature):
                self.assertEqual(
                    calculate_density(pressure, temperature, coefficients),
                    Decimal(expected),
                )

    def test_each_formula_term(self):
        from .services.calculation import calculate_density

        for index, expected in enumerate([1, 2, 3, 6, 9, 18]):
            coefficients = {f"a{i}": int(i == index) for i in range(6)}
            with self.subTest(coefficient=index):
                self.assertEqual(calculate_density(2, 3, coefficients), expected)

    def test_invalid_inputs(self):
        from .services.calculation import calculate_density

        coefficients = {f"a{i}": "0" for i in range(6)}
        for value in [None, "", "abc", 0, -1, "NaN", "Infinity"]:
            for pressure, temperature in [(value, 1400), (60, value)]:
                with self.subTest(pressure=pressure, temperature=temperature):
                    with self.assertRaises(ValueError):
                        calculate_density(pressure, temperature, coefficients)
        with self.assertRaises(ValueError):
            calculate_density(60, 1400, {})
        coefficients["a5"] = "NaN"
        with self.assertRaises(ValueError):
            calculate_density(60, 1400, coefficients)


class ResearchInterfaceTests(TestCase):
    def setUp(self):
        from .models import CoefficientSet

        self.user = get_user_model().objects.create_user(username="owner")
        self.client.force_login(self.user)
        self.data = dict(
            title="Контрольный опыт",
            coefficients=CoefficientSet.objects.get(version=1).pk,
            pressure_min=40,
            pressure_max=80,
            pressure_step=2,
            temperature_min=1300,
            temperature_max=1500,
            temperature_step=10,
        )

    def test_calculation_results_export_and_access(self):
        from .models import ComputationRun

        response = self.client.post(reverse("experiments:index"), self.data)
        run = ComputationRun.objects.get()
        self.assertRedirects(response, reverse("experiments:results", args=[run.pk]))
        self.assertEqual(len(run.results), 117)
        response = self.client.get(reverse("experiments:results", args=[run.pk]))
        self.assertEqual(response.content.count(b'class="plotly-graph-div"'), 2)
        self.assertContains(response, "14,882200")
        export_url = reverse("experiments:export_excel", args=[run.pk])
        workbook = load_workbook(BytesIO(self.client.get(export_url).content))
        self.assertEqual(workbook["Давление"].max_row, 22)
        self.assertAlmostEqual(workbook["Давление"]["B2"].value, 14.8822)
        self.assertEqual(len(workbook["Температура"]._charts), 1)
        other = get_user_model().objects.create_user(username="other")
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(response.request["PATH_INFO"]).status_code, 404
        )
        self.assertEqual(self.client.get(export_url).status_code, 404)
        other.is_staff = True
        other.save()
        self.assertEqual(self.client.get(export_url).status_code, 200)

    def test_invalid_and_excessive_ranges_do_not_save(self):
        from .models import Experiment

        for value in ["0", "-1", "abc", "", "0.000001", "50"]:
            response = self.client.post(
                reverse("experiments:index"), {**self.data, "pressure_step": value}
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertFalse(Experiment.objects.exists())

    def test_uneven_steps_include_endpoints_and_midpoints(self):
        from .models import ComputationRun
        from .services.research import result_sections

        self.client.post(
            reverse("experiments:index"),
            {**self.data, "pressure_step": 7, "temperature_step": 30},
        )
        sections = result_sections(ComputationRun.objects.get())
        self.assertEqual(sections[0]["rows"][-1][0], 80)
        self.assertEqual(sections[1]["rows"][-1][0], 1500)
        self.assertEqual(sections[0]["levels"][1], 1400)
