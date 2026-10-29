from datetime import timedelta
from django.contrib.auth.models import User
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    TransportationSurvey,
    SavedLocation,
    ElectricitySurvey,
    ReusableItemSurvey,
    DailyEmissionLog,
)
from .views import get_weekly_target_summary

from . import weather_logic
from .forms import LocationForm, LocationRenameForm, ElectricitySurveyForm


class TransportationSurveyFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="survey-user",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_survey_page_renders_form_and_ajax_urls(self):
        response = self.client.get(reverse("main:show_dashboard_survey"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="transport_mode"')
        self.assertContains(response, 'name="daily_distance_km"')
        self.assertContains(response, 'data-list-url="/dashboard/survey/list/"')

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

    def test_survey_and_emission_pages_require_login_and_render(self):
        self.client.logout()
        response = self.client.get(reverse("main:show_dashboard_survey"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.user)
        emission_response = self.client.get(reverse("main:emission_dashboard"))
        self.assertEqual(emission_response.status_code, 200)


class EmissionDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="emission-dashboard-user")
        self.client.force_login(self.user)
        self.url = reverse("main:emission_dashboard")
        self.today = timezone.now().date()

    def test_dashboard_with_no_surveys_returns_zero_metrics_and_default_score(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["today_emission"], 0)
        self.assertEqual(response.context["total_7days_emission"], 0)
        self.assertEqual(response.context["co2_saved"], 0)
        self.assertEqual(response.context["eco_score"], 100)
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
        self.assertEqual(response.context["eco_score"], 46)
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


class WeeklyTargetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="weekly-target-user")
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
        self.user = User.objects.create_user(username="main-dashboard-user")
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
            with self.subTest(recommendation=expected_text):
                self.assertTrue(
                    any(expected_text.lower() in item.lower() for item in recommendations),
                    f"Recommendation containing {expected_text!r} was not generated.",
                )


class WeatherFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="weather-user",
            password="test-password"
        )
        self.other = User.objects.create_user(
            username="other-weather",
            password="test-password"
        )

        self.client.force_login(self.user)
        cache.clear()
        self.forecast = {
            "timezone": "Asia/Jakarta",
            "current": {
                "time": "2026-10-22T14:00", "temperature_2m": 29,
                "relative_humidity_2m": 70, "precipitation": 0,
                "weather_code": 2, "is_day": 1, "wind_speed_10m": 12,
                "cloud_cover": 30,
            },
            "hourly": {
                "time": ["2026-10-22T14:00"],
                "precipitation_probability": [15], "uv_index": [4],
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
            with self.subTest(endpoint=name):
                self.assertEqual(getattr(self.client, method)(self.url(name, *args), data).status_code, 302)
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
            with self.subTest(action=action):
                self.assertEqual(self.client.post(self.url(action, other.id), {"name": "Bajak"}).status_code, 404)
        self.assertEqual(self.client.post(self.url("update_location", own.id), {"name": " "}).status_code, 400)
        for coords in ((91, 106), (-6, 181), ("nan", 106), ("inf", 106)):
            with self.subTest(coords=coords):
                self.assertFalse(LocationForm(data={"name": "GPS", "latitude": coords[0],
                                                    "longitude": coords[1]}).is_valid())
        self.assertFalse(LocationRenameForm(data={"name": "  "}).is_valid())

    @patch("main.views.search_locations")
    @patch("main.views.get_weather")
    def test_api_search_weather_and_errors(self, mock_weather, mock_search):
        mock_search.return_value = [{"name": "Depok", "latitude": -6.4, "longitude": 106.8}]
        mock_weather.return_value = {"temperature": 29, "aqi": 55}
        self.assertEqual(self.client.get(self.url("search_location_api"), {"q": "Depok"}).status_code, 200)
        self.assertEqual(self.client.get(self.url("fetch_weather_api"), {"lat": -6.4, "lon": 106.8}).json()["temperature"], 29)
        self.assertEqual(self.client.get(self.url("search_location_api"), {"q": "a"}).json(), {"results": []})
        self.assertEqual(self.client.get(self.url("search_location_api"), {"q": "x" * 101}).status_code, 400)
        for params in ({}, {"lat": "abc", "lon": 106}, {"lat": 91, "lon": 106},
                       {"lat": "nan", "lon": 106}, {"lat": -6, "lon": "inf"}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url("fetch_weather_api"), params).status_code, 400)
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
        self.forecast["hourly"] = {}
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
            with self.subTest(title=title):
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
        self.assertEqual(weather_logic.value_for_time({}, "uv_index", "2026-10-22T14", hourly=True), None)

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
            with self.subTest(changes=changes):
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
        self.user = User.objects.create_user(username='electric-user', password='test123')
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
        other_user = User.objects.create_user(username='other-user', password='test123')
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
