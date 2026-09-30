from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


POSITIVE = MinValueValidator(Decimal('0.000001'))


class Material(models.Model):
    name = models.CharField('Тип материала', max_length=255, unique=True)
    description = models.TextField('Описание состава', blank=True)

    class Meta:
        verbose_name = 'Материал'
        verbose_name_plural = 'Материалы'

    def __str__(self):
        return self.name


class CoefficientSet(models.Model):
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name='coefficient_sets', verbose_name='Материал')
    version = models.PositiveIntegerField('Версия', default=1, validators=[MinValueValidator(1)])
    a0 = models.DecimalField('a0', max_digits=24, decimal_places=15)
    a1 = models.DecimalField('a1', max_digits=24, decimal_places=15)
    a2 = models.DecimalField('a2', max_digits=24, decimal_places=15)
    a3 = models.DecimalField('a3', max_digits=24, decimal_places=15)
    a4 = models.DecimalField('a4', max_digits=24, decimal_places=15)
    a5 = models.DecimalField('a5', max_digits=24, decimal_places=15)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Набор коэффициентов'
        verbose_name_plural = 'Наборы коэффициентов'
        constraints = [models.UniqueConstraint(fields=['material', 'version'], name='unique_material_version')]

    def __str__(self):
        return f'{self.material}, версия {self.version}'


class Experiment(models.Model):
    researcher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='experiments', verbose_name='Исследователь')
    coefficients = models.ForeignKey(CoefficientSet, on_delete=models.PROTECT, related_name='experiments', verbose_name='Набор коэффициентов')
    title = models.CharField('Название', max_length=255)
    pressure_min = models.DecimalField('Минимальное давление, атм', max_digits=12, decimal_places=6, validators=[POSITIVE])
    pressure_max = models.DecimalField('Максимальное давление, атм', max_digits=12, decimal_places=6, validators=[POSITIVE])
    pressure_step = models.DecimalField('Шаг давления, атм', max_digits=12, decimal_places=6, validators=[POSITIVE])
    temperature_min = models.DecimalField('Минимальная температура, °C', max_digits=12, decimal_places=6, validators=[POSITIVE])
    temperature_max = models.DecimalField('Максимальная температура, °C', max_digits=12, decimal_places=6, validators=[POSITIVE])
    temperature_step = models.DecimalField('Шаг температуры, °C', max_digits=12, decimal_places=6, validators=[POSITIVE])
    coefficient_snapshot = models.JSONField('Коэффициенты на момент создания', default=dict, editable=False)
    material_name_snapshot = models.CharField('Материал на момент создания', max_length=255, editable=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Эксперимент'
        verbose_name_plural = 'Эксперименты'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=models.Q(**{f'{field}__gt': 0}), name=f'exp_{field}_positive')
            for field in ('pressure_min', 'pressure_max', 'pressure_step', 'temperature_min', 'temperature_max', 'temperature_step')
        ] + [
            models.CheckConstraint(condition=models.Q(**{f'{axis}_max__gt': models.F(f'{axis}_min')}), name=f'exp_{axis}_range')
            for axis in ('pressure', 'temperature')
        ] + [
            models.CheckConstraint(condition=models.Q(**{f'{axis}_step__lte': models.F(f'{axis}_max') - models.F(f'{axis}_min')}), name=f'exp_{axis}_step_range')
            for axis in ('pressure', 'temperature')
        ]

    def clean(self):
        super().clean()
        errors = {}
        for axis in ('pressure', 'temperature'):
            minimum, maximum, step = (getattr(self, f'{axis}_{suffix}') for suffix in ('min', 'max', 'step'))
            if any(value is not None and (not isinstance(value, (Decimal, int, float)) or not Decimal(str(value)).is_finite()) for value in (minimum, maximum, step)):
                continue
            if minimum is not None and maximum is not None:
                if maximum <= minimum:
                    errors[f'{axis}_max'] = 'Максимум должен быть больше минимума.'
                elif step is not None and step > maximum - minimum:
                    errors[f'{axis}_step'] = 'Шаг не должен превышать ширину диапазона.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.coefficient_snapshot = {f'a{i}': str(getattr(self.coefficients, f'a{i}')) for i in range(6)}
            self.material_name_snapshot = self.coefficients.material.name
        elif type(self).objects.filter(pk=self.pk).exclude(coefficients_id=self.coefficients_id).exists():
            raise ValidationError({'coefficients': 'Для другого набора коэффициентов создайте новый эксперимент.'})
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ComputationRun(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='runs', verbose_name='Эксперимент')
    input_snapshot = models.JSONField('Исходные данные расчёта')
    results = models.JSONField('Точки расчёта', default=list, editable=False)
    computation_seconds = models.FloatField('Время вычисления, с', validators=[MinValueValidator(0)])
    visualization_seconds = models.FloatField('Время визуализации, с', null=True, blank=True, validators=[MinValueValidator(0)])
    peak_memory_bytes = models.PositiveBigIntegerField('Пиковая память, байт')
    operations_per_evaluation = models.PositiveIntegerField('Операций на одно обращение')
    created_at = models.DateTimeField('Выполнен', auto_now_add=True)

    class Meta:
        verbose_name = 'Выполнение расчёта'
        verbose_name_plural = 'Выполнения расчётов'

    def __str__(self):
        return f'{self.experiment} — расчёт {self.pk}'
