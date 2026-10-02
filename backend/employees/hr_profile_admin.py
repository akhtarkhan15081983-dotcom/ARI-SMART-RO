from datetime import date
from decimal import Decimal

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import HasRequiredFeature, request_company

from .hr_lifecycle_models import EmployeeHrLifecycleEvent
from .models import EmployeeProfile


class EmployeeHrProfileAdminAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    @transaction.atomic
    def patch(self, request, employee_id):
        role = str(getattr(request.user, "role", "") or "").upper()
        if role not in {"ADMIN", "MANAGER", "OFFICE"}:
            return Response({"detail": "HR employee profile permission required."}, status=403)
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)
        employee = EmployeeProfile.objects.select_for_update().select_related("user").filter(
            pk=employee_id, company=company
        ).first()
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)

        before = {
            "job_title": employee.job_title,
            "department": employee.department,
            "grade": employee.grade,
            "salary": str(employee.salary),
        }
        text_fields = {
            "address": 1000,
            "city": 100,
            "state": 100,
            "pincode": 10,
            "emergency_name": 100,
            "emergency_contact": 10,
            "aadhaar_number": 12,
            "pan_number": 10,
            "job_title": 120,
            "department": 100,
            "grade": 50,
        }
        changed = []
        for field, limit in text_fields.items():
            if field in request.data:
                value = str(request.data.get(field) or "").strip()[:limit]
                setattr(employee, field, value)
                changed.append(field)

        if "date_of_birth" in request.data and request.data.get("date_of_birth"):
            try:
                employee.date_of_birth = date.fromisoformat(str(request.data["date_of_birth"]))
                changed.append("date_of_birth")
            except ValueError:
                return Response({"detail": "Date of birth must be YYYY-MM-DD."}, status=400)

        if "salary" in request.data:
            try:
                salary = Decimal(str(request.data.get("salary") or 0))
            except Exception:
                return Response({"detail": "Salary must be numeric."}, status=400)
            if salary < 0:
                return Response({"detail": "Salary cannot be negative."}, status=400)
            employee.salary = salary
            changed.append("salary")

        if "reporting_manager_id" in request.data:
            manager_id = request.data.get("reporting_manager_id")
            if manager_id in (None, ""):
                employee.reporting_manager = None
            else:
                manager = EmployeeProfile.objects.filter(
                    pk=manager_id, company=company, is_active=True
                ).first()
                if manager is None or manager.id == employee.id:
                    return Response({"detail": "Select a valid reporting manager."}, status=400)
                employee.reporting_manager = manager
            changed.append("reporting_manager")

        if changed:
            employee.save()
        after = {
            "job_title": employee.job_title,
            "department": employee.department,
            "grade": employee.grade,
            "salary": str(employee.salary),
        }
        EmployeeHrLifecycleEvent.objects.create(
            employee=employee,
            event_type="HR_PROFILE_UPDATED",
            from_status="",
            to_status="",
            note=str(request.data.get("note") or "Employee HR profile completed/updated."),
            metadata={"changed_fields": changed, "before": before, "after": after},
            created_by=request.user,
        )
        return Response({"success": True, "changed_fields": changed})
