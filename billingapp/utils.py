from __future__ import annotations

from datetime import date

from django.db import transaction

from .models import Bill, Subscription


@transaction.atomic
def ensure_subscription_bills(user=None) -> int:
    """Generate bills for due subscriptions. Returns count of bills created."""

    today = date.today()
    subscriptions = Subscription.objects.filter(active=True)
    if user is not None:
        subscriptions = subscriptions.filter(user=user)

    generated = 0
    for sub in subscriptions.select_related("user"):
        while sub.active and sub.next_renewal_date <= today:
            due_date = sub.next_renewal_date
            bill, created = Bill.objects.get_or_create(
                subscription=sub,
                due_date=due_date,
                defaults={
                    "user": sub.user,
                    "title": sub.name,
                    "description": sub.notes or "Recurring subscription payment",
                    "amount": sub.amount,
                    "bill_type": sub.bill_type or "Subscription",
                },
            )

            sub.advance_next_renewal()

            if created:
                generated += 1

            # Ensure the loop will eventually terminate even if the bill already existed
            if sub.next_renewal_date <= today:
                continue

        sub.save(update_fields=["next_renewal_date", "updated_at"])

    return generated

