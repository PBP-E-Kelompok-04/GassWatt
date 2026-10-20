from django.urls import path

from main.views import(
    show_home,
    show_dashboard, 
    show_dashboard_survey, 
    show_dashboard_weather, 
    show_dashboard_emission, 
    add_transport_survey,
    edit_transport_survey,
    delete_transport_survey,
    emission_dashboard,
)

app_name = "main"

urlpatterns = [
    path("", show_home, name="show_home"),
    path("dashboard/", show_dashboard, name="show_dashboard"),
    # path("dashboard/survey/", show_dashboard_survey, name="show_dashboard_survey"),
    path('dashboard/survey/add/', add_transport_survey, name='add_transport_survey'),
    path('dashboard/survey/edit/<uuid:survey_id>/', edit_transport_survey, name='edit_transport_survey'),
    path('dashboard/survey/delete/<uuid:survey_id>/', delete_transport_survey, name='delete_transport_survey'),
    path('dashboard/emission/', emission_dashboard, name='emission_dashboard'),
    path("dashboard/weather/", show_dashboard_weather, name="show_dashboard_weather"),
    # path("dashboard/emission/", show_dashboard_emission, name="show_dashboard_emission"),
]