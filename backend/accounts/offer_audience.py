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


def _offer_creator_scope_q(customer):
    company_id = getattr(customer, "company_id", None)
    if company_id is None:
        return Q()
    return (
        Q(
            created_by__company_memberships__company_id=company_id,
            created_by__company_memberships__is_active=True,
        )
        | Q(created_by__employee_profile__company_id=company_id)
    )


def offer_audience_q_for_user(user):
    targeted = Q(audience="TARGETED", target_user=user)
    broad = Q(audience="ALL", target_user__isnull=True)

    customer = customer_for_user(user)
    if customer is not None:
        if customer.is_active:
            broad |= Q(audience="ACTIVE", target_user__isnull=True)
        else:
            broad |= Q(audience="INACTIVE", target_user__isnull=True)
        creator_scope = _offer_creator_scope_q(customer)
        if creator_scope:
            broad &= creator_scope

    return targeted | broad


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

    candidate = User.objects.filter(
        phone=phone,
        role="CUSTOMER",
        is_active=True,
    ).first()
    if candidate is None:
        return None
    linked_customer = getattr(candidate, "customer_profile", None)
    if linked_customer is not None and linked_customer.pk != customer.pk:
        return None
    return candidate


def users_for_customer_status(is_active, company=None):
    from customers.models import Customer

    customers = Customer.objects.filter(is_active=is_active).select_related("user")
    if company is not None:
        customers = customers.filter(company=company)
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

    users = User.objects.filter(
        id__in=user_ids,
        role="CUSTOMER",
        is_active=True,
    )
    if company is not None:
        users = users.filter(
            Q(customer_profile__company=company)
            | Q(customer_profile__isnull=True)
        )
    return users
