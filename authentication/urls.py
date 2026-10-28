from django.urls import path

from .views import (
    show_login,
    login_user,
    show_register,
    register_user,
    logout_user,
)

urlpatterns = [
    path("login/", show_login, name="show_login"),
    path("login/submit/", login_user, name="login_user"),
    path("register/", show_register, name="show_register"),
    path("register/submit/", register_user, name="register_user"),
    path("logout/", logout_user, name="logout_user"),
]
