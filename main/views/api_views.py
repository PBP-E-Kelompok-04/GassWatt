from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (
    api_view, permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from main.views.view_dashboard import _sync_daily_emission_logs
from main.models import DailyEmissionLog, TransportationSurvey
# from main.permissions import IsPortfolioOwnerOrReadOnly
from main.serializers import TransportationSurveySerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def emission_chart(request):
    _sync_daily_emission_logs(request.user)

    today = timezone.now().date()
    labels = []
    values = []
    day_names = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]

    for days_ago in range(6, -1, -1):
        target_date = today - timedelta(days=days_ago)
        log = DailyEmissionLog.objects.filter(
            user=request.user,
            date=target_date,
        ).first()
        values.append(float(log.total_emission_co2) if log else 0.0)
        labels.append(
            f"{day_names[target_date.weekday()]} ({target_date.day})"
        )

    return Response({
        "status": "success",
        "labels": labels,
        "datasets": [
            {
                "label": "Jejak Karbon (kg CO2e)",
                "data": values,
            }
        ],
    })


@api_view(["GET", "HEAD", "POST"])
@permission_classes([IsAuthenticated])
def transportation_list(request):
    # Menggantikan survey_transport_list_json
    if request.method in ("GET", "HEAD"):
        surveys = TransportationSurvey.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = TransportationSurveySerializer(surveys, many=True)
        return Response({"status": "success", "data": serializer.data})

    # Menggantikan add_transport_survey
    serializer = TransportationSurveySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        _sync_daily_emission_logs(request.user)
        return Response(
            {
                "status": "success",
                "message": "Data berhasil ditambahkan.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {"status": "error", "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def transportation_detail(request, survey_id):
    survey = get_object_or_404(
        TransportationSurvey,
        id=survey_id,
        user=request.user,
    )

    # Opsional: Mengambil satu data spesifik
    if request.method == "GET":
        serializer = TransportationSurveySerializer(survey)
        return Response({"status": "success", "data": serializer.data})

    # Menggantikan edit_transport_survey
    if request.method in ("PUT", "PATCH"):
        # partial=True membuat PATCH bisa mengupdate sebagian field saja
        serializer = TransportationSurveySerializer(
            survey, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            serializer.save()
            _sync_daily_emission_logs(request.user)
            return Response(
                {
                    "status": "success",
                    "message": "Data berhasil diperbarui.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"status": "error", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Menggantikan delete_transport_survey
    if request.method == "DELETE":
        survey.delete()
        _sync_daily_emission_logs(request.user)
        return Response(
            {
                "status": "success",
                "message": "Data berhasil dihapus.",
            },
            status=status.HTTP_200_OK,
        )