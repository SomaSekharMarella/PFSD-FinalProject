from django.contrib import admin

from .models import Bill, Profile, Subscription, Transaction


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "phone")
    search_fields = ("user__username", "full_name", "phone")


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "amount", "due_date", "status")
    list_filter = ("status", "bill_type")
    search_fields = ("title", "user__username", "bill_type")
    autocomplete_fields = ("user", "subscription", "created_by")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "amount", "next_renewal_date", "active")
    list_filter = ("active", "created_by_role")
    search_fields = ("name", "user__username")
    autocomplete_fields = ("user",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("bill", "user", "amount", "payment_date", "method", "status")
    list_filter = ("status", "method")
    search_fields = ("bill__title", "user__username", "method")
    autocomplete_fields = ("bill", "user", "processed_by")
