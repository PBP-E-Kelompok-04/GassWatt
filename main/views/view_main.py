from django.shortcuts import render
from django.http import JsonResponse

from ..models import (
    FAQ,
)

def show_home(request):
    return render(request, "main-templates/home.html")
    
def show_faq(request):
    faq_list = FAQ.objects.filter(
        is_active=True
    ).order_by("order", "id")

    return render(request, "main-templates/faq.html", {
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

    return render(request, "main-templates/about.html", context)

