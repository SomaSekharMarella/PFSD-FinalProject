from django.urls import path

from . import views


app_name = "adminportal"


urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/new/", views.customer_create, name="customer_create"),
    path("customers/<int:user_id>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:user_id>/profile/", views.profile_update, name="profile_update"),
    path("bills/new/", views.bill_create, name="bill_create"),
    path("subscriptions/new/", views.subscription_create, name="subscription_create"),
    path("subscriptions/<int:subscription_id>/toggle/", views.subscription_toggle, name="subscription_toggle"),
]