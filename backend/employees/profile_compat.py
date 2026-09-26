from rest_framework import status
from rest_framework.response import Response

from customers.models import Customer
from .views import EmployeeProfileAPIView


def _customer_for_user(user):
    return Customer.objects.filter(user=user, is_active=True).first()


def _customer_profile_payload(customer):
    return {
        "employee_id": customer.customer_id,
        "first_name": customer.name.split(" ", 1)[0] if customer.name else "",
        "last_name": customer.name.split(" ", 1)[1] if customer.name and " " in customer.name else "",
        "pincode": customer.pincode or "",
        "emergency_name": "",
        "emergency_contact": "",
        "full_name": customer.name or "",
        "phone": customer.phone or "",
        "email": customer.email or "",
        "role": "CUSTOMER",
        "designation": "ARI Customer",
        "joining_date": customer.installation_date.isoformat() if customer.installation_date else "",
        "gender": customer.gender or "",
        "city": customer.city or "",
        "state": customer.state or "",
        "address": customer.address or "",
        "photo": None,
        "face_enrolled": False,
        "face_enrollment_verified": False,
        "face_enrollment_allowed": False,
        "face_enrolled_at": None,
        "attendance_device_id": "",
    }


class CustomerAwareEmployeeProfileAPIView(EmployeeProfileAPIView):
    """Keep the legacy mobile Profile screen working for customer accounts.

    v1.0.40 opens /employees/profile/ for every role. Existing-customer
    activation correctly links Customer.user, so customer requests can return
    customer data here instead of an employee-profile 404. Staff behavior is
    unchanged and continues through EmployeeProfileAPIView.
    """

    def get(self, request):
        if str(getattr(request.user, "role", "") or "").upper() != "CUSTOMER":
            return super().get(request)

        customer = _customer_for_user(request.user)
        if customer is None:
            return Response(
                {"success": False, "message": "Customer profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(_customer_profile_payload(customer), status=status.HTTP_200_OK)

    def put(self, request):
        if str(getattr(request.user, "role", "") or "").upper() != "CUSTOMER":
            return super().put(request)

        customer = _customer_for_user(request.user)
        if customer is None:
            return Response(
                {"success": False, "message": "Customer profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        first_name = str(request.data.get("first_name", "") or "").strip()
        last_name = str(request.data.get("last_name", "") or "").strip()
        full_name = " ".join(part for part in (first_name, last_name) if part).strip()
        if full_name:
            customer.name = full_name
        if "pincode" in request.data:
            customer.pincode = str(request.data.get("pincode", "") or "").strip()
        customer.save(update_fields=["name", "pincode"])
        return Response(_customer_profile_payload(customer), status=status.HTTP_200_OK)
