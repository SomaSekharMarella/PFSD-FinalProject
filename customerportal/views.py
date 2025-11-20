from __future__ import annotations

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from billingapp.forms import ProfileForm, SelfSubscriptionForm
from billingapp.models import Bill, Subscription, Transaction
from billingapp.utils import ensure_subscription_bills


def _ensure_customer(user):
    if user.is_staff:
        return redirect("adminportal:dashboard")
    return None


@login_required
def dashboard(request):
    redirect_response = _ensure_customer(request.user)
    if redirect_response:
        return redirect_response

    ensure_subscription_bills(request.user)

    pending_bills = request.user.bills.filter(status=Bill.STATUS_UNPAID).order_by("due_date")
    today = timezone.now().date()
    due_soon_bills = pending_bills.filter(due_date__gte=today, due_date__lte=today + timedelta(days=7))

    recent_transactions = request.user.transactions.select_related("bill")[:10]
    subscriptions = request.user.subscriptions.all()
    active_subscriptions = subscriptions.filter(active=True)
    recent_paid_bills = request.user.bills.filter(status=Bill.STATUS_PAID).order_by("-paid_at")[:5]

    total_paid = request.user.transactions.aggregate(total=Sum("amount"))["total"] or 0
    total_pending = pending_bills.aggregate(total=Sum("amount"))["total"] or 0

    monthly_spend = (
        request.user.transactions.annotate(month=TruncMonth("payment_date"))
        .values("month")
        .order_by("month")
        .annotate(total=Sum("amount"))
    )

    category_spend = (
        request.user.bills.filter(status=Bill.STATUS_PAID)
        .values("bill_type")
        .annotate(total=Sum("amount"))
        .order_by("bill_type")
    )

    monthly_labels = [entry["month"].strftime("%b %Y") for entry in monthly_spend if entry["month"]]
    monthly_values = [float(entry["total"]) for entry in monthly_spend]
    category_labels = [entry["bill_type"] or "Other" for entry in category_spend]
    category_values = [float(entry["total"]) for entry in category_spend]

    context = {
        "pending_bills": pending_bills,
        "recent_transactions": recent_transactions,
        "subscriptions": subscriptions,
        "active_subscriptions": active_subscriptions,
        "active_subscription_count": active_subscriptions.count(),
        "recent_paid_bills": recent_paid_bills,
        "due_soon_bills": due_soon_bills,
        "due_soon_ids": list(due_soon_bills.values_list("id", flat=True)),
        "total_paid": float(total_paid),
        "total_pending": float(total_pending),
        "monthly_data": json.dumps({"labels": monthly_labels, "values": monthly_values}),
        "category_data": json.dumps({"labels": category_labels, "values": category_values}),
    }
    return render(request, "customer/dashboard.html", context)


@login_required
def pay_bill(request, bill_id):
    redirect_response = _ensure_customer(request.user)
    if redirect_response:
        return redirect_response

    bill = get_object_or_404(Bill, pk=bill_id, user=request.user)

    if request.method == "POST":
        bill.mark_paid(paid_by=request.user)
        messages.success(request, f"Bill '{bill.title}' marked as paid.")
        return redirect("customerportal:dashboard")

    return render(request, "customer/pay_bill_confirm.html", {"bill": bill})


@login_required
def subscriptions(request):
    redirect_response = _ensure_customer(request.user)
    if redirect_response:
        return redirect_response

    ensure_subscription_bills(request.user)
    subs = request.user.subscriptions.all()
    return render(request, "customer/subscriptions.html", {"subscriptions": subs})


@login_required
def subscription_create(request):
    redirect_response = _ensure_customer(request.user)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = SelfSubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            subscription.created_by_role = Subscription.ROLE_USER
            subscription.save()
            ensure_subscription_bills(request.user)
            messages.success(request, "Subscription created successfully.")
            return redirect("customerportal:subscriptions")
    else:
        form = SelfSubscriptionForm()

    return render(request, "customer/subscription_form.html", {"form": form})


@login_required
def subscription_toggle(request, subscription_id):
    redirect_response = _ensure_customer(request.user)
    if redirect_response:
        return redirect_response

    subscription = get_object_or_404(Subscription, pk=subscription_id, user=request.user)
    subscription.active = not subscription.active
    subscription.save(update_fields=["active", "updated_at"])
    status = "activated" if subscription.active else "paused"
    messages.info(request, f"Subscription '{subscription.name}' {status}.")
    return redirect("customerportal:subscriptions")


@login_required
def payment_history(request):
    redirect_response = _ensure_customer(request.user)
    if redirect_response:
        return redirect_response

    transactions = request.user.transactions.select_related("bill")
    success_count = transactions.filter(status=Transaction.STATUS_SUCCESS).count()
    failed_count = transactions.filter(status=Transaction.STATUS_FAILED).count()
    total_amount = transactions.aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "transactions": transactions,
        "success_count": success_count,
        "failed_count": failed_count,
        "total_amount": total_amount,
    }
    return render(request, "customer/payment_history.html", context)


@login_required
def profile(request):
    redirect_response = _ensure_customer(request.user)
    if redirect_response:
        return redirect_response

    profile = request.user.profile

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("customerportal:profile")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "customer/profile.html", {"form": form})
