from django import forms
from .models import Experiment, CoefficientSet


class ExperimentForm(forms.ModelForm):
    class Meta:
        model = Experiment
        fields = (
            "title",
            "coefficients",
            "pressure_min",
            "pressure_max",
            "pressure_step",
            "temperature_min",
            "temperature_max",
            "temperature_step",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["coefficients"].queryset = CoefficientSet.objects.select_related(
            "material"
        ).order_by("material__name", "-version")
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
        if not self.is_bound:
            self.initial.update(
                title="Исследование плотности",
                pressure_min=40,
                pressure_max=80,
                pressure_step=2,
                temperature_min=1300,
                temperature_max=1500,
                temperature_step=10,
            )
            self.initial["coefficients"] = self.fields["coefficients"].queryset.first()

    def clean(self):
        data = super().clean()
        for axis in ("pressure", "temperature"):
            low, high, step = (
                data.get(f"{axis}_{part}") for part in ("min", "max", "step")
            )
            if low is not None and high is not None and step is not None and step > 0:
                if (high - low) / step > 1000:
                    self.add_error(
                        f"{axis}_step",
                        "Увеличьте шаг: допускается не более 1000 интервалов по каждой оси.",
                    )
        return data
