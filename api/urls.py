from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("sessions/", views.SessionAPI.as_view(), name="sessions"),            # POST login, DELETE logout
    path("users/", views.UsersAPI.as_view(), name="users"),                    # POST register
    path("users/me/", views.MeAPI.as_view(), name="me"),                       # GET, PATCH, DELETE
    path("users/me/password/", views.PasswordAPI.as_view(), name="password"),  # PUT
    path("validate-field/", views.ValidateFieldAPI.as_view(), name="validate_field"),
]