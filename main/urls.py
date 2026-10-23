from django.urls import path

from main.views import(
    show_home,
    show_dashboard, 
    show_dashboard_survey, 
    show_dashboard_weather, 
    survey_transport_list_json,
    add_transport_survey,
    edit_transport_survey,
    delete_transport_survey,
    emission_dashboard,
    show_faq,
    show_about,
    search_location_api, 
    fetch_weather_api, 
    list_locations, 
    save_location, 
    update_location, 
    activate_location, 
    delete_location,
)

app_name = "main"

urlpatterns = [
    path("", show_home, name="show_home"),
    path("dashboard/", show_dashboard, name="show_dashboard"),
    path("dashboard/survey/", show_dashboard_survey, name="show_dashboard_survey"),
    path("dashboard/survey/list/", survey_transport_list_json, name="survey_transport_list_json"),
    path('dashboard/survey/add/', add_transport_survey, name='add_transport_survey'),
    path('dashboard/survey/edit/<uuid:survey_id>/', edit_transport_survey, name='edit_transport_survey'),
    path('dashboard/survey/delete/<uuid:survey_id>/', delete_transport_survey, name='delete_transport_survey'),
    path('dashboard/emission/', emission_dashboard, name='emission_dashboard'),

    path("dashboard/weather/", show_dashboard_weather, name="show_dashboard_weather"),
    path("api/search-location/", search_location_api, name="search_location_api"),
    path("api/fetch-weather/", fetch_weather_api, name="fetch_weather_api"),
    path("api/locations/", list_locations, name="list_locations"),
    path("api/save-location/", save_location, name="save_location"),
    path("api/locations/<int:location_id>/update/", update_location, name="update_location"),
    path("api/locations/<int:location_id>/activate/", activate_location, name="activate_location"),
    path("api/locations/<int:location_id>/delete/", delete_location, name="delete_location"),
    
    # path("dashboard/emission/", show_dashboard_emission, name="show_dashboard_emission"),
    path("faq/", show_faq, name="show_faq"),
    path("about/", show_about, name="show_about"),
]