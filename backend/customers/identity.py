from customers.models import Customer


def unique_unlinked_customer_for_phone(phone, *, active_only=True):
    """Return a legacy customer only when the phone identifies exactly one row.

    Shared phone numbers are valid business data. Phone-only fallback must
    therefore fail closed when multiple unlinked customer records share it.
    Durable user/customer links or explicit customer/card references are
    required to disambiguate those cases.
    """
    rows = Customer.objects.filter(phone=phone, user__isnull=True)
    if active_only:
        rows = rows.filter(is_active=True)
    candidates = list(rows.order_by("id")[:2])
    return candidates[0] if len(candidates) == 1 else None
