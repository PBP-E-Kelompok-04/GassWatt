from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import (
    api_view, permission_classes,
)
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from main.views.view_dashboard import (
    _sync_daily_emission_logs,
    get_dashboard_recommendations,
    get_emission_dashboard_data,
    get_weekly_target_summary,
)
from main.models import TransportationSurvey
# from main.permissions import IsPortfolioOwnerOrReadOnly
from main.serializers import (
    TransportationSurveySerializer,
    ElectricitySurveySerializer,
    ReusableSurveySerializer,
    FAQSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def emission_chart(request):
    _sync_daily_emission_logs(request.user)
    emission_data = get_emission_dashboard_data(request.user)

    return Response({
        "status": "success",
        "labels": emission_data["chart_labels"],
        "datasets": [
            {
                "label": "Jejak Karbon (kg CO2e)",
                "data": emission_data["chart_values"],
            }
        ],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def emission_dashboard_data(request):
    _sync_daily_emission_logs(request.user)
    emission_data = get_emission_dashboard_data(request.user)

    return Response({
        "status": "success",
        **emission_data["metrics"],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_recommendations(request):
    _sync_daily_emission_logs(request.user)
    target_weekly = get_weekly_target_summary(request.user)
    recommendations = get_dashboard_recommendations(
        request.user,
        target_weekly,
    )

    return Response({
        "status": "success",
        "data": recommendations,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def weekly_target(request):
    _sync_daily_emission_logs(request.user)
    target_data = get_weekly_target_summary(request.user)

    return Response({
        "status": "success",
        "data": target_data,
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

@api_view(["GET", "HEAD", "POST"])
@permission_classes([IsAuthenticated])
def electricity_list(request):
    if request.method in ("GET", "HEAD"):
        surveys = ElectricitySurvey.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = ElectricitySurveySerializer(surveys, many=True)
        return Response({"status": "success", "data": serializer.data})

    # validate input flutter untuk add electricity emission
    serializer = ElectricitySurveySerializer(data=request.data)
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
        {
            "status": "error",
            "message": "Data gagal ditambahkan.",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST,
    )

@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def electricity_detail(request, survey_id):
    survey = get_object_or_404(
        ElectricitySurvey,
        id=survey_id,
        user=request.user,
    )

    if request.method == "GET":
        serializer = ElectricitySurveySerializer(survey)
        return Response({"status": "success", "data": serializer.data})

    if request.method in ("PUT", "PATCH"):
        serializer = ElectricitySurveySerializer(
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
            {
                "status": "error",
                "message": "Data gagal diperbarui.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

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

@api_view(["GET", "HEAD", "POST"])
@permission_classes([IsAuthenticated])
def reusable_list(request):
    if request.method in ("GET", "HEAD"):
        surveys = ReusableSurvey.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = ReusableSurveySerializer(surveys, many=True)
        return Response({"status": "success", "data": serializer.data})

    # validate input flutter untuk add reusable item
    serializer = ReusableSurveySerializer(data=request.data)
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
        {
            "status": "error",
            "message": "Data gagal ditambahkan.",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST,
    )

@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def reusable_detail(request, survey_id):
    survey = get_object_or_404(
        ReusableSurvey,
        id=survey_id,
        user=request.user,
    )

    if request.method == "GET":
        serializer = ReusableSurveySerializer(survey)
        return Response({"status": "success", "data": serializer.data})

    if request.method in ("PUT", "PATCH"):
        serializer = ReusableSurveySerializer(
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
            {
                "status": "error",
                "message": "Data gagal diperbarui.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

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

@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def faq_list(request):
    if request.method == "GET":
        faqs = FAQ.objects.filter(is_active=True).order_by("order")
        serializer = FAQSerializer(faqs, many=True)
        return Response({"status": "success", "data": serializer.data})

    if not request.user.is_authenticated or not request.user.is_superuser:
        return Response(
            {
                "status": "error",
                "message": "Hanya admin yang dapat menambahkan FAQ.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = FAQSerializer(data=request.data)
    if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "FAQ berhasil ditambahkan.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
    return Response(
        {
            "status": "error",
            "message": "FAQ gagal ditambahkan.",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST,
    )

@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def faq_detail(request, faq_id):
    faq = get_object_or_404(FAQ, id=faq_id)

    if request.method == "GET":
        if not faq.is_active and (not request.user.is_authentivated or not request.user.is_superuser):
            return Response(
                {
                    "status": "error",
                    "message": "FAQ tidak ditemukan."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = FAQSerializer(faq)
        return Response({"status": "success", "data": serializer.data})
    
    if not request.user.is_authentivated or not request.user.is_superuser:
        return Response(
                {
                    "status": "error",
                    "message": "Hanya admin yang dapat mengelola FAQ.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    if request.method in ("PUT", "PATCH"):
        serializer = FAQSerializer(
            faq, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "FAQ berhasil diperbarui.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "FAQ gagal diperbarui.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "DELETE":
        faq.delete()
        return Response(
            {
                "status": "success",
                "message": "FAQ berhasil dihapus.",
            },
            status=status.HTTP_200_OK,
        )
