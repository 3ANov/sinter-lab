from time import perf_counter

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
import plotly.graph_objects as go

from .forms import ExperimentForm
from .models import ComputationRun
from .services.excel import build_excel
from .services.research import calculate_experiment, result_sections


def visible_runs(user):
    runs = ComputationRun.objects.select_related('experiment', 'experiment__researcher')
    return runs if user.is_staff else runs.filter(experiment__researcher=user)


@login_required
def index(request):
    form = ExperimentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                experiment = form.save(commit=False)
                experiment.researcher = request.user
                experiment.save()
                run = calculate_experiment(experiment)
            return redirect('experiments:results', pk=run.pk)
        except (ValidationError, ValueError) as error:
            form.add_error(None, 'Не удалось выполнить расчёт: ' + str(error))
    return render(request, 'experiments/experiment.html', {
        'form': form, 'runs': visible_runs(request.user).order_by('-created_at')[:20]})


@login_required
def results(request, pk):
    run = get_object_or_404(visible_runs(request.user), pk=pk)
    sections = result_sections(run)
    started = perf_counter()
    for index, section in enumerate(sections):
        figure = go.Figure()
        for column, level in enumerate(section['levels']):
            figure.add_trace(go.Scatter(x=[float(x) for x, _ in section['rows']],
                y=[float(values[column]) for _, values in section['rows']],
                mode='lines+markers', name=f"{section['fixed_label']}: {level.normalize():f}"))
        figure.update_layout(template='plotly_white', xaxis_title=f"{section['label']}, {section['unit']}",
                             yaxis_title='Плотность, г/см³', margin=dict(l=60, r=20, t=30, b=60))
        section['chart'] = figure.to_html(full_html=False, include_plotlyjs=index == 0,
                                          config={'responsive': True, 'displaylogo': False})
    elapsed = perf_counter() - started
    if run.visualization_seconds is None:
        ComputationRun.objects.filter(pk=run.pk, visualization_seconds__isnull=True).update(visualization_seconds=elapsed)
        run.refresh_from_db()
    return render(request, 'experiments/results.html', {'run': run, 'sections': sections})


@login_required
def export_excel(request, pk):
    run = get_object_or_404(visible_runs(request.user), pk=pk)
    response = HttpResponse(build_excel(run), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="sinter-lab-{run.pk}.xlsx"'
    return response
