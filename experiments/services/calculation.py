"""Расчёт плотности: реализация будет добавлена после определения формул и единиц."""
"""Плотность в г/см³; давление в атм, температура в °C."""

from decimal import Decimal, InvalidOperation, localcontext
from collections.abc import Mapping


MODEL_EXPRESSION = 'ρ = a0 + a1·Pg + a2·T + a3·Pg·T + a4·T² + a5·Pg·T²'
# T² вычисляется один раз: 8 умножений и 5 сложений.
OPERATIONS_PER_EVALUATION = 13


def _number(value, name, *, positive=False):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{name}: требуется число.') from None
    if not number.is_finite():
        raise ValueError(f'{name}: требуется конечное число.')
    if positive and number <= 0:
        raise ValueError(f'{name}: значение должно быть больше нуля.')
    return number


def calculate_density(pressure, temperature, coefficients):
    """Accept a CoefficientSet or an experiment's coefficient_snapshot mapping.

    Negative coefficients are valid. Do not clamp a nonphysical model output:
    callers must be able to see it and assess the model's applicability.
    """
    pressure = _number(pressure, 'Давление', positive=True)
    temperature = _number(temperature, 'Температура', positive=True)
    values = []
    for index in range(6):
        name = f'a{index}'
        try:
            value = coefficients[name] if isinstance(coefficients, Mapping) else getattr(coefficients, name)
        except (KeyError, AttributeError):
            raise ValueError(f'Не задан коэффициент {name}.') from None
        values.append(_number(value, name))
    a0, a1, a2, a3, a4, a5 = values
    # Enough precision for the decimal fields used by the application.
    with localcontext() as context:
        context.prec = 64
        temperature_squared = temperature * temperature
        return (a0 + a1 * pressure + a2 * temperature
                + a3 * pressure * temperature + a4 * temperature_squared
                + a5 * pressure * temperature_squared)
