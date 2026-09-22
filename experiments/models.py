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

