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
    path("faq/<int:faq_id>/", api_views.faq_detail, name="faq-detail"),

    path("weather/search/", api_views.weather_search, name="weather-search"),
    path("weather/current/", api_views.weather_current, name="weather-current"),
    path("weather/locations/", api_views.weather_location_list, name="weather-location-list"),
    path("weather/locations/<int:location_id>/", api_views.weather_location_detail, name="weather-location-detail"),
    path("weather/locations/<int:location_id>/activate/", api_views.weather_location_activate, name="weather-location-activate"),

    path("admin/dashboard/", api_views.admin_dashboard_summary, name="admin-dashboard"),
    path("admin/users/", api_views.admin_user_list, name="admin-user-list"),
    path("admin/users/<int:user_id>/", api_views.admin_user_delete, name="admin-user-delete"),
    path("admin/faq/", api_views.admin_faq_list, name="admin-faq-list"),
    path("admin/faq/<int:faq_id>/", api_views.admin_faq_detail, name="admin-faq-detail"),

    path("sessions/", views.SessionAPI.as_view(), name="sessions"),            # POST login, DELETE logout
    path("users/", views.UsersAPI.as_view(), name="users"),                    # POST register
    path("users/me/", views.MeAPI.as_view(), name="me"),                       # GET, PATCH, DELETE
    path("users/me/password/", views.PasswordAPI.as_view(), name="password"),  # PUT
    path("validate-field/", views.ValidateFieldAPI.as_view(), name="validate_field"),
]