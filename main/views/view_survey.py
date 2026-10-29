from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET, require_POST

from ..models.model_survey import (
    TransportationSurvey,
    ElectricitySurvey,
    ReusableItemSurvey,
)


from ..forms import (
    TransportationSurveyForm,
    ElectricitySurveyForm,
    ReusableItemSurveyForm,
)

from .view_dashboard import (
    _sync_daily_emission_logs
)

@login_required
@require_GET
def show_dashboard_survey(request):
    return render(
        request,
        "dashboard-templates/dashboard-survey.html",
        {"form": TransportationSurveyForm(), "electricity_form": ElectricitySurveyForm(), "reusable_form": ReusableItemSurveyForm()},
    )

@login_required
@require_GET
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
def survey_reusable_list_json(request):
    item_type = request.GET.get("item_type", "").strip()
    surveys = ReusableItemSurvey.objects.filter(user=request.user)
    if item_type in dict(ReusableItemSurvey.ITEM_CHOICES):
        surveys = surveys.filter(item_type=item_type)
    surveys = surveys.order_by("-created_at")
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