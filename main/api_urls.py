from django.urls import path
from main.views import api_views

app_name = "api"
urlpatterns = [
    path("transportations/", api_views.transportation_list, name="transportation-list"),
    path("transportations/<uuid:survey_id>/", api_views.transportation_detail, name="transportation-detail"),
    path("api/transportation/<uuid:survey_id>/", api_views.transportation_detail, name="api_transportation_detail"),
]