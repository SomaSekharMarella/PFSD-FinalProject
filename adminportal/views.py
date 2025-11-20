from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from billingapp.forms import BillForm, ProfileForm, SubscriptionForm, UserCreationWithProfileForm
from billingapp.models import Bill, Profile, Subscription, Transaction
from billingapp.utils import ensure_subscription_bills


User = get_user_model()


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please sign in to continue.")
            return redirect("login")
        if not request.user.is_staff:
            messages.error(request, "You do not have permission to access the admin workspace.")
            return redirect("customerportal:dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped


@admin_required
def dashboard(request):
    ensure_subscription_bills()

    total_customers = User.objects.filter(is_staff=False).count()
    pending_bills_count = Bill.objects.filter(status=Bill.STATUS_UNPAID).count()
    total_outstanding = Bill.objects.filter(status=Bill.STATUS_UNPAID).aggregate(total=Sum("amount"))["total"] or 0
    total_paid = Transaction.objects.aggregate(total=Sum("amount"))["total"] or 0

    recent_bills = (
        Bill.objects.select_related("user")
        .order_by("-created_at")[:6]
    )

    recent_transactions = Transaction.objects.select_related("bill", "user").all()[:10]
    open_bills = (
        Bill.objects.filter(status=Bill.STATUS_UNPAID)
        .select_related("user")
        .order_by("due_date")[:10]
    )

    subscription_stats = (
        Subscription.objects.values("active")
        .annotate(total=Count("id"))
        .order_by("-active")
    )
    
    context = {
        "total_customers": total_customers,
        "pending_bills_count": pending_bills_count,
        "total_outstanding": total_outstanding,
        "total_paid": total_paid,
        "recent_bills": recent_bills,
        "recent_transactions": recent_transactions,
        "open_bills": open_bills,
        "subscription_stats": subscription_stats,
    }
    return render(request, "admin/dashboard.html", context)


@admin_required
def customer_list(request):
    customers = (
        User.objects.filter(is_staff=False)
        .select_related("profile")
        .annotate(
            unpaid_bills=Count("bills", filter=Q(bills__status=Bill.STATUS_UNPAID)),
            total_due=Sum("bills__amount", filter=Q(bills__status=Bill.STATUS_UNPAID)),
        )
    )
    return render(request, "admin/customer_list.html", {"customers": customers})


@admin_required
def customer_create(request):
    if request.method == "POST":
        form = UserCreationWithProfileForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Customer '{user.username}' created successfully.")
            return redirect("adminportal:customer_list")
    else:
        form = UserCreationWithProfileForm()

    return render(request, "admin/customer_form.html", {"form": form})


@admin_required
def customer_detail(request, user_id):
    customer = get_object_or_404(User.objects.select_related("profile"), pk=user_id, is_staff=False)
    ensure_subscription_bills(customer)

    bills = customer.bills.select_related("subscription").order_by("status", "due_date")
    subscriptions = customer.subscriptions.all()
    transactions = customer.transactions.select_related("bill")[:20]

    context = {
        "customer": customer,
        "bills": bills,
        "subscriptions": subscriptions,
        "transactions": transactions,
    }
    return render(request, "admin/customer_detail.html", context)


@admin_required
def bill_create(request):
    if request.method == "POST":
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.created_by = request.user
            bill.save()
            messages.success(request, f"Bill '{bill.title}' assigned to {bill.user.username}.")
            return redirect("adminportal:customer_list")
    else:
        form = BillForm()

    form.fields["user"].queryset = User.objects.filter(is_staff=False)
    return render(request, "admin/bill_form.html", {"form": form})


@admin_required
def subscription_create(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.created_by_role = Subscription.ROLE_ADMIN
            subscription.save()
            ensure_subscription_bills(subscription.user)
            messages.success(request, f"Subscription '{subscription.name}' created.")
            return redirect("adminportal:customer_list")
    else:
        form = SubscriptionForm()

    form.fields["user"].queryset = User.objects.filter(is_staff=False)
    return render(request, "admin/subscription_form.html", {"form": form})


@admin_required
def subscription_toggle(request, subscription_id):
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    subscription.active = not subscription.active
    if subscription.active:
        subscription.next_renewal_date = max(subscription.next_renewal_date, timezone.now().date())
    subscription.save(update_fields=["active", "next_renewal_date", "updated_at"])
    status = "activated" if subscription.active else "paused"
    messages.info(request, f"Subscription '{subscription.name}' {status}.")
    return redirect("adminportal:customer_detail", user_id=subscription.user_id)


@admin_required
def profile_update(request, user_id):
    customer = get_object_or_404(User.objects.select_related("profile"), pk=user_id, is_staff=False)
    profile = customer.profile

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("adminportal:customer_detail", user_id=customer.id)
    else:
        form = ProfileForm(instance=profile)

    return render(request, "admin/profile_form.html", {"form": form, "customer": customer})
