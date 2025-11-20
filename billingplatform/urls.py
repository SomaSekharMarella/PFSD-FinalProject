from django.contrib import admin
from django.urls import include, path

from . import views


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("admin/", include("adminportal.urls")),
    path("portal/", include("customerportal.urls")),
]
