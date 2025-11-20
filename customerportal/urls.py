from django.urls import path

from . import views


app_name = "customerportal"


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("history/", views.payment_history, name="payment_history"),
    path("bills/<int:bill_id>/pay/", views.pay_bill, name="pay_bill"),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("subscriptions/new/", views.subscription_create, name="subscription_create"),
    path("subscriptions/<int:subscription_id>/toggle/", views.subscription_toggle, name="subscription_toggle"),
]