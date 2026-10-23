import math

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required

from .forms import LocationForm, LocationRenameForm
from .models import SavedLocation
from .weather_logic import WeatherServiceError, get_weather, search_locations

def show_home(request):
    return render(request, "home.html")

def show_dashboard(request):
    return render(request, "dashboard-templates/dashboard.html")

def show_dashboard_survey(request):
    return render(request, "dashboard-templates/dashboard-survey.html")

@login_required
def show_dashboard_weather(request):
    return render(request, "dashboard-templates/dashboard-weather.html")

@login_required
@require_GET
def search_location_api(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})
    if len(query) > 100:
        return JsonResponse({"error": "Pencarian maksimal 100 karakter."}, status=400)
    try:
        return JsonResponse({"results": search_locations(query)})
    except WeatherServiceError:
        return JsonResponse({"error": "Pencarian lokasi sementara gagal."}, status=502)

@login_required
def fetch_weather_api(request):
    try:
        latitude = float(request.GET["lat"])
        longitude = float(request.GET["lon"])
    except (KeyError, ValueError, TypeError):
        return JsonResponse({"error": "Latitude dan longitude wajib berupa angka."}, status=400)
    if not (math.isfinite(latitude) and math.isfinite(longitude)
            and -90 <= latitude <= 90 and -180 <= longitude <= 180):
        return JsonResponse({"error": "Koordinat berada di luar rentang yang valid."}, status=400)
    try:
        return JsonResponse(get_weather(latitude, longitude))
    except WeatherServiceError:
        return JsonResponse({"error": "Gagal mengambil cuaca dari Open-Meteo. Coba lagi."}, status=502)

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
    locations = SavedLocation.objects.filter(user=request.user)
    
    return JsonResponse({"results": [serialize_locations(location) for location in locations]})


@login_required
@require_POST
def save_location(request):
    form = LocationForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    values = form.cleaned_data
    try:
        with transaction.atomic():
            SavedLocation.objects.filter(user=request.user, is_active=True).update(is_active=False)
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
        return JsonResponse({"error": "Lokasi sedang diubah, coba kembali."}, status=409)
    return JsonResponse({"status": "success", "created": created,
                         "location": serialize_locations(location)}, status=201 if created else 200)

@login_required
@require_POST
def update_location(request, location_id):
    location = get_object_or_404(SavedLocation, pk=location_id, user=request.user)
    form = LocationRenameForm(request.POST, instance=location)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)
    location = form.save()
    return JsonResponse({"status": "success", "location": serialize_locations(location)})

@login_required
@require_POST
def activate_location(request, location_id):
    try:
        with transaction.atomic():
            location = get_object_or_404(SavedLocation, pk=location_id, user=request.user)
            SavedLocation.objects.filter(user=request.user, is_active=True).exclude(
                pk=location.pk
            ).update(is_active=False)
            location.is_active = True
            location.save(update_fields=["is_active"])
    except IntegrityError:
        return JsonResponse({"error": "Terjadi konflik saat memilih lokasi."}, status=409)
    return JsonResponse({"status": "success", "location": serialize_locations(location)})

@login_required
@require_POST
def delete_location(request, location_id):
    location = get_object_or_404(SavedLocation, pk=location_id, user=request.user)
    was_active = location.is_active
    location.delete()
    return JsonResponse({"status": "success", "was_active": was_active})


def show_dashboard_emission(request):
    return render(request, "dashboard-templates/dashboard-emission.html")