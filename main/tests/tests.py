from datetime import timedelta
from unittest.mock import patch

import requests, re, json
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings, RequestFactory
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse


from ..models.model_survey import (
    TransportationSurvey,
    SavedLocation,
    ElectricitySurvey,
    ReusableItemSurvey,
    DailyEmissionLog,
    FAQ,
)
from ..views import get_weekly_target_summary, view_admin

from .. import weather_logic
from ..forms import LocationForm, LocationRenameForm, ElectricitySurveyForm

User = get_user_model()

# Membuat user
def make_user(username, password=None):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
    )


class TransportationSurveyFlowTests(TestCase):
    def setUp(self):
        self.user = make_user("survey-user", "test-password")
        self.client.force_login(self.user)

    def test_survey_page_renders_form_and_ajax_urls(self):
        response = self.client.get(reverse("main:show_dashboard_survey"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="transport_mode"')
        self.assertContains(response, 'name="daily_distance_km"')
        self.assertContains(response, 'data-list-url="/dashboard/survey/transport/list/"')

    def test_transport_survey_crud_and_list(self):
        add_response = self.client.post(
            reverse("main:add_transport_survey"),
            {
                "transport_mode": "motor_ice",
                "daily_distance_km": "12.5",
                "notes": "Rumah ke kantor",
            },
        )

        self.assertEqual(add_response.status_code, 201)
        survey_id = str(TransportationSurvey.objects.get(user=self.user).id)

        list_response = self.client.get(reverse("main:survey_transport_list_json"))
        self.assertEqual(list_response.status_code, 200)
        survey_data = list_response.json()["data"][0]
        self.assertEqual(survey_data["id"], survey_id)
        self.assertEqual(survey_data["mode"], "Motor Bensin (ICE)")
        self.assertEqual(survey_data["mode_val"], "motor_ice")
        self.assertEqual(survey_data["distance"], 12.5)
        self.assertEqual(survey_data["notes"], "Rumah ke kantor")
        self.assertEqual(survey_data["daily_emission_co2"], 1.12)

        edit_response = self.client.post(
            reverse("main:edit_transport_survey", args=[survey_id]),
            {
                "transport_mode": "car_ev",
                "daily_distance_km": "10",
                "notes": "",
            },
        )
        self.assertEqual(edit_response.status_code, 200)
        updated_data = self.client.get(
            reverse("main:survey_transport_list_json")
        ).json()["data"][0]
        self.assertEqual(updated_data["mode_val"], "car_ev")
        self.assertEqual(updated_data["notes"], "")

        delete_response = self.client.post(
            reverse("main:delete_transport_survey", args=[survey_id])
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(
            self.client.get(reverse("main:survey_transport_list_json")).json()["data"],
            [],
        )

    def test_transport_survey_invalid_input_returns_validation_errors(self):
        response = self.client.post(
            reverse("main:add_transport_survey"),
            {
                "transport_mode": "spaceship",
                "daily_distance_km": "not-a-number",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("transport_mode", response.json()["errors"])
        self.assertIn("daily_distance_km", response.json()["errors"])
        self.assertFalse(TransportationSurvey.objects.filter(user=self.user).exists())

    def test_transport_survey_rejects_unsupported_methods(self):
        add_url = reverse("main:add_transport_survey")
        list_url = reverse("main:survey_transport_list_json")

        self.assertEqual(self.client.get(add_url).status_code, 405)
        self.assertEqual(self.client.post(list_url).status_code, 405)

        survey = TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="motor_ice",
            daily_distance_km=5,
        )
        self.assertEqual(
            self.client.get(
                reverse("main:edit_transport_survey", args=[survey.id])
            ).status_code,
            405,
        )
        self.assertEqual(
            self.client.get(
                reverse("main:delete_transport_survey", args=[survey.id])
            ).status_code,
            405,
        )
        self.assertTrue(
            TransportationSurvey.objects.filter(pk=survey.id, user=self.user).exists()
        )

    def test_transport_survey_cannot_be_accessed_or_changed_by_another_user(self):
        other_user = make_user("other-transport-user")
        survey = TransportationSurvey.objects.create(
            user=other_user,
            transport_mode="motor_ice",
            daily_distance_km=5,
        )
        edit_url = reverse("main:edit_transport_survey", args=[survey.id])
        delete_url = reverse("main:delete_transport_survey", args=[survey.id])

        self.assertEqual(
            self.client.get(reverse("main:survey_transport_list_json")).json()["data"],
            [],
        )
        self.assertEqual(self.client.post(edit_url, {
            "transport_mode": "car_ev",
            "daily_distance_km": "10",
        }).status_code, 404)
        self.assertEqual(self.client.post(delete_url).status_code, 404)

        survey.refresh_from_db()
        self.assertEqual(survey.transport_mode, "motor_ice")
        self.assertEqual(float(survey.daily_distance_km), 5)

    def test_dashboard_pages_and_transport_list_require_login(self):
        protected_urls = (
            reverse("main:show_dashboard"),
            reverse("main:show_dashboard_survey"),
            reverse("main:emission_dashboard"),
            reverse("main:survey_transport_list_json"),
        )
        self.client.logout()

        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)

    def test_survey_and_emission_pages_require_login_and_render(self):
        self.client.logout()
        response = self.client.get(reverse("main:show_dashboard_survey"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.user)
        emission_response = self.client.get(reverse("main:emission_dashboard"))
        self.assertEqual(emission_response.status_code, 200)


class EmissionDashboardTests(TestCase):
    def setUp(self):
        self.user = make_user("emission-dashboard-user")
        self.client.force_login(self.user)
        self.url = reverse("main:emission_dashboard")
        self.today = timezone.now().date()

    def test_dashboard_with_no_surveys_returns_zero_metrics_and_default_score(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["today_emission"], 0)
        self.assertEqual(response.context["total_7days_emission"], 0)
        self.assertEqual(response.context["co2_saved"], 0)
        self.assertIsNone(response.context["eco_score"])
        self.assertContains(response, "Belum ada data")
        self.assertEqual(response.context["trees_saved"], 0)
        self.assertEqual(response.context["avoided_km"], 0)
        self.assertEqual(response.context["transport_emission_today"], 0)
        self.assertEqual(response.context["electricity_emission_today"], 0)
        self.assertEqual(response.context["reusable_emission_saved_today"], 0)

    def test_dashboard_calculates_emissions_savings_score_and_impacts(self):
        DailyEmissionLog.objects.create(
            user=self.user,
            date=self.today - timedelta(days=6),
            total_emission_co2=2,
        )
        DailyEmissionLog.objects.create(
            user=self.user,
            date=self.today - timedelta(days=8),
            total_emission_co2=100,
        )
        TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="busway",
            daily_distance_km=10,
        )
        TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="motor_ice",
            daily_distance_km=2,
        )
        ElectricitySurvey.objects.create(
            user=self.user,
            device_type="laptop",
            quantity=1,
            power_watts=100,
            daily_usage_hours=5,
        )
        ReusableItemSurvey.objects.create(
            user=self.user,
            item_type="botol_minum",
            quantity=1,
            uses_per_week=7,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["today_emission"], 1.42)
        self.assertEqual(response.context["total_7days_emission"], 13.42)
        self.assertEqual(response.context["co2_saved"], 8.47)
        self.assertEqual(response.context["eco_score"], 58)
        self.assertEqual(response.context["trees_saved"], 24)
        self.assertEqual(response.context["avoided_km"], 70)
        self.assertEqual(response.context["transport_emission_today"], 1.07)
        self.assertEqual(response.context["electricity_emission_today"], 0.36)
        self.assertEqual(response.context["reusable_emission_saved_today"], 0.01)

    def test_dashboard_clamps_score_and_savings_at_zero(self):
        TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="car_ice",
            daily_distance_km=10,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.context["eco_score"], 0)
        self.assertEqual(response.context["co2_saved"], 0)
        self.assertEqual(response.context["avoided_km"], 0)

    def test_dashboard_rejects_non_get_methods(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    def test_dashboard_metrics_only_include_the_authenticated_users_surveys(self):
        other_user = make_user("other-emission-user")
        TransportationSurvey.objects.create(
            user=other_user,
            transport_mode="car_ice",
            daily_distance_km=100,
        )
        ElectricitySurvey.objects.create(
            user=other_user,
            device_type="desktop",
            quantity=1,
            power_watts=1000,
            daily_usage_hours=24,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["transport_emission_today"], 0)
        self.assertEqual(response.context["electricity_emission_today"], 0)
        self.assertEqual(response.context["today_emission"], 0)


class WeeklyTargetTests(TestCase):
    def setUp(self):
        self.user = make_user("weekly-target-user")
        self.client.force_login(self.user)
        self.today = timezone.now().date()

    def create_week_logs(self, start_days_ago, end_days_ago, value):
        DailyEmissionLog.objects.bulk_create([
            DailyEmissionLog(
                user=self.user,
                date=self.today - timedelta(days=days_ago),
                total_emission_co2=value,
            )
            for days_ago in range(start_days_ago, end_days_ago - 1, -1)
        ])

    def test_weekly_target_compares_two_exact_seven_day_periods(self):
        self.create_week_logs(13, 7, 10)
        self.create_week_logs(6, 0, 8)
        DailyEmissionLog.objects.create(
            user=self.user,
            date=self.today - timedelta(days=14),
            total_emission_co2=100,
        )

        target = get_weekly_target_summary(self.user)

        self.assertEqual(target["co2_reduced_kg"], 14)
        self.assertEqual(target["actual_reduction_pct"], 20)
        self.assertTrue(target["is_achieved"])
        self.assertTrue(target["has_baseline"])

    def test_dashboard_updates_target_after_survey_edit(self):
        self.create_week_logs(13, 7, 1)
        self.create_week_logs(6, 0, 1)
        survey = TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="motor_ice",
            daily_distance_km=5,
        )

        before_edit = self.client.get(reverse("main:show_dashboard"))
        before_progress = before_edit.context["target_data"]["actual_reduction_pct"]

        edit_response = self.client.post(
            reverse("main:edit_transport_survey", args=[survey.id]),
            {
                "transport_mode": "motor_ice",
                "daily_distance_km": "10",
                "notes": "",
            },
        )
        self.assertEqual(edit_response.status_code, 200)

        after_edit = self.client.get(reverse("main:show_dashboard"))
        after_progress = after_edit.context["target_data"]["actual_reduction_pct"]

        self.assertLess(after_progress, before_progress)


class MainDashboardTests(TestCase):
    def setUp(self):
        self.user = make_user("main-dashboard-user")
        self.client.force_login(self.user)
        self.today = timezone.now().date()
        self.url = reverse("main:show_dashboard")

    def create_week(self, start_days_ago, end_days_ago, value):
        DailyEmissionLog.objects.bulk_create([
            DailyEmissionLog(
                user=self.user,
                date=self.today - timedelta(days=days_ago),
                total_emission_co2=value,
            )
            for days_ago in range(start_days_ago, end_days_ago - 1, -1)
        ])

    def test_dashboard_explains_missing_weekly_baseline(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["target_data"]["has_baseline"])
        self.assertEqual(response.context["target_data"]["actual_reduction_pct"], 0)
        self.assertIn(
            "Belum ada data emisi minggu lalu",
            response.context["recommendations"][0],
        )

    def test_dashboard_reports_achieved_weekly_target(self):
        self.create_week(13, 7, 10)
        self.create_week(6, 0, 10)

        response = self.client.get(self.url)

        self.assertTrue(response.context["target_data"]["has_baseline"])
        self.assertTrue(response.context["target_data"]["is_achieved"])
        self.assertIn(
            "Target minggu ini telah tercapai",
            response.context["recommendations"][0],
        )

    def test_dashboard_reports_partial_and_negative_weekly_reduction(self):
        self.create_week(13, 7, 10)
        self.create_week(6, 1, 10)

        TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="motor_ice",
            daily_distance_km=72.22,
        )
        partial_response = self.client.get(self.url)

        self.assertAlmostEqual(
            partial_response.context["target_data"]["actual_reduction_pct"],
            5,
        )
        self.assertIn(
            "Sedikit lagi!",
            partial_response.context["recommendations"][0],
        )

        survey = TransportationSurvey.objects.get(user=self.user)
        survey.daily_distance_km = 122.23
        survey.save()
        higher_emission_response = self.client.get(self.url)

        self.assertLess(
            higher_emission_response.context["target_data"]["actual_reduction_pct"],
            0,
        )
        self.assertIn(
            "Emisi masih lebih tinggi dari minggu lalu",
            higher_emission_response.context["recommendations"][0],
        )

    def test_dashboard_recommends_actions_from_transport_energy_and_reusable_surveys(self):
        TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="car_ice",
            daily_distance_km=1,
        )
        TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="car_ice",
            daily_distance_km=12,
        )
        TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="motor_ice",
            daily_distance_km=5,
        )
        ElectricitySurvey.objects.create(
            user=self.user,
            device_type="ac",
            quantity=1,
            power_watts=1000,
            daily_usage_hours=8,
        )
        ElectricitySurvey.objects.create(
            user=self.user,
            device_type="desktop",
            quantity=1,
            power_watts=600,
            daily_usage_hours=4,
        )
        ElectricitySurvey.objects.create(
            user=self.user,
            device_type="lamp",
            quantity=3,
            power_watts=10,
            daily_usage_hours=5,
        )
        ElectricitySurvey.objects.create(
            user=self.user,
            device_type="television",
            quantity=1,
            power_watts=100,
            daily_usage_hours=12,
        )
        ReusableItemSurvey.objects.create(
            user=self.user,
            item_type="botol_minum",
            quantity=1,
            uses_per_week=2,
        )
        ReusableItemSurvey.objects.create(
            user=self.user,
            item_type="tote_bag",
            quantity=2,
            uses_per_week=4,
        )

        response = self.client.get(self.url)
        recommendations = response.context["recommendations"]

        self.assertEqual(response.status_code, 200)
        for expected_text in (
            "tergolong dekat",
            "menghasilkan emisi cukup tinggi",
            "Motor bensin",
            "Penggunaan AC",
            "menggunakan daya besar",
            "unit lampu",
            "menyala selama 12 jam/hari",
            "hanya 2 kali seminggu",
            "Gunakan sesering mungkin",
        ):
            self.assertTrue(
                any(expected_text.lower() in item.lower() for item in recommendations)
            )

    def test_dashboard_rejects_non_get_methods(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    def test_recommendations_do_not_include_another_users_survey_data(self):
        other_user = make_user("other-recommendation-user")
        TransportationSurvey.objects.create(
            user=other_user,
            transport_mode="car_ice",
            daily_distance_km=1,
        )
        ElectricitySurvey.objects.create(
            user=other_user,
            device_type="ac",
            quantity=1,
            power_watts=1000,
            daily_usage_hours=10,
        )
        ReusableItemSurvey.objects.create(
            user=other_user,
            item_type="botol_minum",
            quantity=1,
            uses_per_week=1,
        )

        response = self.client.get(self.url)
        recommendations = response.context["recommendations"]

        self.assertFalse(any("tergolong dekat" in item for item in recommendations))
        self.assertFalse(any("Penggunaan AC" in item for item in recommendations))
        self.assertTrue(any("belum menggunakan Barang Reusable" in item for item in recommendations))


class WeatherFlowTests(TestCase):
    def setUp(self):
        self.user = make_user("weather-user", "test-password")
        self.other = make_user("other-weather", "test-password")

        self.client.force_login(self.user)
        cache.clear()
        self.forecast = {
            "timezone": "Asia/Jakarta",
            "current": {
                "time": "2026-10-22T14:00",
                "temperature_2m": 29,
                "relative_humidity_2m": 70,
                "precipitation": 0,
                "weather_code": 2,
                "is_day": 1,
                "wind_speed_10m": 12,
                "cloud_cover": 30,
                "precipitation_probability": 15,
                "uv_index": 4,
            },
        }
        self.air = {
            "current": {
                "time": "2026-10-22T14:00", "us_aqi": 55,
                "nitrogen_dioxide": 22.5, "us_aqi_nitrogen_dioxide": 12,
            },
            "current_units": {"nitrogen_dioxide": "µg/m³"},
        }

    def url(self, name, *args):
        return reverse(f"main:{name}", args=args)

    def mock_api(self, url, params):
        if url == weather_logic.FORECAST_URL:
            return self.forecast
        if url == weather_logic.AIR_QUALITY_URL:
            return self.air
        if url == weather_logic.GEOCODING_URL:
            return {"results": [{"name": "Depok", "admin1": "Jawa Barat",
                                "country": "Indonesia", "latitude": -6.4,
                                "longitude": 106.8}]}
        raise AssertionError(url)

    def test_page_and_api_require_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url("show_dashboard_weather")).status_code, 302)
        endpoints = [
            ("get", "search_location_api", (), {"q": "Depok"}),
            ("get", "fetch_weather_api", (), {"lat": -6.4, "lon": 106.8}),
            ("get", "list_locations", (), {}),
            ("post", "save_location", (), {}),
            ("post", "update_location", (1,), {}),
            ("post", "activate_location", (1,), {}),
            ("post", "delete_location", (1,), {}),
        ]
        for method, name, args, data in endpoints:
            response = getattr(self.client, method)(self.url(name, *args), data)
            self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(self.url("show_dashboard_weather"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="weatherRenameModal"')
        self.assertContains(response, 'id="weatherDeleteModal"')

    def test_location_crud_flow(self):
        first = self.client.post(self.url("save_location"), {
            "name": " Depok ", "latitude": -6.4, "longitude": 106.8,
        })
        self.assertEqual(first.status_code, 201)
        first_id = first.json()["location"]["id"]
        second = self.client.post(self.url("save_location"), {
            "name": "Jakarta", "latitude": -6.2, "longitude": 106.9,
        })
        self.assertEqual(second.status_code, 201)
        second_id = second.json()["location"]["id"]
        self.assertEqual(self.client.get(self.url("list_locations")).json()["results"][0]["name"], "Jakarta")
        self.assertEqual(SavedLocation.objects.filter(user=self.user, is_active=True).count(), 1)

        self.assertEqual(self.client.post(self.url("activate_location", first_id)).status_code, 200)
        self.assertTrue(SavedLocation.objects.get(pk=first_id).is_active)
        self.assertFalse(SavedLocation.objects.get(pk=second_id).is_active)
        updated = self.client.post(self.url("update_location", first_id), {"name": " Depok Baru "})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["location"]["name"], "Depok Baru")
        repeated = self.client.post(self.url("save_location"), {
            "name": "Depok", "latitude": -6.4, "longitude": 106.8,
        })
        self.assertEqual(repeated.status_code, 200)
        self.assertFalse(repeated.json()["created"])
        self.assertEqual(SavedLocation.objects.filter(user=self.user).count(), 2)

        deleted = self.client.post(self.url("delete_location", first_id))
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["was_active"])
        self.assertFalse(SavedLocation.objects.filter(pk=first_id).exists())

    def test_invalid_location_and_user_isolation(self):
        bad = {"name": "  ", "latitude": 100, "longitude": 200}
        self.assertEqual(self.client.post(self.url("save_location"), bad).status_code, 400)
        self.assertFalse(SavedLocation.objects.exists())
        own = SavedLocation.objects.create(user=self.user, name="Milik saya", latitude=-6.4, longitude=106.8)
        other = SavedLocation.objects.create(user=self.other, name="Rahasia", latitude=-6.2, longitude=106.9)
        self.assertIn("Milik saya", str(own))
        listed = self.client.get(self.url("list_locations")).json()["results"]
        self.assertEqual([item["id"] for item in listed], [own.id])
        for action in ("update_location", "activate_location", "delete_location"):
            response = self.client.post(
                self.url(action, other.id), {"name": "Bajak"}
            )
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.post(self.url("update_location", own.id), {"name": " "}).status_code, 400)
        for coords in ((91, 106), (-6, 181), ("nan", 106), ("inf", 106)):
            form = LocationForm(data={
                "name": "GPS",
                "latitude": coords[0],
                "longitude": coords[1],
            })
            self.assertFalse(form.is_valid())
        self.assertFalse(LocationRenameForm(data={"name": "  "}).is_valid())

    @patch("main.views.view_dashboard.search_locations")
    @patch("main.views.view_dashboard.get_weather")
    def test_api_search_weather_and_errors(self, mock_weather, mock_search):
        mock_search.return_value = [{"name": "Depok", "latitude": -6.4, "longitude": 106.8}]
        mock_weather.return_value = {"temperature": 29, "aqi": 55}
        self.assertEqual(self.client.get(self.url("search_location_api"), {"q": "Depok"}).status_code, 200)
        self.assertEqual(self.client.get(self.url("fetch_weather_api"), {"lat": -6.4, "lon": 106.8}).json()["temperature"], 29)
        self.assertEqual(self.client.get(self.url("search_location_api"), {"q": "a"}).json(), {"results": []})
        self.assertEqual(self.client.get(self.url("search_location_api"), {"q": "x" * 101}).status_code, 400)
        for params in ({}, {"lat": "abc", "lon": 106}, {"lat": 91, "lon": 106},
                       {"lat": "nan", "lon": 106}, {"lat": -6, "lon": "inf"}):
            response = self.client.get(self.url("fetch_weather_api"), params)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(self.url("save_location")).status_code, 405)
        self.assertEqual(self.client.post(self.url("fetch_weather_api")).status_code, 405)
        mock_weather.side_effect = weather_logic.WeatherServiceError("down")
        mock_search.side_effect = weather_logic.WeatherServiceError("down")
        self.assertEqual(self.client.get(self.url("fetch_weather_api"), {"lat": -6, "lon": 106}).status_code, 502)
        self.assertEqual(self.client.get(self.url("search_location_api"), {"q": "depok"}).status_code, 502)

    @patch("main.weather_logic.api_get")
    def test_live_weather_mock_cache_and_location_search(self, mock_get):
        mock_get.side_effect = self.mock_api
        weather = weather_logic.get_weather(-6.4, 106.8)
        self.assertEqual(weather["temperature"], 29)
        self.assertEqual(weather["aqi"], 55)
        self.assertEqual(weather["pop"], 15)
        self.assertEqual(weather["uv_index"], 4)
        self.assertTrue(weather["weather_icon"])
        self.assertTrue(weather["icons"]["temp"])
        self.assertEqual(set(weather["recommendations"]), {"energi", "mobilitas", "lainnya"})
        weather_logic.get_weather(-6.4, 106.8)
        self.assertEqual(mock_get.call_count, 2) 
        self.assertEqual(weather_logic.search_locations("  Depok  ")[0]["name"], "Depok, Jawa Barat, Indonesia")
        weather_logic.search_locations("depok")
        self.assertEqual(mock_get.call_count, 3)

    @patch("main.weather_logic.api_get")
    def test_air_quality_failure_does_not_break_weather(self, mock_get):
        def air_fails(url, params):
            if url == weather_logic.AIR_QUALITY_URL:
                raise weather_logic.WeatherServiceError("air offline")
            return self.mock_api(url, params)

        mock_get.side_effect = air_fails
        weather = weather_logic.get_weather(-6.4, 106.8)
        self.assertEqual(weather["temperature"], 29)
        self.assertIsNone(weather["aqi"])
        self.assertNotIn("None", str(weather["recommendations"]))
        cache.clear()
        self.forecast["current"].pop("precipitation_probability", None)
        self.forecast["current"].pop("uv_index", None)
        self.forecast["current"]["wind_speed_10m"] = None
        self.forecast["current"]["precipitation"] = None
        weather = weather_logic.get_weather(-6.4, 106.8)
        self.assertIsNone(weather["pop"])
        self.assertIsNone(weather["uv_index"])
        self.assertEqual(set(weather["recommendations"]), {"energi", "mobilitas", "lainnya"})

    def test_weather_recommendation_scenarios(self):
        base = weather_logic.parse_forecast(self.forecast)
        base.update({**weather_logic.AIR_QUALITY_EMPTY, "aqi": 35, "no2_aqi": 10,
                     "nitrogen_dioxide": 20})
        cases = [
            ({"temperature": 23, "weather_code": 0, "pop": 5}, "energi", "Kurangi penggunaan AC"),
            ({"temperature": 23, "aqi": 191, "no2_aqi": 130}, "energi", "Hemat AC tanpa membuka jendela"),
            ({"temperature": 34, "precipitation": 2, "pop": 90, "wind_speed": 35, "uv_index": 8}, "mobilitas", "Prioritaskan transportasi umum"),
            ({"weather_code": 95, "is_day": 0}, "mobilitas", "Tunda perjalanan saat badai"),
            ({"pop": 50}, "mobilitas", "Persiapan menghadapi hujan"),
            ({"aqi": 191}, "lainnya", "Kurangi aktivitas di luar ruangan"),
            ({"aqi": 120}, "lainnya", "Waspadai kualitas udara"),
            ({"aqi": 55}, "lainnya", "Perhatikan kualitas udara sedang"),
            ({"no2_aqi": 140}, "lainnya", "Waspadai paparan NO₂"),
        ]
        for updates, group, title in cases:
            weather = {**base, **updates}
            recs = weather_logic.generate_recommendations(weather)
            self.assertIn(title, [item["title"] for item in recs[group]])
        suitable = {**base, "pop": 5, "weather_code": 0}
        self.assertIn("Jalan kaki atau bersepeda", [r["title"] for r in weather_logic.mobility_recommendations(suitable)])
        polluted = {**suitable, "aqi": 191}
        self.assertNotIn("Jalan kaki atau bersepeda", [r["title"] for r in weather_logic.mobility_recommendations(polluted)])
        unavailable = {**base, "aqi": None, "no2_aqi": None, "nitrogen_dioxide": None,
                       "pop": None, "wind_speed": None, "uv_index": None, "precipitation": None}
        self.assertNotIn("None", str(weather_logic.generate_recommendations(unavailable)))

    def test_service_validation_and_icon_helpers(self):
        self.assertEqual(weather_logic.aqi_category(0), "Baik")
        self.assertEqual(weather_logic.aqi_category(101), "Tidak sehat bagi kelompok sensitif")
        self.assertEqual(weather_logic.aqi_category(201), "Sangat tidak sehat")
        self.assertEqual(weather_logic.aqi_category(301), "Berbahaya")
        self.assertNotEqual(weather_logic.parse_wmo_code(0, 1)[1], weather_logic.parse_wmo_code(0, 0)[1])
        self.assertEqual(weather_logic.parse_wmo_code(999)[0], "Kondisi tidak diketahui")
        self.assertTrue(weather_logic.weather_metric_icons(weather_logic.parse_forecast(self.forecast))["code"])
        self.assertEqual(weather_logic.icon_when_available("temp", None), "")

        parsed = weather_logic.parse_forecast(self.forecast)
        self.assertEqual(parsed["temperature"], 29)
        self.assertEqual(parsed["weather_code"], 2)
        self.assertEqual(parsed["day_period"], "Siang")

        for changes in (
            {"time": "bad time"},
            {"time": None},
            {"temperature_2m": None},
            {"weather_code": None},
            {"is_day": None},
        ):
            payload = {**self.forecast, "current": {**self.forecast["current"], **changes}}
            with self.assertRaises(weather_logic.WeatherServiceError):
                weather_logic.parse_forecast(payload)
        with self.assertRaises(weather_logic.WeatherServiceError):
            weather_logic.parse_forecast({"current": {}})
        with patch("main.weather_logic.requests.get", side_effect=requests.Timeout()):
            with self.assertRaises(weather_logic.WeatherServiceError):
                weather_logic.api_get(weather_logic.FORECAST_URL, {})
        with patch("main.weather_logic.api_get", return_value={"current": {}}):
            with self.assertRaises(weather_logic.WeatherServiceError):
                weather_logic.get_air_quality(-6.4, 106.8)

class ElectricitySurveyTests(TestCase):
    def setUp(self):
        self.user = make_user('electric-user', 'test123')
        self.client.force_login(self.user)
        self.data = {
            'device_type': 'laptop',
            'device_name': '',
            'quantity': '2',
            'power_watts': '65',
            'daily_usage_hours': '6',
            'notes': 'Untuk kuliah',
        }

    def test_emission_calculation(self):
        item = ElectricitySurvey.objects.create(
            user=self.user, device_type='laptop', quantity=2,
            power_watts='65', daily_usage_hours=6
        )
        item.refresh_from_db()
        self.assertAlmostEqual(float(item.daily_consumption_kwh), 0.78)
        self.assertAlmostEqual(float(item.daily_emission_co2), 0.559)

    def test_invalid_form(self):
        data = self.data.copy()
        data.update(device_type='other', device_name='')
        form = ElectricitySurveyForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('device_name', form.errors)

        data = self.data.copy()
        data['daily_usage_hours'] = '25'
        self.assertFalse(ElectricitySurveyForm(data=data).is_valid())

    def test_electricity_crud(self):
        add = self.client.post(reverse('main:add_electricity_survey'), self.data)
        self.assertEqual(add.status_code, 201)
        item = ElectricitySurvey.objects.get(user=self.user)

        listing = self.client.get(reverse('main:survey_electricity_list_json'))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()['data'][0]['device_label'], 'Laptop')

        edited = self.data.copy()
        edited.update(power_watts='100', quantity='1')
        update = self.client.post(reverse('main:edit_electricity_survey', args=[item.id]), edited)
        self.assertEqual(update.status_code, 200)
        item.refresh_from_db()
        self.assertAlmostEqual(float(item.daily_consumption_kwh), 0.6)

        delete = self.client.post(reverse('main:delete_electricity_survey', args=[item.id]))
        self.assertEqual(delete.status_code, 200)
        self.assertFalse(ElectricitySurvey.objects.filter(pk=item.id).exists())

    def test_cannot_edit_or_delete_other_users_data(self):
        other_user = make_user('other-user', 'test123')
        other_item = ElectricitySurvey.objects.create(
            user=other_user, device_type='laptop', quantity=2,
            power_watts='65', daily_usage_hours=6
        )

        listing = self.client.get(reverse('main:survey_electricity_list_json'))
        self.assertEqual(listing.json()['data'], [])
        self.assertEqual(
            self.client.post(reverse('main:edit_electricity_survey', args=[other_item.id]), self.data).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse('main:delete_electricity_survey', args=[other_item.id])).status_code,
            404,
        )
        self.assertTrue(ElectricitySurvey.objects.filter(pk=other_item.id).exists())

#Reusable Survey Test

class ReusableItemSurveyFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reusable-user",
            email="reusable-user@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_survey_page_renders_reusable_form_and_ajax_urls(self):
        response = self.client.get(reverse("main:show_dashboard_survey"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="item_type"')
        self.assertContains(response, 'name="quantity"')
        self.assertContains(response, 'name="uses_per_week"')
        self.assertContains(response, 'id="reusableFilter"')

    def test_reusable_survey_crud_and_list(self):
        add_response = self.client.post(
            reverse("main:add_reusable_survey"),
            {
                "item_type": "botol_minum",
                "quantity": 1,
                "uses_per_week": 7,
                "notes": "Botol minum pribadi",
            },
        )

        self.assertEqual(add_response.status_code, 201)
        survey_id = str(ReusableItemSurvey.objects.get(user=self.user).id)

        list_response = self.client.get(
            reverse("main:survey_reusable_list_json")
        )
        self.assertEqual(list_response.status_code, 200)

        survey_data = list_response.json()["data"][0]
        self.assertEqual(survey_data["id"], survey_id)
        self.assertEqual(survey_data["item_val"], "botol_minum")
        self.assertEqual(survey_data["quantity"], 1)
        self.assertEqual(survey_data["uses_per_week"], 7)
        self.assertEqual(survey_data["daily_emission_co2"], 0.01)

        edit_response = self.client.post(
            reverse("main:edit_reusable_survey", args=[survey_id]),
            {
                "item_type": "tote_bag",
                "quantity": 2,
                "uses_per_week": 5,
                "notes": "Tote bag",
            },
        )
        self.assertEqual(edit_response.status_code, 200)

        updated_data = self.client.get(
            reverse("main:survey_reusable_list_json")
        ).json()["data"][0]
        self.assertEqual(updated_data["item_val"], "tote_bag")
        self.assertEqual(updated_data["quantity"], 2)

        delete_response = self.client.post(
            reverse("main:delete_reusable_survey", args=[survey_id])
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("main:survey_reusable_list_json")
            ).json()["data"],
            [],
        )

    def test_reusable_survey_requires_login_and_updates_emission_log(self):
        add_response = self.client.post(
            reverse("main:add_reusable_survey"),
            {
                "item_type": "botol_minum",
                "quantity": 1,
                "uses_per_week": 7,
            },
        )
        self.assertEqual(add_response.status_code, 201)

        log = DailyEmissionLog.objects.get(user=self.user)
        self.assertEqual(float(log.total_emission_co2), -0.01)

        self.client.logout()
        response = self.client.get(
            reverse("main:survey_reusable_list_json")
        )
        self.assertEqual(response.status_code, 302)

#Public Features Test

PASSWORD = "Sandi-uji-123"

NO_MANIFEST = override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
})


@NO_MANIFEST
class PublicFeaturesTests(TestCase):

    def test_home_page_and_cta(self):
        response = self.client.get(reverse("main:show_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Track Your Energy")

        html = response.content.decode()
        tag = re.search(r'<a[^>]*class="btn-cta"[^>]*>', html)
        self.assertIsNotNone(tag)

        self.assertIn(
            reverse("main:show_register"),
            tag.group(0)
        )

        user = User.objects.create_user("pengguna", password=PASSWORD)
        self.client.force_login(user)

        response = self.client.get(reverse("main:show_home"))
        self.assertIn(
            reverse("main:show_dashboard"),
            response.content.decode()
        )

    def test_about_page(self):
        response = self.client.get(reverse("main:show_about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visi")
        self.assertContains(response, "Misi")

    def test_faq_page_shows_only_active_faqs(self):
        FAQ.objects.create(
            question="Pertanyaan pertama",
            answer="Jawaban pertama",
            order=1
        )
        FAQ.objects.create(
            question="Pertanyaan kedua",
            answer="Jawaban kedua",
            order=2
        )
        FAQ.objects.create(
            question="Pertanyaan tersembunyi",
            answer="Jawaban rahasia",
            order=3,
            is_active=False
        )

        response = self.client.get(reverse("main:show_faq"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pertanyaan pertama")
        self.assertContains(response, "Pertanyaan kedua")
        self.assertNotContains(response, "Pertanyaan tersembunyi")

        content = response.content.decode()
        self.assertLess(
            content.index("Pertanyaan pertama"),
            content.index("Pertanyaan kedua")
        )

    def test_faq_admin_protection(self):
        faq = FAQ.objects.create(
            question="Pertanyaan awal",
            answer="Jawaban awal",
            order=1
        )

        user = User.objects.create_user("biasa", password=PASSWORD)

        # User biasa
        self.client.force_login(user)
        self.client.post(
            reverse("main:add_faq"),
            {"question": "Baru", "answer": "Isi"}
        )
        self.assertEqual(FAQ.objects.count(), 1)

        # User biasa
        self.client.post(
            reverse("main:edit_faq", args=[faq.id]),
            {"question": "Diubah", "answer": "Diubah"}
        )
        faq.refresh_from_db()
        self.assertEqual(faq.question, "Pertanyaan awal")

        # Admin
        admin = User.objects.create_superuser("admin", password=PASSWORD)
        self.client.force_login(admin)
        self.client.post(
            reverse("main:add_faq"),
            {"question": "Baru", "answer": "Isi"}
        )
        self.assertEqual(FAQ.objects.count(), 2)






class AdminViewsTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="password123",
            first_name="Admin",
            last_name="GassWatt",
            is_staff=True,
        )

        self.user = User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="password123",
            first_name="User",
            last_name="Biasa",
        )

    def make_request(self, method, path="/", user=None, data=None):
        user = user or self.admin

        if method == "GET":
            request = self.factory.get(path)
        elif method == "POST":
            request = self.factory.post(path, data=data or {})
        else:
            raise ValueError("Method tidak didukung")

        request.user = user

        request.session = {}
        request._messages = FallbackStorage(request)

        return request

    @patch("main.views.view_admin.render")
    def test_admin_dashboard_success(self, mock_render):
        mock_render.return_value = HttpResponse("Dashboard")

        TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="motor_ice",
            daily_distance_km=Decimal("10"),
        )

        ElectricitySurvey.objects.create(
            user=self.user,
            device_type="lamp",
            quantity=1,
            power_watts=Decimal("100"),
            daily_usage_hours=2,
        )

        ReusableItemSurvey.objects.create(
            user=self.user,
            item_type="botol_minum",
            quantity=1,
            uses_per_week=7,
        )

        SavedLocation.objects.create(
            user=self.user,
            name="Jakarta",
            latitude=-6.2,
            longitude=106.8,
        )

        response = view_admin.admin_dashboard(
            self.make_request("GET")
        )

        self.assertEqual(response.status_code, 200)

        context = mock_render.call_args[0][2]

        self.assertEqual(context["admin_name"], "Admin GassWatt")
        self.assertEqual(context["total_users"], 2)
        self.assertEqual(context["total_lokasi"], 1)

        self.assertAlmostEqual(
            context["total_emisi"], 1.05, places=2
        )

        self.assertEqual(context["total_aktivitas_today"], 4)

        self.assertEqual(
            context["emisi_transport"], Decimal("0.90")
        )

        self.assertEqual(
            context["emisi_listrik"], Decimal("0.143")
        )

        self.assertEqual(
            context["emisi_reusable"], Decimal("0.010")
        )

        monthly_labels = json.loads(
            context["monthly_labels_json"]
        )
        monthly_users = json.loads(
            context["monthly_users_json"]
        )
        daily_labels = json.loads(
            context["daily_labels_json"]
        )
        daily_activities = json.loads(
            context["daily_activities_json"]
        )

        self.assertEqual(len(monthly_labels), 12)
        self.assertEqual(len(monthly_users), 12)
        self.assertEqual(len(daily_labels), 7)
        self.assertEqual(len(daily_activities), 7)

        self.assertEqual(
            daily_activities[-1], 4
        )

        self.assertEqual(
            mock_render.call_args[0][1],
            "admin-templates/admin-dashboard.html",
        )

    @patch("main.views.view_admin.render")
    def test_admin_dashboard_empty_emissions(self, mock_render):
        mock_render.return_value = HttpResponse("Dashboard")

        response = view_admin.admin_dashboard(
            self.make_request("GET")
        )

        context = mock_render.call_args[0][2]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(context["total_emisi"], 0.0)
        self.assertEqual(context["total_aktivitas_today"], 0)
        self.assertEqual(context["total_lokasi"], 0)

    @patch("main.views.view_admin.render")
    def test_admin_dashboard_admin_without_full_name(self, mock_render):
        mock_render.return_value = HttpResponse("Dashboard")

        self.admin.first_name = ""
        self.admin.last_name = ""
        self.admin.save()

        view_admin.admin_dashboard(
            self.make_request("GET")
        )

        context = mock_render.call_args[0][2]

        self.assertEqual(context["admin_name"], "admin")

    def test_admin_dashboard_requires_admin(self):
        request = self.make_request("GET", user=self.user)

        with self.assertRaises(PermissionDenied):
            view_admin.admin_dashboard(request)

    @patch("main.views.view_admin.render")
    def test_kelola_pengguna_success(self, mock_render):
        mock_render.return_value = HttpResponse("Users")

        TransportationSurvey.objects.create(
            user=self.user,
            transport_mode="motor_ice",
            daily_distance_km=Decimal("10"),
        )

        ElectricitySurvey.objects.create(
            user=self.user,
            device_type="lamp",
            power_watts=Decimal("100"),
            daily_usage_hours=2,
        )

        ReusableItemSurvey.objects.create(
            user=self.user,
            item_type="botol_minum",
            quantity=1,
            uses_per_week=7,
        )

        response = view_admin.kelola_pengguna(
            self.make_request("GET")
        )

        context = mock_render.call_args[0][2]
        users = context["users"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(context["total_count"], 2)
        self.assertEqual(len(users), 2)

        admin_data = next(
            u for u in users if u["id"] == self.admin.id
        )

        user_data = next(
            u for u in users if u["id"] == self.user.id
        )

        self.assertEqual(admin_data["nama"], "Admin GassWatt")
        self.assertEqual(admin_data["role"], "Admin")
        self.assertEqual(admin_data["status"], "Aktif")
        self.assertTrue(admin_data["is_self"])

        self.assertEqual(user_data["nama"], "User Biasa")
        self.assertEqual(user_data["role"], "Pengguna")
        self.assertEqual(user_data["status"], "Aktif")
        self.assertFalse(user_data["is_self"])

        self.assertAlmostEqual(
            user_data["total_emisi"], 1.05, places=1
        )

    @patch("main.views.view_admin.render")
    def test_kelola_pengguna_inactive_and_missing_email(self, mock_render):
        mock_render.return_value = HttpResponse("Users")

        self.user.is_active = False
        self.user.email = ""
        self.user.save()

        view_admin.kelola_pengguna(
            self.make_request("GET")
        )

        users = mock_render.call_args[0][2]["users"]

        user_data = next(
            u for u in users if u["id"] == self.user.id
        )

        self.assertEqual(user_data["email"], "-")
        self.assertEqual(user_data["status"], "Inaktif")

    @patch("main.views.view_admin.render")
    def test_kelola_pengguna_superuser_role(self, mock_render):
        mock_render.return_value = HttpResponse("Users")

        self.admin.is_staff = False
        self.admin.is_superuser = True
        self.admin.save()

        view_admin.kelola_pengguna(
            self.make_request("GET")
        )

        users = mock_render.call_args[0][2]["users"]

        admin_data = next(
            u for u in users if u["id"] == self.admin.id
        )

        self.assertEqual(admin_data["role"], "Admin")

    def test_delete_user_success(self):
        user_id = self.user.id

        request = self.make_request("POST")

        response = view_admin.delete_user(
            request, user_id=user_id
        )

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEqual(data["status"], "success")
        self.assertFalse(
            User.objects.filter(id=user_id).exists()
        )

    def test_delete_user_cannot_delete_self(self):
        request = self.make_request("POST")

        response = view_admin.delete_user(
            request, user_id=self.admin.id
        )

        self.assertEqual(response.status_code, 400)

        data = json.loads(response.content)

        self.assertEqual(data["status"], "error")
        self.assertTrue(
            User.objects.filter(id=self.admin.id).exists()
        )

    def test_delete_user_not_found(self):
        request = self.make_request("POST")

        response = view_admin.delete_user(
            request, user_id=999999
        )

        self.assertEqual(response.status_code, 404)

        data = json.loads(response.content)

        self.assertEqual(data["status"], "error")
        self.assertEqual(
            data["message"], "Pengguna tidak ditemukan."
        )

    def test_delete_user_denied_for_regular_user(self):
        request = self.make_request("POST", user=self.user)

        response = view_admin.delete_user(
            request, user_id=self.admin.id
        )

        self.assertEqual(response.status_code, 403)

        data = json.loads(response.content)

        self.assertEqual(data["status"], "error")
        self.assertEqual(data["message"], "Akses ditolak.")

        self.assertTrue(
            User.objects.filter(id=self.admin.id).exists()
        )


    @patch("main.views.view_admin.render")
    def test_kelola_faq_success(self, mock_render):
        mock_render.return_value = HttpResponse("FAQ")

        faq1 = FAQ.objects.create(
            question="Apa itu GassWatt?",
            answer="Platform ramah lingkungan.",
            order=2,
        )

        faq2 = FAQ.objects.create(
            question="Bagaimana cara menghitung emisi?",
            answer="Menggunakan data aktivitas.",
            order=1,
        )

        response = view_admin.kelola_faq(
            self.make_request("GET")
        )

        context = mock_render.call_args[0][2]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(context["admin_name"], "Admin GassWatt")

        self.assertEqual(
            list(context["faq_list"]),
            [faq2, faq1],
        )

    @patch("main.views.view_admin.render")
    def test_kelola_faq_admin_without_full_name(self, mock_render):
        mock_render.return_value = HttpResponse("FAQ")

        self.admin.first_name = ""
        self.admin.last_name = ""
        self.admin.save()

        view_admin.kelola_faq(
            self.make_request("GET")
        )

        context = mock_render.call_args[0][2]

        self.assertEqual(context["admin_name"], "admin")


    @patch("main.views.view_admin.redirect")
    def test_add_faq_success(self, mock_redirect):
        mock_redirect.return_value = HttpResponse(status=302)

        response = view_admin.add_faq(
            self.make_request(
                "POST",
                data={
                    "question": " Apa itu GassWatt? ",
                    "answer": " Platform pengelolaan emisi. ",
                },
            )
        )

        self.assertEqual(response.status_code, 302)

        faq = FAQ.objects.get()

        self.assertEqual(faq.question, "Apa itu GassWatt?")
        self.assertEqual(faq.answer, "Platform pengelolaan emisi.")
        self.assertEqual(faq.order, 1)
        self.assertTrue(faq.is_active)

    @patch("main.views.view_admin.redirect")
    def test_add_faq_auto_increment_order(self, mock_redirect):
        mock_redirect.return_value = HttpResponse(status=302)

        FAQ.objects.create(
            question="FAQ lama",
            answer="Jawaban lama",
            order=5,
        )

        view_admin.add_faq(
            self.make_request(
                "POST",
                data={
                    "question": "FAQ baru",
                    "answer": "Jawaban baru",
                },
            )
        )

        faq = FAQ.objects.get(question="FAQ baru")
        self.assertEqual(faq.order, 6)

    @patch("main.views.view_admin.redirect")
    def test_add_faq_invalid_empty_question(self, mock_redirect):
        mock_redirect.return_value = HttpResponse(status=302)
        response = view_admin.add_faq(
            self.make_request(
                "POST",
                data={
                    "question": " ",
                    "answer": "Jawaban",
                },
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FAQ.objects.count(), 0)

    @patch("main.views.view_admin.redirect")
    def test_add_faq_invalid_empty_answer(self, mock_redirect):
        mock_redirect.return_value = HttpResponse(status=302)
        response = view_admin.add_faq(
            self.make_request(
                "POST",
                data={
                    "question": "Pertanyaan",
                    "answer": " ",
                },
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FAQ.objects.count(), 0)


    @patch("main.views.view_admin.redirect")
    def test_edit_faq_success(self, mock_redirect):
        mock_redirect.return_value = HttpResponse(status=302)

        faq = FAQ.objects.create(
            question="Pertanyaan lama",
            answer="Jawaban lama",
            order=1,
        )
        response = view_admin.edit_faq(
            self.make_request(
                "POST",
                data={
                    "question": "Pertanyaan baru",
                    "answer": "Jawaban baru",
                },
            ),
            faq_id=faq.id,
        )
        self.assertEqual(response.status_code, 302)
        faq.refresh_from_db()
        self.assertEqual(faq.question, "Pertanyaan baru")
        self.assertEqual(faq.answer, "Jawaban baru")
        self.assertEqual(faq.order, 1)

    @patch("main.views.view_admin.redirect")
    def test_edit_faq_invalid_question(self, mock_redirect):
        mock_redirect.return_value = HttpResponse(status=302)
        faq = FAQ.objects.create(
            question="Pertanyaan lama",
            answer="Jawaban lama",
        )
        view_admin.edit_faq(
            self.make_request(
                "POST",
                data={
                    "question": "",
                    "answer": "Jawaban baru",
                },
            ),
            faq_id=faq.id,
        )
        faq.refresh_from_db()
        self.assertEqual(faq.question, "Pertanyaan lama")
        self.assertEqual(faq.answer, "Jawaban lama")

    @patch("main.views.view_admin.redirect")
    def test_edit_faq_invalid_answer(self, mock_redirect):
        mock_redirect.return_value = HttpResponse(status=302)
        faq = FAQ.objects.create(
            question="Pertanyaan lama",
            answer="Jawaban lama",
        )
        view_admin.edit_faq(
            self.make_request(
                "POST",
                data={
                    "question": "Pertanyaan baru",
                    "answer": " ",
                },
            ),
            faq_id=faq.id,
        )
        faq.refresh_from_db()
        self.assertEqual(faq.question, "Pertanyaan lama")
        self.assertEqual(faq.answer, "Jawaban lama")

    def test_edit_faq_not_found(self):
        request = self.make_request(
            "POST",
            data={
                "question": "Pertanyaan",
                "answer": "Jawaban",
            },
        )
        with self.assertRaises(Http404):
            view_admin.edit_faq(
                request, faq_id=999999
            )

    @patch("main.views.view_admin.redirect")
    def test_delete_faq_success(self, mock_redirect):
        mock_redirect.return_value = HttpResponse(status=302)
        faq = FAQ.objects.create(
            question="FAQ yang akan dihapus",
            answer="Jawaban",
        )
        faq_id = faq.id
        response = view_admin.delete_faq(
            self.make_request("POST"),
            faq_id=faq_id,
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            FAQ.objects.filter(id=faq_id).exists()
        )

    def test_delete_faq_not_found(self):
        request = self.make_request("POST")
        with self.assertRaises(Http404):
            view_admin.delete_faq(
                request, faq_id=999999
            )

    def test_admin_dashboard_only_accepts_get(self):
        request = self.make_request("POST")
        response = view_admin.admin_dashboard(request)
        self.assertEqual(response.status_code, 405)

    def test_delete_user_only_accepts_post(self):
        request = self.make_request("GET")
        response = view_admin.delete_user(
            request, user_id=self.user.id
        )
        self.assertEqual(response.status_code, 405)

    def test_add_faq_only_accepts_post(self):
        request = self.make_request("GET")
        response = view_admin.add_faq(request)
        self.assertEqual(response.status_code, 405)

    def test_edit_faq_only_accepts_post(self):
        faq = FAQ.objects.create(
            question="Pertanyaan",
            answer="Jawaban",
        )
        request = self.make_request("GET")
        response = view_admin.edit_faq(
            request, faq_id=faq.id
        )
        self.assertEqual(response.status_code, 405)

    def test_delete_faq_only_accepts_post(self):
        faq = FAQ.objects.create(
            question="Pertanyaan",
            answer="Jawaban",
        )
        request = self.make_request("GET")
        response = view_admin.delete_faq(
            request, faq_id=faq.id
        )
        self.assertEqual(response.status_code, 405)
