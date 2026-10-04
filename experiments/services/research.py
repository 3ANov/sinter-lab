from decimal import Decimal, localcontext
from time import perf_counter
import tracemalloc
from threading import Lock

from ..models import ComputationRun
from .calculation import calculate_density, OPERATIONS_PER_EVALUATION

_measurement_lock = Lock()


def axis_values(low, high, step):
    low, high, step = map(Decimal, (low, high, step))
    if step <= 0 or high <= low or (high - low) / step > 1000:
        raise ValueError('Некорректный диапазон или слишком маленький шаг.')
    values = [low + i * step for i in range(int((high - low) // step) + 1)]
    if values[-1] != high:
        values.append(high)
    return values


def calculate_experiment(experiment):
    experiment.full_clean()
    params = {name: str(getattr(experiment, name)) for name in (
        'pressure_min', 'pressure_max', 'pressure_step', 'temperature_min', 'temperature_max', 'temperature_step')}
    pressures = axis_values(experiment.pressure_min, experiment.pressure_max, experiment.pressure_step)
    temperatures = axis_values(experiment.temperature_min, experiment.temperature_max, experiment.temperature_step)
    pressure_levels = [pressures[0], (pressures[0] + pressures[-1]) / 2, pressures[-1]]
    temperature_levels = [temperatures[0], (temperatures[0] + temperatures[-1]) / 2, temperatures[-1]]
    points = sorted({(p, t) for p in pressures for t in temperature_levels} |
                    {(p, t) for p in pressure_levels for t in temperatures})
    with _measurement_lock:
        owned_trace = not tracemalloc.is_tracing()
        if owned_trace:
            tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]
        started = perf_counter()
        try:
            rows = [(p, t, calculate_density(p, t, experiment.coefficient_snapshot)) for p, t in points]
            elapsed = perf_counter() - started
            memory = max(0, tracemalloc.get_traced_memory()[1] - baseline)
        finally:
            if owned_trace:
                tracemalloc.stop()
    with localcontext() as context:
        context.prec = 64
        results = [{'pressure': str(p), 'temperature': str(t),
                    'density': str(d.quantize(Decimal('0.000000000001')))} for p, t, d in rows]
    return ComputationRun.objects.create(
        experiment=experiment, input_snapshot={**params, 'coefficients': experiment.coefficient_snapshot,
        'material': experiment.material_name_snapshot, 'title': experiment.title},
        results=results, computation_seconds=elapsed, peak_memory_bytes=memory,
        operations_per_evaluation=OPERATIONS_PER_EVALUATION)


def result_sections(run):
    rows = run.results
    data = run.input_snapshot
    sections = []
    for axis, fixed, label, unit in [('pressure', 'temperature', 'Давление', 'атм'),
                                      ('temperature', 'pressure', 'Температура', '°C')]:
        low, high = Decimal(data[f'{fixed}_min']), Decimal(data[f'{fixed}_max'])
        levels = [low, (low + high) / 2, high]
        xs = axis_values(data[f'{axis}_min'], data[f'{axis}_max'], data[f'{axis}_step'])
        lookup = {(Decimal(row[axis]), Decimal(row[fixed])): Decimal(row['density']) for row in rows}
        sections.append({'axis': axis, 'label': label, 'unit': unit, 'levels': levels,
                         'fixed_label': 'T, °C' if fixed == 'temperature' else 'Pg, атм',
                         'rows': [(x, [lookup[(x, level)] for level in levels]) for x in xs]})
    return sections
