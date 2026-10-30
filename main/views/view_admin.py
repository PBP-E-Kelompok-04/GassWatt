from datetime import timedelta
import json

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .view_decorators import admin_required, admin_required_json
from ..models import (
    TransportationSurvey,
    ElectricitySurvey,
    ReusableItemSurvey,
    FAQ,
    SavedLocation,
)

User = get_user_model()

@admin_required
@require_GET
def admin_dashboard(request):

    today_local = timezone.localtime(timezone.now()).date()
    current_year = today_local.year

    # 1. Total pengguna yang terdaftar
    total_users = User.objects.count()

    # 2. Total Emisi Tercatat
    emisi_listrik = ElectricitySurvey.objects.aggregate(total=Sum('daily_emission_co2'))['total'] or 0
    emisi_transport = TransportationSurvey.objects.aggregate(total=Sum('daily_emission_co2'))['total'] or 0
    emisi_reusable = ReusableItemSurvey.objects.aggregate(total=Sum('daily_emission_co2'))['total'] or 0
    
    total_emisi = round(float(emisi_listrik) + float(emisi_transport) + float(emisi_reusable), 2)

    # Total aktivitas
    today_transport = TransportationSurvey.objects.filter(created_at__date=today_local).count()
    today_listrik = ElectricitySurvey.objects.filter(created_at__date=today_local).count()
    today_reusable = ReusableItemSurvey.objects.filter(created_at__date=today_local).count()
    today_lokasi = SavedLocation.objects.filter(created_at__date=today_local).count()

    total_aktivitas_today = today_transport + today_listrik + today_reusable + today_lokasi

    # 4. Total lokasi/Kota pengguna
    total_lokasi = SavedLocation.objects.count()

    # DATA BULANAN
    months_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
    monthly_users = []

    # Akumulasi pengguna terdatar hingga akhir bulan masing-masing
    for month in range(1, 13):
        user_count = User.objects.filter(
            date_joined__year__lte=current_year,
            date_joined__month__lte=month
        ).count()
        monthly_users.append(user_count)

    # --- 2. DATA HARIAN (7 Hari Terakhir) ---
    days_map = {0: 'Sen', 1: 'Sel', 2: 'Rab', 3: 'Kam', 4: 'Jum', 5: 'Sab', 6: 'Min'}
    daily_labels = []
    daily_activities = []

    for i in range(6, -1, -1):
        target_date = today_local - timedelta(days=i)
        daily_labels.append(f"{days_map[target_date.weekday()]} ({target_date.day})")

        act_count = (
            TransportationSurvey.objects.filter(created_at__date=target_date).count() +
            ElectricitySurvey.objects.filter(created_at__date=target_date).count() +
            ReusableItemSurvey.objects.filter(created_at__date=target_date).count() +
            SavedLocation.objects.filter(created_at__date=target_date).count()
        )
        daily_activities.append(act_count)

    context = {
        "admin_name": (
                    request.user.get_full_name() or request.user.username
                    if request.user.is_authenticated
                    else "Administrator"
                ),
        'total_users' : total_users,
        'total_emisi' : total_emisi,
        'total_aktivitas_today' : total_aktivitas_today,
        'total_lokasi' : total_lokasi,
        # Data untuk chart
        'emisi_listrik': emisi_listrik,
        'emisi_transport' : emisi_transport,
        'emisi_reusable' : emisi_reusable,

        # Data JSON
        'monthly_labels_json': json.dumps(months_labels),
        'monthly_users_json': json.dumps(monthly_users),
        'daily_labels_json': json.dumps(daily_labels),
        'daily_activities_json': json.dumps(daily_activities),
    }

    return render(request, "admin-templates/admin-dashboard.html", context)

@admin_required
def kelola_pengguna(request):
    users = User.objects.all().order_by('-date_joined')
    user_list = []

    for u in users:
        # Hitung akumulasi emisi per user dari 3 survey
        e_electricity = ElectricitySurvey.objects.filter(user=u).aggregate(s=Sum('daily_emission_co2'))['s'] or 0
        e_transport = TransportationSurvey.objects.filter(user=u).aggregate(s=Sum('daily_emission_co2'))['s'] or 0
        e_reusable = ReusableItemSurvey.objects.filter(user=u).aggregate(s=Sum('daily_emission_co2'))['s'] or 0
        
        total_emission = round(float(e_electricity) + float(e_transport) + float(e_reusable), 1)
        
        user_list.append({
            'id': u.id,
            'nama' : u.get_full_name() or u.username,
            'email' : u.email or "-",
            'role' : 'Admin' if u.is_staff or u.is_superuser else 'Pengguna',
            'total_emisi' : total_emission,
            'status' : 'Aktif' if u.is_active else 'Inaktif',
            'is_self' : u == request.user
        })

    context = {
        'admin_name' : request.user.get_full_name() or request.user.username,
        'users' : user_list,
        'total_count' : len(user_list),
    }

    return render(request, "admin-templates/kelola-pengguna.html", context)


@admin_required_json
@require_POST
def delete_user(request, user_id):
    """Endpoint untuk menghapus/menonaktifkan pengguna"""
    try:
        user_to_delete = User.objects.get(id=user_id)
        if user_to_delete == request.user:
            return JsonResponse({'status': 'error', 'message': 'Tidak bisa menghapus akun sendiri!'}, status=400)

        user_to_delete.delete()
        return JsonResponse({'status': 'success', 'message': 'Pengguna berhasil dihapus.'})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Pengguna tidak ditemukan.'}, status=404)

@admin_required
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

@admin_required
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

@admin_required
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

@admin_required
@require_POST
def delete_faq(request, faq_id):
    faq = get_object_or_404(FAQ, id=faq_id)
    faq.delete()

    messages.success(request, "FAQ berhasil dihapus.")
    return redirect('main:kelola_faq')