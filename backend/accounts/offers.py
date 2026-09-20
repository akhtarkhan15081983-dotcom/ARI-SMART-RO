from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q
from django.utils import timezone

from .models import CustomerEngagement


ZERO = Decimal("0.00")


def _money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def eligible_offers(user=None, scope=None, now=None):
    now = now or timezone.now()
    rows = CustomerEngagement.objects.filter(
        is_active=True,
        kind="OFFER",
        auto_apply=True,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))
    if scope:
        rows = rows.filter(offer_scope=scope)
    if user is None:
        rows = rows.filter(audience="ALL", target_user__isnull=True)
    else:
        rows = rows.filter(
            Q(audience="ALL", target_user__isnull=True)
            | Q(audience="TARGETED", target_user=user)
        )
    return rows.order_by("-priority", "-created_at")


def discount_for_offer(offer, base_amount):
    base = _money(base_amount)
    if base <= ZERO or base < _money(offer.minimum_amount):
        return ZERO
    if offer.discount_type == "PERCENT":
        discount = base * _money(offer.discount_value) / Decimal("100")
    elif offer.discount_type == "FIXED":
        discount = _money(offer.discount_value)
    else:
        return ZERO
    cap = _money(offer.max_discount)
    if cap > ZERO:
        discount = min(discount, cap)
    return min(base, _money(discount))


def best_offer(user, scope, base_amount):
    base = _money(base_amount)
    best = None
    best_discount = ZERO
    for offer in eligible_offers(user=user, scope=scope):
        discount = discount_for_offer(offer, base)
        if discount > best_discount:
            best = offer
            best_discount = discount
    return best, best_discount, _money(base - best_discount)


def customer_offer_user(customer):
    if getattr(customer, "user_id", None):
        return customer.user
    if not getattr(customer, "phone", ""):
        return None
    from .models import User
    return User.objects.filter(phone=customer.phone, role="CUSTOMER", is_active=True).first()



def best_public_offer(scope, base_amount, promo_code=""):
    base = _money(base_amount)
    code = str(promo_code or "").strip().upper()
    candidates = CustomerEngagement.objects.filter(
        is_active=True,
        kind="OFFER",
        audience="ALL",
        target_user__isnull=True,
        offer_scope=scope,
        valid_from__lte=timezone.now(),
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.now()))
    if code:
        candidates = candidates.filter(promo_code__iexact=code)
    else:
        candidates = candidates.filter(auto_apply=True)

    best = None
    best_discount = ZERO
    for offer in candidates.order_by("-priority", "-created_at"):
        discount = discount_for_offer(offer, base)
        if discount > best_discount:
            best = offer
            best_discount = discount
    return best, best_discount, _money(base - best_discount)
