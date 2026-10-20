from django.http import JsonResponse
from django.shortcuts import render
from main.models import FAQ

def show_home(request):
    return render(request, "home.html")

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
