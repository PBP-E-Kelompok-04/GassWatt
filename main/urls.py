from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    # Main
    path("", views.show_home, name="show_home"),
    path("faq/", views.show_faq, name="show_faq"),
    path("about/", views.show_about, name="show_about"),

    # Auth
    path("login/", views.show_login, name="show_login"),
    path("login/submit/", views.login_user, name="login_user"),
    path("register/", views.show_register, name="show_register"),
    path("register/submit/", views.register_user, name="register_user"),
    path("logout/", views.logout_user, name="logout_user"),

    # Dashboard
    path("dashboard/", views.show_dashboard, name="show_dashboard"),
    path("dashboard/survey/", views.show_dashboard_survey, name="show_dashboard_survey"),
    path("dashboard/emission/", views.emission_dashboard, name="emission_dashboard"),
    path("dashboard/weather/", views.show_dashboard_weather, name="show_dashboard_weather"),

     # Survey: transport
    path("dashboard/survey/transport/list/", views.survey_transport_list_json, name="survey_transport_list_json"),
    path("dashboard/survey/transport/add/", views.add_transport_survey, name="add_transport_survey"),
    path("dashboard/survey/transport/edit/<uuid:survey_id>/", views.edit_transport_survey, name="edit_transport_survey"),
    path("dashboard/survey/transport/delete/<uuid:survey_id>/", views.delete_transport_survey, name="delete_transport_survey"),

    # Survey: electricity
    path("dashboard/survey/electricity/list/", views.survey_electricity_list_json, name="survey_electricity_list_json"),
    path("dashboard/survey/electricity/add/", views.add_electricity_survey, name="add_electricity_survey"),
    path("dashboard/survey/electricity/edit/<uuid:survey_id>/", views.edit_electricity_survey, name="edit_electricity_survey"),
    path("dashboard/survey/electricity/delete/<uuid:survey_id>/", views.delete_electricity_survey, name="delete_electricity_survey"),

    # Survey: reusable
    path("dashboard/survey/reusable/list/", views.survey_reusable_list_json, name="survey_reusable_list_json"),
    path("dashboard/survey/reusable/add/", views.add_reusable_survey, name="add_reusable_survey"),
    path("dashboard/survey/reusable/edit/<uuid:survey_id>/", views.edit_reusable_survey, name="edit_reusable_survey"),
    path("dashboard/survey/reusable/delete/<uuid:survey_id>/", views.delete_reusable_survey, name="delete_reusable_survey"),

    # Charts API
    path("api/emission-chart/", views.emission_chart_api, name="api_emission_chart"),
    path("api/daily-energy-chart/", views.daily_energy_chart_api, name="daily_energy_chart_api"),

    # Weather / locations API
    path("api/search-location/", views.search_location_api, name="search_location_api"),
    path("api/fetch-weather/", views.fetch_weather_api, name="fetch_weather_api"),
    path("api/locations/", views.list_locations, name="list_locations"),
    path("api/save-location/", views.save_location, name="save_location"),
    path("api/locations/<int:location_id>/update/", views.update_location, name="update_location"),
    path("api/locations/<int:location_id>/activate/", views.activate_location, name="activate_location"),
    path("api/locations/<int:location_id>/delete/", views.delete_location, name="delete_location"),

    # Admin portal
    path("admin-portal/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-portal/pengguna/", views.kelola_pengguna, name="kelola_pengguna"),
    path("admin-portal/<int:user_id>/delete/", views.delete_user, name="delete_user"),
    path("admin-portal/faq/", views.kelola_faq, name="kelola_faq"),
    path("admin-portal/faq/add/", views.add_faq, name="add_faq"),
    path("admin-portal/<int:faq_id>/edit/", views.edit_faq, name="edit_faq"),
    path("admin-portal/<int:faq_id>/delete/", views.delete_faq, name="delete_faq"),
]