
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import TransportationSurvey, DailyEmissionLog
from .forms import TransportationSurveyForm


from django.http import JsonResponse
from django.shortcuts import render
from main.models import FAQ


def show_home(request):
    return render(request, "home.html")

def show_dashboard(request):
    return render(request, "dashboard-templates/dashboard.html")


@login_required
def show_dashboard_survey(request):
    return render(
        request,
        "dashboard-templates/dashboard-survey.html",
        {"form": TransportationSurveyForm()},
    )


def show_dashboard_weather(request):
    return render(request, "dashboard-templates/dashboard-weather.html")

def _sync_daily_emission_logs(user):
    today = timezone.now().date()
    
    current_total = TransportationSurvey.objects.filter(user=user).aggregate(
        total=Sum('daily_emission_co2')
    )['total'] or 0.000

    last_log = DailyEmissionLog.objects.filter(user=user).order_by('-date').first()

    if not last_log:
        DailyEmissionLog.objects.create(user=user, date=today, total_emission_co2=current_total)
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
                defaults={'total_emission_co2': last_log.total_emission_co2}
            )
            start_date += timedelta(days=1)

@login_required
def survey_transport_list_json(request):
    surveys = TransportationSurvey.objects.filter(user=request.user).order_by("-created_at")
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
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    return JsonResponse({"status": "error", "message": "Method tidak diizinkan."}, status=405)


@login_required
def edit_transport_survey(request, survey_id):
    survey = get_object_or_404(TransportationSurvey, id=survey_id, user=request.user)

    if request.method == "POST":
        form = TransportationSurveyForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            _sync_daily_emission_logs(request.user)
            return JsonResponse({'status': 'success', 'message': 'Data berhasil diperbarui.'}, status=200)
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    return JsonResponse({"status": "error", "message": "Method tidak diizinkan."}, status=405)


@login_required
def delete_transport_survey(request, survey_id):
    survey = get_object_or_404(TransportationSurvey, id=survey_id, user=request.user)
    
    if request.method == "POST":
        survey.delete()
        _sync_daily_emission_logs(request.user)
        return JsonResponse({'status': 'success', 'message': 'Data berhasil dihapus.'}, status=200)
        
    return JsonResponse({"status": "error", "message": "Method tidak diizinkan."}, status=405)

@login_required
def emission_dashboard(request):
    user = request.user
    
    # Sinkronisasi data log harian
    _sync_daily_emission_logs(user)

    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=6)

    # ---------------------------------------------------
    # Step 1: Data Emisi Harian & 7 Hari
    # ---------------------------------------------------
    # 1. Emisi riil khusus HARI INI (kg CO2e)
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

    # ---------------------------------------------------
    # Step 2: Indikator Berbasis Baseline Seminggu (7 Hari)
    # ---------------------------------------------------
    # Total jarak harian survey milik user (asumsi rutinitas harian diisi via survey)
    daily_survey_distance = float(
        TransportationSurvey.objects.filter(user=user).aggregate(
            total=Sum('daily_distance_km')
        )['total'] or 0.0
    )

    # Akumulasi jarak 7 hari (rutinitas harian x 7 hari)
    total_7days_distance = daily_survey_distance * 7.0

    # Baseline 7 Hari jika seluruh perjalanan menggunakan Mobil Bensin (0.190 kg CO2/km)
    baseline_7days_emission = total_7days_distance * 0.190
    
    # 1. Penghematan CO2 Seminggu (Baseline Mobil 7 Hari - Emisi Riil 7 Hari)
    co2_saved_7days = max(0.0, baseline_7days_emission - total_7days_emission)

    # 2. Eco Score Seminggu (Efisiensi emisi seminggu terakhir)
    if baseline_7days_emission > 0:
        score = (1.0 - (total_7days_emission / baseline_7days_emission)) * 100
        eco_score = max(0, min(100, round(score)))
    else:
        eco_score = 100

    # 3. Beban Serap Pohon HARI INI (1 pohon dewasa ~ 0.06 kg CO2e / hari)
    trees_saved = round(today_emission / 0.06) if today_emission > 0 else 0

    # 4. Perjalanan Dihindari SEMINGGU (Moda ramah lingkungan x 7 hari)
    eco_friendly_modes = ['walk_bike', 'krl_mrt_lrt', 'busway']
    daily_eco_distance = float(
        TransportationSurvey.objects.filter(
            user=user,
            transport_mode__in=eco_friendly_modes
        ).aggregate(total=Sum('daily_distance_km'))['total'] or 0.0
    )
    avoided_km_7days = daily_eco_distance * 7.0

    # ---------------------------------------------------
    # Step 3: Kirim ke Context Template
    # ---------------------------------------------------
    context = {
        'today_emission': round(today_emission, 1),       # Harian (kg CO2e)
        'total_7days_emission': round(total_7days_emission, 1), # Seminggu (kg CO2e)
        'co2_saved': round(co2_saved_7days, 1),            # Seminggu (kg CO2e)
        'eco_score': eco_score,                            # Seminggu (0-100)
        'trees_saved': trees_saved,                        # Harian (Pohon/Hari)
        'avoided_km': round(avoided_km_7days, 1),          # Seminggu (Km)
    }
    
    return render(request, 'dashboard-templates/dashboard-emission.html', context)

# @login_required
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
    faq_list = FAQ.objects.filter(is_active=True)
    context = {
        "faq_list" : faq_list,
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

