from .view_main import (
    show_home,
    show_faq,
    show_about,
    get_faq_json,
)
from .view_auth import (
    show_login,
    login_user,
    show_register,
    register_user,
    logout_user,
    validate_field
)
from .view_dashboard import (
    get_weekly_target_summary,
    show_dashboard,
    show_dashboard_weather,
    _sync_daily_emission_logs,
    emission_dashboard,
    emission_chart_api,
    daily_energy_chart_api,
    search_location_api,
    fetch_weather_api,
    serialize_locations,
    list_locations,
    save_location,
    update_location,
    activate_location,
    delete_location,
)
from .view_survey import (
    show_dashboard_survey,
    survey_transport_list_json,
    add_transport_survey,
    edit_transport_survey,
    delete_transport_survey,
    survey_electricity_list_json,
    add_electricity_survey,
    edit_electricity_survey,
    delete_electricity_survey,
    survey_reusable_list_json,
    add_reusable_survey,
    edit_reusable_survey,
    delete_reusable_survey,
)
from .view_admin import (
    admin_dashboard,
    kelola_pengguna,
    delete_user,
    kelola_faq,
    add_faq,
    edit_faq,
    delete_faq,
)
from .view_decorators import (
    _is_admin,
)