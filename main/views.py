from datetime import datetime, timedelta
import math

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.utils import timezone

from django.contrib import messages

from django.views.decorators.http import require_GET, require_POST

from authentication.views import show_login, login_user, show_register, register_user

from .models import (
    TransportationSurvey,
    ElectricitySurvey,
    ReusableItemSurvey,
    DailyEmissionLog,
    FAQ,
    SavedLocation,
)


from .forms import (
    TransportationSurveyForm,
    ElectricitySurveyForm,
    ReusableItemSurveyForm,
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

def get_weekly_target_summary(user, target_goal_pct=10.0):
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)
    fourteen_days_ago = today - timedelta(days=14)

    this_week_raw = DailyEmissionLog.objects.filter(
        user=user, date__gte=seven_days_ago
    ).aggregate(total=Sum('total_emission_co2'))['total']
    this_week = float(this_week_raw) if this_week_raw is not None else 0.0

    last_week_raw = DailyEmissionLog.objects.filter(
        user=user, date__gte=fourteen_days_ago, date__lt=seven_days_ago
    ).aggregate(total=Sum('total_emission_co2'))['total']
    last_week = float(last_week_raw) if last_week_raw is not None else 0.0

    co2_reduced_kg = max(0.0, last_week - this_week)
    actual_reduction_pct = ((last_week - this_week) / last_week * 100) if last_week > 0 else 0.0
    is_achieved = actual_reduction_pct >= target_goal_pct

    return {
        'co2_reduced_kg': round(co2_reduced_kg, 2),
        'target_goal_pct': round(target_goal_pct, 1),
        'actual_reduction_pct': round(actual_reduction_pct, 1),
        'is_achieved': is_achieved
    }

@login_required
def show_dashboard(request):
    recommendations = []

    target_weekly = get_weekly_target_summary(request.user)

    if target_weekly["is_achieved"]:
        recommendations.append("Target minggu ini telah tercapai! Pertahankan pola mobilitas rendah emisi ini.")
    elif target_weekly["actual_reduction_pct"] > 0:
        recommendations.append(f"Sedikit lagi! Kamu sudah memotong {round(target_weekly['actual_reduction_pct'], 1)}% emisi minggu ini.")
    else:
        recommendations.append("Emisi masih lebih tinggi dari minggu lalu. Coba gunakan transportasi umum.")

    transportation_survey = TransportationSurvey.objects.filter(user=request.user)

    for transport in transportation_survey:
        mode = transport.transport_mode
        mode_display = transport.get_transport_mode_display()
        dist = float(transport.daily_distance_km)
        co2 = float(transport.daily_emission_co2)

        if dist <= 2.0 and mode != 'walk_bike':
            recommendations.append(
                f"Penggunaan {mode_display} dengan jarak {dist} km tergolong dekat. Berjalan kaki atau bersepeda bisa menghemat 100% emisi harianmu ({co2:.2f} kg CO₂e)."
            )
        elif dist > 10.0 and mode not in ['krl_mrt_lrt', 'busway']:
            recommendations.append(
                f"Perjalanan sejauh {dist} km menggunakan {mode_display} menghasilkan emisi cukup tinggi ({co2:.2f} kg CO₂e). Coba beralih ke KRL, MRT, atau Busway untuk menekan emisi."
            )
        elif mode in ['motor_ice', 'car_ice']:
            vehicle_type = "Motor" if mode == 'motor_ice' else "Mobil"
            recommendations.append(
                f"Kamu menggunakan {vehicle_type} bensin. Beralih ke {vehicle_type} listrik (EV) dapat memotong emisi harianmu hingga 60%."
            )

    electricity_survey = ElectricitySurvey.objects.filter(user=request.user)

    for electric in electricity_survey:
        device_type = electric.device_type
        watts = float(electric.power_watts)
        hours = electric.daily_usage_hours
        qty = electric.quantity
        label = electric.device_label()

        if device_type == 'ac' and hours >= 8:
            recommendations.append(
                f"Penggunaan AC ({qty} unit) selama {hours} jam/hari menyedot emisi cukup tinggi. Atur suhu ke 24°C-25°C untuk menghemat energi."
            )
        elif watts >= 500.0 and device_type != 'refrigerator':
            recommendations.append(
                f"{label} menggunakan daya besar ({watts}W). Cabut steker saat tidak digunakan agar menghindari daya phantom."
            )
        elif device_type == 'lamp' and qty >= 3:
            recommendations.append(
                f"Kamu mencatat {qty} unit lampu. Pastikan sudah beralih ke lampu LED hemat energi dan matikan saat ruangan kosong."
            )
        elif hours >= 12 and device_type != 'refrigerator':
            recommendations.append(
                f"{label} menyala selama {hours} jam/hari. Mengurangi durasi pemakaian 1-2 jam sehari dapat menekan emisi harianmu."
            )

    reusable_survey = ReusableItemSurvey.objects.filter(user=request.user)

    for item in reusable_survey:
        item_display = item.get_item_type_display()
        uses = item.uses_per_week
        qty = item.quantity

        if uses < 3:
            recommendations.append(
                f"Penggunaan {item_display} hanya {uses} kali seminggu. Tingkatkan penggunaannya agar lebih maksimal mengurangi sampah sekali pakai."
            )

        elif qty >= 2 and uses < 5:
            recommendations.append(
                f"Kamu memiliki {qty} unit {item_display}. Gunakan sesering mungkin agar seimbang dengan footprint produksinya."
            )
    if not reusable_survey:
        recommendations.append(
            "Kamu belum menggunakan Barang Reusable sama sekali. Gunakan Barang Reusable supaya membantu mengurangi emisi yang kamu hasilkan"
        )

    context = {
        'target_data': target_weekly,
        'recommendations': recommendations  
    }
    return render(request, "dashboard-templates/dashboard.html", context)

@login_required
def show_dashboard_survey(request):
    return render(
        request,
        "dashboard-templates/dashboard-survey.html",
        {"form": TransportationSurveyForm(), "electricity_form": ElectricitySurveyForm(), "reusable_form": ReusableItemSurveyForm()},
    )

@login_required
def show_dashboard_weather(request):
    return render(request, "dashboard-templates/dashboard-weather.html")

def _sync_daily_emission_logs(user):
    today = timezone.now().date()

    transport = TransportationSurvey.objects.filter(user=user).aggregate(
        total=Sum('daily_emission_co2')
    )['total'] or 0
    electricity = ElectricitySurvey.objects.filter(user=user).aggregate(
        total=Sum('daily_emission_co2')
    )['total'] or 0
    reusable = ReusableItemSurvey.objects.filter(user=user).aggregate(
        total=Sum('daily_emission_co2')
    )['total'] or 0

    current_total = transport + electricity - reusable

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
@require_GET
def survey_electricity_list_json(request):
    surveys = ElectricitySurvey.objects.filter(user=request.user).order_by('-created_at')
    return JsonResponse({
        'status': 'success',
        'data': [
            {
                'id': str(item.id),
                'device_type': item.device_type,
                'device_label': item.device_label(),
                'device_name': item.device_name or '',
                'quantity': item.quantity,
                'power_watts': str(item.power_watts),
                'daily_usage_hours': str(item.daily_usage_hours),
                'daily_consumption_kwh': str(item.daily_consumption_kwh),
                'daily_emission_co2': str(item.daily_emission_co2),
                'notes': item.notes or '',
            } for item in surveys
        ],
    })

@login_required
@require_POST
def add_electricity_survey(request):
    form = ElectricitySurveyForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    item = form.save(commit=False)
    item.user = request.user
    item.save()
    _sync_daily_emission_logs(request.user)
    return JsonResponse({'status': 'success', 'message': 'Perangkat berhasil ditambahkan.'}, status=201)

@login_required
@require_POST
def edit_electricity_survey(request, survey_id):
    item = get_object_or_404(ElectricitySurvey, pk=survey_id, user=request.user)
    form = ElectricitySurveyForm(request.POST, instance=item)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    form.save()
    _sync_daily_emission_logs(request.user)
    return JsonResponse({'status': 'success', 'message': 'Perangkat berhasil diperbarui.'})

@login_required
@require_POST
def delete_electricity_survey(request, survey_id):
    item = get_object_or_404(ElectricitySurvey, pk=survey_id, user=request.user)
    item.delete()
    _sync_daily_emission_logs(request.user)
    return JsonResponse({'status': 'success', 'message': 'Perangkat berhasil dihapus.'})

@login_required
def emission_dashboard(request):
    user = request.user
    
    # Sinkronisasi data log harian
    _sync_daily_emission_logs(user)

    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=6)

    today_log = DailyEmissionLog.objects.filter(user=user, date=today).first()
    today_emission = float(today_log.total_emission_co2) if today_log else 0.0

    # 2. Total emisi RIIL 7 HARI TERAKHIR dari DailyEmissionLog
    total_7days_emission = float(
        DailyEmissionLog.objects.filter(
            user=user,
            date__gte=seven_days_ago,
            date__lte=today
        ).aggregate(total=Sum('total_emission_co2'))['total'] or 0.0
    )


    daily_survey_distance = float(
        TransportationSurvey.objects.filter(user=user).aggregate(
            total=Sum('daily_distance_km')
        )['total'] or 0.0
    )

    transport_daily = float(
        TransportationSurvey.objects.filter(user=user).aggregate(
            total=Sum('daily_emission_co2')
        )['total'] or 0.0
    )

    electricity_daily = float(
        ElectricitySurvey.objects.filter(user=user).aggregate(
            total=Sum('daily_emission_co2')
        )['total'] or 0.0
    )

    reusable_daily = float(
        ReusableItemSurvey.objects.filter(user=user).aggregate(
            total=Sum('daily_emission_co2')
        )['total'] or 0.0
    )

    # Akumulasi jarak 7 hari 
    total_7days_distance = daily_survey_distance * 7.0

    # Baseline 7 Hari jika seluruh perjalanan menggunakan Mobil Bensin (0.190 kg CO2/km)
    transport_baseline_7days = total_7days_distance * 0.190
    electricity_7days = electricity_daily * 7.0
    baseline_7days_emission = transport_baseline_7days + electricity_7days
    estimated_7days_emission = (transport_daily + electricity_daily) * 7.0

    # 1. Penghematan CO2 Seminggu (Baseline Mobil 7 Hari - Emisi Riil 7 Hari)
    co2_saved_7days = max(0.0, transport_baseline_7days - transport_daily * 7.0)

    # 2. Eco Score Seminggu (Efisiensi emisi seminggu terakhir)
    if baseline_7days_emission > 0:
        score = (1.0 - (estimated_7days_emission / baseline_7days_emission)) * 100
        eco_score = max(0, min(100, round(score)))
    else:
        eco_score = 100

    # 3. Beban Serap Pohon HARI INI (1 pohon dewasa ~ 0.06 kg CO2e / hari)
    trees_saved = round(today_emission / 0.06) if today_emission > 0 else 0

    # 4. Perjalanan Dihindari seminggu (Moda ramah lingkungan x 7 hari)
    eco_friendly_modes = ['walk_bike', 'krl_mrt_lrt', 'busway']
    daily_eco_distance = float(
        TransportationSurvey.objects.filter(
            user=user,
            transport_mode__in=eco_friendly_modes
        ).aggregate(total=Sum('daily_distance_km'))['total'] or 0.0
    )
    avoided_km_7days = daily_eco_distance * 7.0

    context = {
        'today_emission': round(today_emission, 2),       
        'total_7days_emission': round(total_7days_emission, 2), 
        'co2_saved': round(co2_saved_7days, 2),            
        'eco_score': eco_score,                            
        'trees_saved': trees_saved,                        
        'avoided_km': round(avoided_km_7days, 2),    
        'transport_emission_today': round(transport_daily, 2),
        'electricity_emission_today': round(electricity_daily, 2),      
        'reusable_emission_saved_today': round(reusable_daily, 2),
    }
    
    return render(request, 'dashboard-templates/dashboard-emission.html', context)

@login_required
def emission_chart_api(request):
    user = request.user
    _sync_daily_emission_logs(user)

    today = timezone.now().date()
    chart_dates = []
    chart_values = []
    day_names = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']

    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        log = DailyEmissionLog.objects.filter(user=user, date=target_date).first()
        val = float(log.total_emission_co2) if log else 0.0
        
        label = f"{day_names[target_date.weekday()]} ({target_date.day})"
        chart_dates.append(label)
        chart_values.append(val)

    return JsonResponse({
        'status': 'success',
        'labels': chart_dates,
        'datasets': [
            {
                'label': 'Jejak Karbon (kg CO2e)',
                'data': chart_values,
            }
        ]
    })

def show_faq(request):
    faq_list = FAQ.objects.filter(
        is_active=True
    ).order_by("order", "id")

    return render(request, "faq.html", {
        "faq_list": faq_list,
    })

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



def admin_dashboard(request):
    # Data dummy (contoh)
    context = {
        'admin_name' : 'Sofie',
        'npm' : '12345',
        'total_pengguna' : 5,
        'total_emisi' : '3.482',
        'aktivitas_hari_ini' : 542,
        'total_kota' : 12,
    }
    return render(request, "admin-templates/admin-dashboard.html", context)

def kelola_pengguna(request):
    return render(request, "admin-templates/kelola-pengguna.html")

## @login_required
def kelola_faq(request):
    faq_list = FAQ.objects.all().order_by("order", "id")
    context = {
        "faq_list": faq_list,
        "admin_name": (
            request.user.get_full_name() or request.user.username
            if request.user.is_authenticated
            else "Administrator"
        ),
    }

    return render(request, "admin-templates/kelola-faq.html", context)

## @login_required
@require_POST
def add_faq(request):
    question = request.POST.get("question", "").strip()
    answer = request.POST.get("answer", "").strip()

    if not question or not answer:
        messages.error(request, "Pertanyaan dan jawaban wajib diisi.")
        return redirect('main:kelola_faq')
    

    FAQ.objects.create (
        question=question,
        answer=answer,
        order=(FAQ.objects.order_by("-order").values_list("order", flat=True).first() or 0) + 1,
        is_active=True,
    )

    messages.success(request, "FAQ berhasil ditambahkan.")
    return redirect('main:kelola_faq')

## @login_required
@require_POST
def edit_faq(request, faq_id):
    faq = get_object_or_404(FAQ, id=faq_id)

    question = request.POST.get("question", "").strip()
    answer = request.POST.get("answer", "").strip()

    if not question or not answer:
        messages.error(request, "Pertanyaan dan jawaban wajib diisi.")
        return redirect("main:kelola_faq")

    faq.question = question
    faq.answer = answer
    faq.save()

    messages.success(request, "FAQ berhasil diperbarui")
    return redirect("main:kelola_faq")

## @login_required
@require_POST
def delete_faq(request, faq_id):
    faq = get_object_or_404(FAQ, id=faq_id)
    faq.delete()

    messages.success(request, "FAQ berhasil dihapus.")
    return redirect('main:kelola_faq')

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
@require_GET
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

@login_required
def survey_reusable_list_json(request):
    surveys = ReusableItemSurvey.objects.filter(user=request.user).order_by("-created_at")
    data = [
        {
            "id": str(item.id),
            "item": item.get_item_type_display(),
            "item_val": item.item_type,
            "quantity": item.quantity,
            "uses_per_week": item.uses_per_week,
            "notes": item.notes or "",
            "daily_emission_co2": float(item.daily_emission_co2),
        }
        for item in surveys
    ]
    return JsonResponse({"status": "success", "data": data})  
 
@login_required
def add_reusable_survey(request):
    if request.method == "POST":
        form = ReusableItemSurveyForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            _sync_daily_emission_logs(request.user)
            return JsonResponse({
                'status': 'success',
                'message': 'Data berhasil ditambahkan.'
            }, status=201)
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
 
    return JsonResponse({"status": "error", "message": "Method tidak diizinkan."}, status=405)

@login_required
def edit_reusable_survey(request, survey_id):
    item = get_object_or_404(ReusableItemSurvey, id=survey_id, user=request.user)
 
    if request.method == "POST":
        form = ReusableItemSurveyForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            _sync_daily_emission_logs(request.user)
            return JsonResponse({'status': 'success', 'message': 'Data berhasil diperbarui.'}, status=200)
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
 
    return JsonResponse({"status": "error", "message": "Method tidak diizinkan."}, status=405)
 
 
@login_required
def delete_reusable_survey(request, survey_id):
    item = get_object_or_404(ReusableItemSurvey, id=survey_id, user=request.user)
 
    if request.method == "POST":
        item.delete()
        _sync_daily_emission_logs(request.user)
        return JsonResponse({'status': 'success', 'message': 'Data berhasil dihapus.'}, status=200)
 
    return JsonResponse({"status": "error", "message": "Method tidak diizinkan."}, status=405)