from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import TransportationSurvey


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
