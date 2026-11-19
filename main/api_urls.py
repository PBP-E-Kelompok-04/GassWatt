from django.urls import path
from main.views import api_views

app_name = "api"
urlpatterns = [
    path("emissions/chart/", api_views.emission_chart, name="emission-chart"),
    path("emissions/dashboard/", api_views.emission_dashboard_data, name="emission-dashboard",),
    path("recommendations/", api_views.dashboard_recommendations, name="recommendations"),
    path("targets/weekly/", api_views.weekly_target, name="weekly-target"),
    path("transportations/", api_views.transportation_list, name="transportation-list"),
    path("transportations/<uuid:survey_id>/", api_views.transportation_detail, name="transportation-detail"),
    path("api/transportation/<uuid:survey_id>/", api_views.transportation_detail, name="api_transportation_detail"),
]