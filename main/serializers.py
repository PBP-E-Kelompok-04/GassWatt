from django.utils.html import strip_tags
from rest_framework import serializers

from main.models import TransportationSurvey


class TransportationSurveySerializer(serializers.ModelSerializer):
    transport_mode_display = serializers.CharField(
        source="get_transport_mode_display",
        read_only=True,
    )

    class Meta:
        model = TransportationSurvey
        fields = [
            "id",
            "user",
            "transport_mode",
            "transport_mode_display",
            "daily_distance_km",
            "notes",
            "daily_emission_co2",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "daily_emission_co2",
            "created_at",
        ]

    def validate_notes(self, value):
        return strip_tags(value) if value else value