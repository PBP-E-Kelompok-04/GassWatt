from django.shortcuts import render

def show_home(request):
    return render(request, "home.html")

def show_dashboard(request):
    return render(request, "dashboard-templates/dashboard.html")

def show_dashboard_survey(request):
    return render(request, "dashboard-templates/dashboard-survey.html")

def show_dashboard_weather(request):
    return render(request, "dashboard-templates/dashboard-weather.html")

def show_dashboard_emission(request):
    return render(request, "dashboard-templates/dashboard-emission.html")