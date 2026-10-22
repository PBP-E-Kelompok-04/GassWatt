from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User

from .models import TransportationSurvey, DailyEmissionLog
from .forms import TransportationSurveyForm
from main.models import FAQ

#=========================================================================================#
#                                   LOGIN VIEWS                                           #
#=========================================================================================#
@require_GET
def show_login(request):
    return render(request, "login.html")
 
@require_POST
def login_user(request):
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
 
    user = authenticate(request, username=username, password=password)
    if user is None:
        messages.error(request, "Username atau password invalid.")
        return redirect("main:show_login")
    login(request, user)

    if user.is_staff or user.is_superuser:
        #TODO: Change redirect to admin dashboard
        return redirect("main:show_dashboard_weather")
    return redirect("main:show_dashboard_weather")

 
@require_GET
def show_register(request):
    return render(request, "register.html")
 
@require_POST
def register_user(request):
    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")
 
    if not username or not password:
        messages.error(request, "Username dan password dibutuhkan.")
        return redirect("main:show_register")
 
    if password != confirm_password:
        messages.error(request, "Password tidak sama.")
        return redirect("main:show_register")
 
    if User.objects.filter(username=username).exists():
        messages.error(request, "Username sudah diambil.")
        return redirect("main:show_register")
 
    User.objects.create_user(username=username, email=email, password=password)
    messages.success(request, "Akun telah dibuat. Anda bisa login.")
    return redirect("main:show_login")


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

