from django.shortcuts import get_object_or_404
import math
from rest_framework import status
from rest_framework.decorators import (
    api_view, permission_classes,
)
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.db.models import Sum, Max

from main.views.view_dashboard import (
    _sync_daily_emission_logs,
    get_dashboard_recommendations,
    get_emission_dashboard_data,
    get_weekly_target_summary,
)

from main.models import (
    TransportationSurvey,
    ElectricitySurvey,
    ReusableItemSurvey,
    FAQ,
    SavedLocation
)
# from main.permissions import IsPortfolioOwnerOrReadOnly
from main.serializers import (
    TransportationSurveySerializer,
    ElectricitySurveySerializer,
    ReusableSurveySerializer,
    FAQSerializer,
    SavedLocationSerializer,
    AdminUserSerializer,
    AdminFAQSerializer,
)

from main.weather_logic import WeatherServiceError, search_locations, get_weather

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
        surveys = ReusableItemSurvey.objects.filter(
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
        ReusableItemSurvey,
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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def weather_search(request):
    query = request.query_params.get("q", "").strip()
    if len(query) < 2:
        return Response({"results": []})
    if len(query) > 100:
        return Response({"error": "Pencarian maksimal 100 karakter."}, status=400)
    try:
        return Response({"results": search_locations(query)})
    except WeatherServiceError:
        return Response({"error": "Pencarian lokasi sementara gagal."}, status=502)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def weather_current(request):
    try:
        lat = float(request.query_params.get("lat", ""))
        lon = float(request.query_params.get("lon", ""))
    except (ValueError, TypeError):
        return Response({"error": "Koordinat tidak valid."}, status=400)

    if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return Response({"error": "Koordinat di luar rentang yang valid."}, status=400)

    try:
        return Response(get_weather(lat, lon))
    except WeatherServiceError:
        return Response({"error": "Gagal mengambil cuaca dari Open-Meteo. Coba lagi."}, status=502)


@api_view(["GET", "HEAD", "POST"])
@permission_classes([IsAuthenticated])
def weather_location_list(request):
    if request.method in ("GET", "HEAD"):
        locations = SavedLocation.objects.filter(user=request.user)
        return Response({"results": SavedLocationSerializer(locations, many=True).data})

    serializer = SavedLocationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    location = SavedLocation.objects.filter(
        user=request.user,
        latitude=values["latitude"],
        longitude=values["longitude"],
    ).first()
    created = location is None

    SavedLocation.objects.filter(
        user=request.user, is_active=True
    ).update(is_active=False)

    if created:
        location = serializer.save(user=request.user, is_active=True)
    else:
        location.name = values["name"]
        location.is_active = True
        location.save(update_fields=["name", "is_active"])

    return Response({
        "status": "success", "created": created,
        "location": SavedLocationSerializer(location).data,
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def weather_location_detail(request, location_id):
    location = get_object_or_404(SavedLocation, pk=location_id, user=request.user)
    if request.method in ("GET", "HEAD"):
        return Response(SavedLocationSerializer(location).data)
    if request.method == "DELETE":
        location.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if set(request.data.keys()) != {"name"}:
        return Response({"error": "Hanya nama lokasi yang boleh diubah."}, status=400)

    serializer = SavedLocationSerializer(
        location, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({"status": "success", "location": SavedLocationSerializer(location).data})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def weather_location_activate(request, location_id):
    location = get_object_or_404(
        SavedLocation, pk=location_id, user=request.user
    )

    if request.method == "GET":
        return Response(SavedLocationSerializer(location).data)
    
    SavedLocation.objects.filter(
        user=request.user, is_active=True
    ).exclude(pk=location.pk).update(is_active=False)

    location.is_active = True
    location.save(update_fields=["is_active"])
    return Response({"status": "success", "location": SavedLocationSerializer(location).data})



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_dashboard_summary(request):
    if not request.user.is_superuser:
        return Response(
            {"status": "error", "message": "Akses ditolak. Khusus Admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_faqs = FAQ.objects.count()

    transport_co2 = TransportationSurvey.objects.aggregate(total=Sum("daily_emission_co2"))["total"] or 0.0
    electricity_co2 = ElectricitySurvey.objects.aggregate(total=Sum("daily_emission_co2"))["total"] or 0.0
    reusable_co2 = ReusableItemSurvey.objects.aggregate(total=Sum("daily_emission_co2"))["total"] or 0.0
    total_emission = round(transport_co2 + electricity_co2 + reusable_co2, 2)

    return Response({
        "status": "success",
        "metrics": {
            "total_users": total_users,
            "active_users": active_users,
            "total_faqs": total_faqs,
            "total_emission_co2": total_emission,
            "breakdown": {
                "transportation": round(transport_co2, 2),
                "electricity": round(electricity_co2, 2),
                "reusable": round(reusable_co2, 2),
            },
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_user_list(request):
    if not request.user.is_superuser:
        return Response(
            {"status": "error", "message": "Akses ditolak. Khusus Admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    query = request.query_params.get("q", "").strip()
    users = User.objects.all().order_by("-date_joined")
    if query:
        users = users.filter(username__icontains=query) | users.filter(email__icontains=query)

    serializer = AdminUserSerializer(users, many=True)
    return Response({"status": "success", "data": serializer.data})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def admin_user_delete(request, user_id):
    if not request.user.is_superuser:
        return Response(
            {"status": "error", "message": "Akses ditolak. Khusus Admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.user.id == user_id:
        return Response(
            {"status": "error", "message": "Tidak dapat menghapus akun sendiri."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    target_user = get_object_or_404(User, id=user_id)
    target_user.delete()
    return Response(
        {"status": "success", "message": "Pengguna berhasil dihapus."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def admin_faq_list(request):
    if not request.user.is_superuser:
        return Response(
            {"status": "error", "message": "Akses ditolak. Khusus Admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "GET":
        faqs = FAQ.objects.all().order_by("order")
        serializer = AdminFAQSerializer(faqs, many=True)
        return Response({"status": "success", "data": serializer.data})

    serializer = AdminFAQSerializer(data=request.data)
    if serializer.is_valid():
        max_order = FAQ.objects.aggregate(max_val=Max("order"))["max_val"] or 0
        serializer.save(order=max_order + 1, is_active=True)
        return Response(
            {
                "status": "success",
                "message": "FAQ berhasil ditambahkan.",
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
def admin_faq_detail(request, faq_id):
    if not request.user.is_superuser:
        return Response(
            {"status": "error", "message": "Akses ditolak. Khusus Admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    faq = get_object_or_404(FAQ, id=faq_id)

    if request.method == "GET":
        serializer = AdminFAQSerializer(faq)
        return Response({"status": "success", "data": serializer.data})

    if request.method in ("PUT", "PATCH"):
        serializer = AdminFAQSerializer(
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
            {"status": "error", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "DELETE":
        faq.delete()
        return Response(
            {"status": "success", "message": "FAQ berhasil dihapus."},
            status=status.HTTP_200_OK,
        )