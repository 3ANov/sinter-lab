from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

app_name = "experiments"
urlpatterns = [
    path("login/", LoginView.as_view(template_name="experiments/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", views.index, name="index"),
    path("export/", views.export_excel, name="export_excel"),
]
