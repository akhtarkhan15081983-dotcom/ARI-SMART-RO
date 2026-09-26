from django.db.models import Q

from .models import User


OFFER_AUDIENCES = {"ALL", "ACTIVE", "INACTIVE", "TARGETED"}


def customer_for_user(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    customer = getattr(user, "customer_profile", None)
    if customer is not None:
        return customer

    phone = str(getattr(user, "phone", "") or "").strip()
    if not phone:
        return None

    from customers.models import Customer

    return Customer.objects.filter(phone=phone).order_by("id").first()


def offer_audience_q_for_user(user):
    criteria = (
        Q(audience="ALL", target_user__isnull=True)
        | Q(audience="TARGETED", target_user=user)
    )

    customer = customer_for_user(user)
    if customer is not None:
        if customer.is_active:
            criteria |= Q(audience="ACTIVE", target_user__isnull=True)
        else:
            criteria |= Q(audience="INACTIVE", target_user__isnull=True)

    return criteria


def customer_user(customer):
    linked = getattr(customer, "user", None)
    if (
        linked is not None
        and linked.role == "CUSTOMER"
        and linked.is_active
    ):
        return linked

    phone = str(getattr(customer, "phone", "") or "").strip()
    if not phone:
        return None

    return User.objects.filter(
        phone=phone,
        role="CUSTOMER",
        is_active=True,
    ).first()


def users_for_customer_status(is_active):
    from customers.models import Customer

    customers = Customer.objects.filter(is_active=is_active).select_related("user")
    user_ids = set()
    fallback_phones = set()

    for customer in customers.iterator():
        linked = getattr(customer, "user", None)
        if linked is not None and linked.role == "CUSTOMER" and linked.is_active:
            user_ids.add(linked.id)
        else:
            phone = str(customer.phone or "").strip()
            if phone:
                fallback_phones.add(phone)

    if fallback_phones:
        user_ids.update(
            User.objects.filter(
                phone__in=fallback_phones,
                role="CUSTOMER",
                is_active=True,
            ).values_list("id", flat=True)
        )

    return User.objects.filter(id__in=user_ids, role="CUSTOMER", is_active=True)
