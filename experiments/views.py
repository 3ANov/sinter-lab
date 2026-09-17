from django.http import HttpResponse
from django.shortcuts import render
import plotly.graph_objects as go

from .services.excel import build_excel


# Demonstration data; replace with application models when the domain is defined.
DEMO_ROWS = [(0, 20), (10, 200), (20, 450), (30, 700), (40, 950), (50, 1100)]


def index(request):
    figure = go.Figure(go.Scatter(
        x=[row[0] for row in DEMO_ROWS],
        y=[row[1] for row in DEMO_ROWS],
        mode="lines+markers",
        line={"color": "#0d6efd", "width": 3},
    ))
    figure.update_layout(
        template="plotly_white", xaxis_title="Время, мин",
        yaxis_title="Температура, °C", margin={"l": 60, "r": 20, "t": 20, "b": 60},
    )
    return render(request, "experiments/experiment.html", {
        "chart": figure.to_html(full_html=False, include_plotlyjs=True,
                                config={"responsive": True, "displaylogo": False}),
        "rows": DEMO_ROWS,
    })


def export_excel(request):
    response = HttpResponse(build_excel(DEMO_ROWS), content_type=(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ))
    response["Content-Disposition"] = 'attachment; filename="sinter-lab-demo.xlsx"'
    return response
