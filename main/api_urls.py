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
    path("electricity/", api_views.electricity_list, name="electricity-list"),
    path("electricity/<uuid:survey_id>/", api_views.electricity_detail, name="electricity-detail"),
    path("reusable/", api_views.reusable_list, name="reusable-list"),
    path("reusable/<uuid:survey_id>/", api_views.reusable_detail, name="reusable-detail"),
    path("faq/", api_views.faq_list, name="faq-list"),
    path("faq/<uuid:faq_id>/", api_views.faq_detail, name="faq-detail"),
]