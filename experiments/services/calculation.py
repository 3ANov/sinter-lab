from decimal import Decimal, InvalidOperation, localcontext
from collections.abc import Mapping


MODEL_EXPRESSION = "ρ = a0 + a1·Pg + a2·T + a3·Pg·T + a4·T² + a5·Pg·T²"
OPERATIONS_PER_EVALUATION = 13


def _number(value, name, *, positive=False):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name}: требуется число.") from None
    if not number.is_finite():
        raise ValueError(f"{name}: требуется конечное число.")
    if positive and number <= 0:
        raise ValueError(f"{name}: значение должно быть больше нуля.")
    return number


def calculate_density(pressure, temperature, coefficients):
    pressure = _number(pressure, "Давление", positive=True)
    temperature = _number(temperature, "Температура", positive=True)
    values = []
    for index in range(6):
        name = f"a{index}"
        try:
            value = (
                coefficients[name]
                if isinstance(coefficients, Mapping)
                else getattr(coefficients, name)
            )
        except (KeyError, AttributeError):
            raise ValueError(f"Не задан коэффициент {name}.") from None
        values.append(_number(value, name))
    a0, a1, a2, a3, a4, a5 = values
    with localcontext() as context:
        context.prec = 64
        temperature_squared = temperature * temperature
        return (
            a0
            + a1 * pressure
            + a2 * temperature
            + a3 * pressure * temperature
            + a4 * temperature_squared
            + a5 * pressure * temperature_squared
        )
