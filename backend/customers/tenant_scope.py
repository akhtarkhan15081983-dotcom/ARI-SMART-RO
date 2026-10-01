from django.db.models import Q

from tenancy.access import request_company

from .models import Customer


def operator_customer_queryset(request, queryset=None):
    """Scope operational customer mutations to the active workspace.

    Legacy company=NULL rows are visible only when their assigned employee
    proves ownership in the active company. Accounts without a company context
    remain limited to legacy unowned rows.
    """
    rows = queryset if queryset is not None else Customer.objects.all()
    company = request_company(request)
    if company is not None:
        return rows.filter(
            Q(company=company)
            | Q(company__isnull=True, assigned_engineer__company=company)
        ).distinct()
    return rows.filter(company__isnull=True).filter(
        Q(assigned_engineer__isnull=True)
        | Q(assigned_engineer__company__isnull=True)
    )
