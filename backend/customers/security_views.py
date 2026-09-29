from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from employees.models import EmployeeProfile
from jobs.idempotency import action_id_from_request
from jobs.models import ClientActionReceipt
from tenancy.access import request_company

from .models import Customer, CustomerRentPayment
from .views import AssignCustomerAPIView, RentPaymentCreateAPIView, RentPaymentHistoryAPIView


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
    """Tenant-guard and atomically de-duplicate rent payment retries."""

    @transaction.atomic
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
        assigned_company_id = customer.assigned_engineer.company_id if customer.assigned_engineer_id else None

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

        action_id = action_id_from_request(request)
        receipt = None
        created = False
        if action_id:
            receipt, created = ClientActionReceipt.objects.get_or_create(
                user=request.user,
                action_id=action_id,
                defaults={
                    "action_type": "RENT_PAYMENT",
                    "response_status": status.HTTP_202_ACCEPTED,
                    "response_payload": {"detail": "Rent payment action is processing."},
                },
            )
            if not created:
                if receipt.action_type != "RENT_PAYMENT":
                    return Response(
                        {
                            "detail": "This action ID was already used for another action type.",
                            "action_id": action_id,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                if receipt.completed_at is None:
                    return Response(
                        {"detail": "This rent payment action is already processing.", "action_id": action_id},
                        status=status.HTTP_409_CONFLICT,
                    )
                payload = dict(receipt.response_payload or {})
                payload["action_id"] = action_id
                payload["idempotent_replay"] = True
                return Response(payload, status=receipt.response_status)

        response = super().post(request)

        if action_id and receipt is not None:
            if 200 <= response.status_code < 300:
                payload = dict(response.data) if isinstance(response.data, dict) else {"result": response.data}
                payload["action_id"] = action_id
                payload["idempotent_replay"] = False
                response.data = payload
                receipt.response_status = response.status_code
                receipt.response_payload = payload
                receipt.completed_at = timezone.now()
                receipt.save(update_fields=["response_status", "response_payload", "completed_at"])
            elif created:
                # Validation/business-rule failures are not durable client
                # actions; remove the claim so a corrected retry can reuse ID.
                receipt.delete()

        return response


class TenantScopedRentPaymentHistoryAPIView(RentPaymentHistoryAPIView):
    """Restrict rent ledger reads to the active workspace."""

    def get(self, request):
        if request.user.role not in self.ALLOWED_ROLES:
            return super().get(request)

        company = request_company(request)
        payments = CustomerRentPayment.objects.select_related(
            "customer",
            "customer__assigned_engineer",
            "rent_history",
            "collected_by__user",
        )
        if company is not None:
            payments = payments.filter(customer__assigned_engineer__company=company)
        else:
            payments = payments.filter(
                Q(customer__assigned_engineer__isnull=True)
                | Q(customer__assigned_engineer__company__isnull=True)
            )

        customer_id = request.query_params.get("customer_id")
        if customer_id:
            try:
                customer_id = int(customer_id)
            except (TypeError, ValueError):
                return Response(
                    {"success": False, "message": "Invalid customer_id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            payments = payments.filter(customer_id=customer_id)

        payment_data = []
        for payment in payments.order_by("-payment_date", "-id"):
            customer = payment.customer
            collector_name = ""
            if payment.collected_by:
                collector_user = payment.collected_by.user
                collector_name = (
                    (collector_user.get_full_name() or "").strip()
                    or str(getattr(collector_user, "role", "") or "")
                    or collector_user.phone
                )
            payment_data.append(
                {
                    "id": payment.id,
                    "customer": {
                        "id": customer.id,
                        "customer_id": customer.customer_id,
                        "name": customer.name,
                        "phone": customer.phone,
                        "card_number": customer.card_number,
                        "old_card_number": customer.old_card_number,
                    },
                    "rent_month": (
                        payment.rent_history.rent_month.isoformat()
                        if payment.rent_history and payment.rent_history.rent_month
                        else None
                    ),
                    "amount": float(payment.amount or 0),
                    "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
                    "payment_mode": payment.payment_mode,
                    "remarks": payment.remarks,
                    "collected_by": collector_name,
                    "created_at": payment.created_at.isoformat() if payment.created_at else None,
                }
            )

        return Response(
            {"success": True, "count": len(payment_data), "payments": payment_data},
            status=status.HTTP_200_OK,
        )
