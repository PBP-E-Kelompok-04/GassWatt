from django.urls import path

from main.views import(
    show_home,
    show_dashboard, show_dashboard_survey, show_dashboard_weather, show_dashboard_emission,
)

app_name = "main"

urlpatterns = [
    path("", show_home, name="show_home"),
    path("dashboard/", show_dashboard, name="show_dashboard"),
    path("dashboard/survey/", show_dashboard_survey, name="show_dashboard_survey"),
    path("dashboard/weather/", show_dashboard_weather, name="show_dashboard_weather"),
    path("dashboard/emission/", show_dashboard_emission, name="show_dashboard_emission"),
]