from rest_framework import status
from rest_framework.response import Response

from employees.models import EmployeeProfile
from tenancy.access import request_company

from .models import Customer
from .views import AssignCustomerAPIView, RentPaymentCreateAPIView


class TenantScopedAssignCustomerAPIView(AssignCustomerAPIView):
    """Limit customer assignment targets to staff in the current workspace."""

    def post(self, request, pk):
        company = request_company(request)

        employee_id = request.data.get("employee_id", request.data.get("engineer"))
        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            return super().post(request, pk)

        employee_scope = EmployeeProfile.objects.filter(
            pk=employee_id,
            is_active=True,
            user__is_active=True,
            user__role__in=["ENGINEER", "OFFICE"],
        )
        if company is not None:
            employee_scope = employee_scope.filter(company=company)
        else:
            employee_scope = employee_scope.filter(company__isnull=True)

        if not employee_scope.exists():
            return Response(
                {"message": "Employee not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().post(request, pk)


class TenantScopedRentPaymentCreateAPIView(RentPaymentCreateAPIView):
    """Fail closed for direct-ID rent writes until Customer owns company explicitly."""

    def post(self, request):
        customer_id = request.data.get("customer_id")
        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError):
            return super().post(request)

        customer = Customer.objects.select_related("assigned_engineer").filter(pk=customer_id).first()
        if customer is None:
            return Response(
                {"success": False, "message": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        company = request_company(request)
        assigned_company_id = (
            customer.assigned_engineer.company_id
            if customer.assigned_engineer_id else None
        )

        if company is not None:
            if assigned_company_id is None:
                return Response(
                    {
                        "success": False,
                        "code": "CUSTOMER_TENANT_UNRESOLVED",
                        "message": (
                            "Customer workspace ownership is unresolved. Assign the customer "
                            "inside this workspace before recording rent."
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if assigned_company_id != company.id:
                return Response(
                    {"success": False, "message": "Customer not found in this workspace."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        elif assigned_company_id is not None:
            return Response(
                {"success": False, "message": "Customer not found in the legacy workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().post(request)
