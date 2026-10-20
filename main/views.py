from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import TransportationSurvey, DailyEmissionLog
from .forms import TransportationSurveyForm


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
    _sync_daily_emission_logs(request.user)

    logs = DailyEmissionLog.objects.filter(user=request.user)

    chart_dates = [log.date.strftime('%d %b') for log in logs]
    chart_values = [float(log.total_emission_co2) for log in logs]

    context = {
        'chart_dates': chart_dates,
        'chart_values': chart_values,
        'logs': logs,
    }
    return render(request, "dashboard-templates/dashboard-emission.html", context)