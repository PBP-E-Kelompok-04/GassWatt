from django.urls import path

from main.views import(
    show_home,
    show_dashboard, show_dashboard_survey, show_dashboard_weather, show_dashboard_emission,
    search_location_api, fetch_weather_api, list_locations, save_location, update_location, activate_location, delete_location,
)

app_name = "main"

urlpatterns = [
    path("", show_home, name="show_home"),
    path("dashboard/", show_dashboard, name="show_dashboard"),
    path("dashboard/survey/", show_dashboard_survey, name="show_dashboard_survey"),

    path("dashboard/weather/", show_dashboard_weather, name="show_dashboard_weather"),
    path("api/search-location/", search_location_api, name="search_location_api"),
    path("api/fetch-weather/", fetch_weather_api, name="fetch_weather_api"),
    path("api/locations/", list_locations, name="list_locations"),
    path("api/save-location/", save_location, name="save_location"),
    path("api/locations/<int:location_id>/update/", update_location, name="update_location"),
    path("api/locations/<int:location_id>/activate/", activate_location, name="activate_location"),
    path("api/locations/<int:location_id>/delete/", delete_location, name="delete_location"),
    
    path("dashboard/emission/", show_dashboard_emission, name="show_dashboard_emission"),
]