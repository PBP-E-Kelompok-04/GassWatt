from django.utils.html import strip_tags
from rest_framework import serializers

from main.models import TransportationSurvey, ElectricitySurvey, ReusableItemSurvey, FAQ


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

class ElectricitySurveySerializer(serializers.ModelSerializer):
    device_type_display = serializers.CharField(
        source="get_device_type_display",
        read_only=True,
    )

    class Meta:
        model = ElectricitySurvey
        fields = [
            "id",
            "user",
            "device_type",
            "device_type_display",
            "device_name",
            "quantity",
            "power_watts",
            "daily_usage_hours",
            "notes",
            "daily_emission_co2",
            "daily_consumption_kwh",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "daily_consumption_kwh",
            "daily_emission_co2",
            "created_at",
        ]
    
    def validete_notes(self, value):
        return strip_tags(value) if value else value

class ReusableSurveySerializer(serializers.ModelSerializer):
    item_type_display = serializers.CharField(
        source="get_item_type_display",
        read_only=True,
    )

    class Meta:
        model = ReusableItemSurvey
        fields = [
            "id",
            "user",
            "item_type",
            "item_type_display",
            "quantity",
            "user_per_week",
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
    
    def validete_notes(self, value):
        return strip_tags(value) if value else value

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            "id",
            "question",
            "answer",
            "order",
        ]
        read_only_fields = fields