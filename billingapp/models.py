from __future__ import annotations

import calendar
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

User = get_user_model()

BILL_TYPE_ELECTRICITY = "electricity"
BILL_TYPE_FEES = "fees"
BILL_TYPE_SUBSCRIPTION = "subscription"
BILL_TYPE_OTHER = "other"

BILL_TYPE_CHOICES = (
    (BILL_TYPE_ELECTRICITY, "Electricity"),
    (BILL_TYPE_FEES, "Fees"),
    (BILL_TYPE_SUBSCRIPTION, "Subscription"),
    (BILL_TYPE_OTHER, "Other"),
)


def _add_month(reference_date: date) -> date:
    """Return a date advanced by one month, preserving the day when possible."""

    year = reference_date.year
    month = reference_date.month + 1
    if month > 12:
        month = 1
        year += 1

    last_day = calendar.monthrange(year, month)[1]
    day = min(reference_date.day, last_day)
    return date(year, month, day)


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return self.full_name or self.user.get_username()


class Subscription(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_USER = "user"
    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_USER, "User"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    bill_type = models.CharField(max_length=40, choices=BILL_TYPE_CHOICES, default=BILL_TYPE_SUBSCRIPTION)
    next_renewal_date = models.DateField()
    active = models.BooleanField(default=True)
    created_by_role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_ADMIN)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-active", "next_renewal_date"]

    def __str__(self) -> str:
        return f"{self.name} - {self.user.username}"

    def advance_next_renewal(self) -> None:
        self.next_renewal_date = _add_month(self.next_renewal_date)


class Bill(models.Model):
    STATUS_UNPAID = "unpaid"
    STATUS_PAID = "paid"
    STATUS_CHOICES = (
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_PAID, "Paid"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bills")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="bills")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    due_date = models.DateField()
    bill_type = models.CharField(max_length=40, choices=BILL_TYPE_CHOICES, default=BILL_TYPE_SUBSCRIPTION)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_UNPAID)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_bills")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "due_date"],
                name="unique_subscription_bill_per_cycle",
                condition=Q(subscription__isnull=False),
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.user.username})"

    def mark_paid(self, paid_by: User | None = None, method: str = "Simulated") -> "Transaction":
        if self.status == self.STATUS_PAID:
            try:
                return self.transactions.latest("payment_date")
            except Transaction.DoesNotExist:  # type: ignore[name-defined]
                pass

        self.status = self.STATUS_PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at", "updated_at"])

        return Transaction.objects.create(
            user=self.user,
            bill=self,
            amount=self.amount,
            method=method,
            status=Transaction.STATUS_SUCCESS,
            processed_by=paid_by,
        )


class Transaction(models.Model):
    METHOD_SIMULATED = "Simulated"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=40, default=METHOD_SIMULATED)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="processed_transactions"
    )

    class Meta:
        ordering = ["-payment_date"]
        get_latest_by = "payment_date"

    def __str__(self) -> str:
        return f"{self.bill.title} - {self.amount}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance: User, created: bool, **kwargs) -> None:
    if created:
        Profile.objects.create(user=instance, full_name=instance.get_full_name())
    else:
        Profile.objects.get_or_create(user=instance)
