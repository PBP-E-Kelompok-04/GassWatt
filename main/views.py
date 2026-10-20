from django.shortcuts import render

def show_home(request):
    return render(request, "home.html")

def show_dashboard(request):
    return render(request, "dashboard-templates/dashboard.html")

# def show_dashboard_survey(request):
#     return render(request, "dashboard-templates/dashboard-survey.html")

def show_dashboard_weather(request):
    return render(request, "dashboard-templates/dashboard-weather.html")

# def show_dashboard_emission(request):
#     return render(request, "dashboard-templates/dashboard-emission.html")

from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum

from .models import TransportationSurvey, DailyEmissionLog
from .forms import TransportationSurveyForm


def _sync_daily_emission_logs(user):
    """
    Menghitung TOTAL akumulasi emisi dari SEMUA moda transportasi aktif milik pengguna,
    kemudian menyimpannya ke log harian.
    """
    today = timezone.now().date()
    
    # Penjumlahan emisi dari seluruh segmen perjalanan pengguna
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
        
        # Mengisi gap tanggal jika ada hari pengguna tidak membuka aplikasi
        start_date = last_log.date + timedelta(days=1)
        while start_date < today:
            DailyEmissionLog.objects.get_or_create(
                user=user,
                date=start_date,
                defaults={'total_emission_co2': last_log.total_emission_co2}
            )
            start_date += timedelta(days=1)


@login_required
def survey_transport_list(request):
    """
    Menampilkan daftar segmen perjalanan harian pengguna & total emisi harian
    """
    _sync_daily_emission_logs(request.user)

    surveys = TransportationSurvey.objects.filter(user=request.user)
    form = TransportationSurveyForm()

    # Total emisi harian gabungan seluruh moda
    total_daily_emission = surveys.aggregate(Sum('daily_emission_co2'))['daily_emission_co2__sum'] or 0

    context = {
        'surveys': surveys,
        'form': form,
        'total_daily_emission': total_daily_emission,
    }
    return render(request, 'survey/transport_list.html', context)


@login_required
def add_transport_survey(request):
    if request.method == 'POST':
        form = TransportationSurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.user = request.user
            survey.save()

            _sync_daily_emission_logs(request.user)
            return redirect('survey_transport_list')
    return redirect('survey_transport_list')


@login_required
def edit_transport_survey(request, survey_id):
    survey = get_object_or_404(TransportationSurvey, id=survey_id, user=request.user)

    if request.method == 'POST':
        form = TransportationSurveyForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            _sync_daily_emission_logs(request.user)
            return redirect('survey_transport_list')
    else:
        form = TransportationSurveyForm(instance=survey)

    context = {
        'form': form,
        'survey': survey,
    }
    return render(request, 'survey/transport_edit.html', context)


@login_required
def delete_transport_survey(request, survey_id):
    survey = get_object_or_404(TransportationSurvey, id=survey_id, user=request.user)
    
    if request.method == 'POST':
        survey.delete()
        _sync_daily_emission_logs(request.user)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Data berhasil dihapus.'})
            
        return redirect('survey_transport_list')
        
    return redirect('survey_transport_list')


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
    return render(request, 'emission/dashboard.html', context)