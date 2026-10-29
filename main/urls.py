from django.urls import path

from main.views.views import (
    show_dashboard, show_dashboard_survey, show_dashboard_weather, 
    survey_transport_list_json, add_transport_survey, edit_transport_survey, delete_transport_survey,
    survey_electricity_list_json, add_electricity_survey, edit_electricity_survey, delete_electricity_survey,
    survey_reusable_list_json, add_reusable_survey, edit_reusable_survey, delete_reusable_survey,
    emission_dashboard, emission_chart_api, daily_energy_chart_api,
    admin_dashboard, kelola_pengguna, delete_user, kelola_faq, add_faq, edit_faq, delete_faq,
    search_location_api, fetch_weather_api, list_locations, 
    save_location, update_location, activate_location, delete_location,
)

from main.views.view_main import (
    show_home, show_faq, show_about,
)

from main.views.view_auth import (
    show_login, login_user, show_register, register_user, logout_user,
)

app_name = "main"

urlpatterns = [
    # Main
    path("", show_home, name="show_home"),
    path("faq/", show_faq, name="show_faq"),
    path("about/", show_about, name="show_about"),

    # Auth
    path("login/", show_login, name="show_login"),
    path("login/submit/", login_user, name="login_user"),
    path("register/", show_register, name="show_register"),
    path("register/submit/", register_user, name="register_user"),
    path("logout/", logout_user, name="logout_user"),

    # Dashboard
    path("dashboard/", show_dashboard, name="show_dashboard"),
    path("dashboard/survey/", show_dashboard_survey, name="show_dashboard_survey"),
    path('dashboard/emission/', emission_dashboard, name='emission_dashboard'),
    path("dashboard/weather/", show_dashboard_weather, name="show_dashboard_weather"),

    # Survey: electricity
    path("dashboard/survey/electricity/list/", survey_electricity_list_json, name="survey_electricity_list_json"),
    path('dashboard/survey/electricity/add/', add_electricity_survey, name='add_electricity_survey'),
    path('dashboard/survey/electricity/edit/<uuid:survey_id>/', edit_electricity_survey, name='edit_electricity_survey'),
    path('dashboard/survey/electricity/delete/<uuid:survey_id>/', delete_electricity_survey, name='delete_electricity_survey'),

     # Survey: reusable
    path("dashboard/survey/reusable/list/", survey_reusable_list_json, name="survey_reusable_list_json"),
    path("dashboard/survey/reusable/add/", add_reusable_survey, name="add_reusable_survey"),
    path("dashboard/survey/reusable/edit/<uuid:survey_id>/", edit_reusable_survey, name="edit_reusable_survey"),
    path("dashboard/survey/reusable/delete/<uuid:survey_id>/", delete_reusable_survey, name="delete_reusable_survey"),

    # Charts API
    path('api/emission-chart/', emission_chart_api, name='api_emission_chart'),
    path('api/daily-energy-chart/', daily_energy_chart_api, name='daily_energy_chart_api'),

    # Weather / locations API
    path("api/search-location/", search_location_api, name="search_location_api"),
    path("api/fetch-weather/", fetch_weather_api, name="fetch_weather_api"),
    path("api/locations/", list_locations, name="list_locations"),
    path("api/save-location/", save_location, name="save_location"),
    path("api/locations/<int:location_id>/update/", update_location, name="update_location"),
    path("api/locations/<int:location_id>/activate/", activate_location, name="activate_location"),
    path("api/locations/<int:location_id>/delete/", delete_location, name="delete_location"),

    # Admin portal
    path('admin-portal/', admin_dashboard, name='admin_dashboard'),
    path('admin-portal/pengguna/', kelola_pengguna, name='kelola_pengguna'),
    path('admin-portal/<int:user_id>/delete/', delete_user, name='delete_user'),
    path('admin-portal/faq/', kelola_faq, name='kelola_faq'),
    path('admin-portal/faq/add/', add_faq, name='add_faq'),
    path('admin-portal/<int:faq_id>/edit/', edit_faq, name='edit_faq'),
    path('admin-portal/<int:faq_id>/delete/', delete_faq, name='delete_faq'),
]