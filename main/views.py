import math
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import (
    TransportationSurvey,
    DailyEmissionLog,
    FAQ,
    SavedLocation,
)

from .forms import (
    TransportationSurveyForm,
    LocationForm,
    LocationRenameForm,
)

from .weather_logic import (
    WeatherServiceError,
    get_weather,
    search_locations,
)

def show_home(request):
    return render(request, "home.html")

def show_dashboard(request):
    return render(request, "dashboard-templates/dashboard.html")

# @login_required
def show_dashboard_survey(request):
    return render(
        request,
        "dashboard-templates/dashboard-survey.html",
        {"form": TransportationSurveyForm()},
    )

#@login_required
def show_dashboard_weather(request):
    return render(request, "dashboard-templates/dashboard-weather.html")

def _sync_daily_emission_logs(user):
    today = timezone.now().date()

    current_total = TransportationSurvey.objects.filter(user=user).aggregate(
        total=Sum('daily_emission_co2')
    )['total'] or 0.000

    last_log = DailyEmissionLog.objects.filter(user=user).order_by('-date').first()

    if not last_log:
        DailyEmissionLog.objects.create(
            user=user,
            date=today,
            total_emission_co2=current_total
        )
    else:
        DailyEmissionLog.objects.update_or_create(
            user=user,
            date=today,
            defaults={'total_emission_co2': current_total}
        )

        start_date = last_log.date + timedelta(days=1)

        while start_date < today:
            DailyEmissionLog.objects.get_or_create(
                user=user,
                date=start_date,
                defaults={
                    'total_emission_co2': last_log.total_emission_co2
                }
            )
            start_date += timedelta(days=1)

@login_required
def survey_transport_list_json(request):
    surveys = TransportationSurvey.objects.filter(
        user=request.user
    ).order_by("-created_at")

    data = [
        {
            "id": str(survey.id),
            "mode": survey.get_transport_mode_display(),
            "mode_val": survey.transport_mode,
            "distance": float(survey.daily_distance_km),
            "notes": survey.notes or "",
            "daily_emission_co2": float(survey.daily_emission_co2),
        }
        for survey in surveys
    ]

    return JsonResponse({"status": "success", "data": data})

@login_required
def add_transport_survey(request):
    if request.method == "POST":
        form = TransportationSurveyForm(request.POST)

        if form.is_valid():
            survey = form.save(commit=False)
            survey.user = request.user
            survey.save()

            _sync_daily_emission_logs(request.user)

            return JsonResponse({
                'status': 'success',
                'message': 'Data berhasil ditambahkan.'
            }, status=201)
        else:
            return JsonResponse({
                'status': 'error',
                'errors': form.errors
            }, status=400)

    return JsonResponse({
        "status": "error",
        "message": "Method tidak diizinkan."
    }, status=405)

@login_required
def edit_transport_survey(request, survey_id):
    survey = get_object_or_404(
        TransportationSurvey,
        id=survey_id,
        user=request.user
    )

    if request.method == "POST":
        form = TransportationSurveyForm(request.POST, instance=survey)

        if form.is_valid():
            form.save()
            _sync_daily_emission_logs(request.user)

            return JsonResponse({
                'status': 'success',
                'message': 'Data berhasil diperbarui.'
            }, status=200)
        else:
            return JsonResponse({
                'status': 'error',
                'errors': form.errors
            }, status=400)

    return JsonResponse({
        "status": "error",
        "message": "Method tidak diizinkan."
    }, status=405)

@login_required
def delete_transport_survey(request, survey_id):
    survey = get_object_or_404(
        TransportationSurvey,
        id=survey_id,
        user=request.user
    )

    if request.method == "POST":
        survey.delete()
        _sync_daily_emission_logs(request.user)

        return JsonResponse({
            'status': 'success',
            'message': 'Data berhasil dihapus.'
        }, status=200)

    return JsonResponse({
        "status": "error",
        "message": "Method tidak diizinkan."
    }, status=405)

@login_required
def emission_dashboard(request):
    _sync_daily_emission_logs(request.user)

    logs = DailyEmissionLog.objects.filter(user=request.user)

    chart_dates = [
        log.date.strftime('%d %b') for log in logs
    ]
    chart_values = [
        float(log.total_emission_co2) for log in logs
    ]

    context = {
        'chart_dates': chart_dates,
        'chart_values': chart_values,
        'logs': logs,
    }

    return render(
        request,
        "dashboard-templates/dashboard-emission.html",
        context
    )

def show_faq(request):
    faq_list = FAQ.objects.filter(is_active=True)

    context = {
        "faq_list": faq_list,
    }

    return render(request, "faq.html", context)

def get_faq_json(request):
    faqs = FAQ.objects.all()
    data = []

    for faq in faqs:
        data.append({
            "pk": str(faq.id),
            "fields": {
                "question": faq.question,
                "answer": faq.answer,
                "order": faq.order,
                "is_active": faq.is_active,
            }
        })

    return JsonResponse(data, safe=False)

def show_about(request):
    context = {
        "name": "GassWatt",
    }

    return render(request, "about.html", context)

@login_required
@require_GET
def search_location_api(request):
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"results": []})

    if len(query) > 100:
        return JsonResponse({
            "error": "Pencarian maksimal 100 karakter."
        }, status=400)

    try:
        return JsonResponse({
            "results": search_locations(query)
        })
    except WeatherServiceError:
        return JsonResponse({
            "error": "Pencarian lokasi sementara gagal."
        }, status=502)

@login_required
def fetch_weather_api(request):
    try:
        latitude = float(request.GET["lat"])
        longitude = float(request.GET["lon"])
    except (KeyError, ValueError, TypeError):
        return JsonResponse({
            "error": "Latitude dan longitude wajib berupa angka."
        }, status=400)

    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):
        return JsonResponse({
            "error": "Koordinat berada di luar rentang yang valid."
        }, status=400)

    try:
        return JsonResponse(
            get_weather(latitude, longitude)
        )
    except WeatherServiceError:
        return JsonResponse({
            "error": "Gagal mengambil cuaca dari Open-Meteo. Coba lagi."
        }, status=502)

def serialize_locations(location):
    return {
        "id": location.id,
        "name": location.name,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "is_active": location.is_active,
    }

@login_required
@require_GET
def list_locations(request):
    locations = SavedLocation.objects.filter(
        user=request.user
    )

    return JsonResponse({
        "results": [
            serialize_locations(location)
            for location in locations
        ]
    })

@login_required
@require_POST
def save_location(request):
    form = LocationForm(request.POST)

    if not form.is_valid():
        return JsonResponse({
            "errors": form.errors
        }, status=400)

    values = form.cleaned_data

    try:
        with transaction.atomic():
            SavedLocation.objects.filter(
                user=request.user,
                is_active=True
            ).update(is_active=False)

            location = SavedLocation.objects.filter(
                user=request.user,
                latitude=values["latitude"],
                longitude=values["longitude"],
            ).first()

            created = location is None

            if created:
                location = form.save(commit=False)
                location.user = request.user
            else:
                location.name = values["name"]

            location.is_active = True
            location.save()

    except IntegrityError:
        return JsonResponse({
            "error": "Lokasi sedang diubah, coba kembali."
        }, status=409)

    return JsonResponse({
        "status": "success",
        "created": created,
        "location": serialize_locations(location)
    }, status=201 if created else 200)

@login_required
@require_POST
def update_location(request, location_id):
    location = get_object_or_404(
        SavedLocation,
        pk=location_id,
        user=request.user
    )

    form = LocationRenameForm(
        request.POST,
        instance=location
    )

    if not form.is_valid():
        return JsonResponse({
            "errors": form.errors
        }, status=400)

    location = form.save()

    return JsonResponse({
        "status": "success",
        "location": serialize_locations(location)
    })

@login_required
@require_POST
def activate_location(request, location_id):
    try:
        with transaction.atomic():
            location = get_object_or_404(
                SavedLocation,
                pk=location_id,
                user=request.user
            )

            SavedLocation.objects.filter(
                user=request.user,
                is_active=True
            ).exclude(
                pk=location.pk
            ).update(is_active=False)

            location.is_active = True
            location.save(update_fields=["is_active"])

    except IntegrityError:
        return JsonResponse({
            "error": "Terjadi konflik saat memilih lokasi."
        }, status=409)

    return JsonResponse({
        "status": "success",
        "location": serialize_locations(location)
    })

@login_required
@require_POST
def delete_location(request, location_id):
    location = get_object_or_404(
        SavedLocation,
        pk=location_id,
        user=request.user
    )

    was_active = location.is_active
    location.delete()

    return JsonResponse({
        "status": "success",
        "was_active": was_active
    })