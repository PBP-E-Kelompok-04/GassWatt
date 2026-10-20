from django.urls import path

from main.views import(
    show_home,
    show_faq,
    show_about,
)

app_name = "main"

urlpatterns = [
    path("", show_home, name="show_home"),
    path("faq/", show_faq, name="show_faq"),
    path("about/", show_about, name="show_about"),
]