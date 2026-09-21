from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from accounts.permissions import IsAdmin, IsOperationsUser, IsStaffOperator, can_edit_customers
from accounts.models import User
from tenancy.models import CompanyMembership
from tenancy.access import HasRequiredFeature, has_feature_access

from .models import EmployeeCareerMovement, EmployeeProfile
from .serializers import (
    EmployeeLocationSerializer,
    EmployeeProfileSerializer,
    EmployeeProfileUpdateSerializer,
    AssignmentEmployeeSerializer,
)


def _photo_url(request, employee):
    if not employee.photo:
        return None
    return request.build_absolute_uri(employee.photo.url)


def _refresh_onboarding(employee):
    from .training import sync_training_assignments
    sync_training_assignments(employee)
    profile_complete = bool(
        employee.user.first_name
        and employee.joining_date
        and employee.designation
    )
    security_complete = bool(
        employee.photo
        and employee.face_enrollment_verified
        and employee.attendance_device_id
    )
    mandatory = employee.training_assignments.filter(
        course__is_active=True,
        course__is_mandatory=True,
    )
    training_complete = not mandatory.exclude(status="COMPLETED").exists()
    if not profile_complete:
        status_value = "PROFILE_PENDING"
    elif not security_complete:
        status_value = "SECURITY_PENDING"
    elif not training_complete:
        status_value = "TRAINING_PENDING"
    else:
        status_value = "READY"
    if employee.onboarding_status != status_value:
        employee.onboarding_status = status_value
        employee.save(update_fields=["onboarding_status"])
    return {
        "status": status_value,
        "profile_complete": profile_complete,
        "security_complete": security_complete,
        "training_complete": training_complete,
        "ready": status_value == "READY",
    }


def _employee_id_card_payload(request, employee):
    return {
        "employee_id": employee.employee_id,
        "name": employee.user.get_full_name() or employee.user.phone,
        "designation": employee.designation,
        "job_title": employee.job_title,
        "department": employee.department,
        "photo": _photo_url(request, employee),
        "company": getattr(employee.company, "name", "") if employee.company_id else "",
        "verification_code": employee.public_verification_code,
        "qr_payload": f"ARI-EMP:{employee.public_verification_code}",
        "issued_at": employee.id_card_issued_at.isoformat() if employee.id_card_issued_at else None,
        "valid_until": employee.id_card_valid_until.isoformat() if employee.id_card_valid_until else None,
        "active": bool(employee.is_active and employee.user.is_active),
        "identity_verified": bool(employee.face_enrollment_verified),
        "onboarding": _refresh_onboarding(employee),
    }


def _request_company(request):
    membership = (
        CompanyMembership.objects.filter(
            user=request.user, is_active=True, company__is_active=True,
            company__lifecycle_status="ACTIVE",
        )
        .select_related("company__subscription__plan", "branch")
        .first()
    )
    return membership.company if membership else None


class EmployeeManagementAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "employee_management"

    def get(self, request):
        company = _request_company(request)
        if company is None:
            return Response({"success": False, "message": "Active company workspace not found."}, status=403)
        employees = EmployeeProfile.objects.filter(company=company).select_related("user", "reporting_manager__user").order_by(
            "user__first_name", "user__last_name"
        )
        return Response({
            "success": True,
            "company": {"id": company.id, "name": company.name},
            "can_delegate_customer_edit": str(getattr(request.user, "role", "") or "").upper() == "ADMIN",
            "employees": [
                {
                    "id": employee.id,
                    "employee_id": employee.employee_id,
                    "name": employee.user.get_full_name() or employee.user.phone,
                    "phone": employee.user.phone,
                    "email": employee.user.email,
                    "designation": employee.designation,
                    "job_title": employee.job_title,
                    "department": employee.department,
                    "grade": employee.grade,
                    "reporting_manager": None if employee.reporting_manager is None else {
                        "id": employee.reporting_manager_id,
                        "name": employee.reporting_manager.user.get_full_name() or employee.reporting_manager.user.phone,
                    },
                    "joining_date": employee.joining_date,
                    "salary": employee.salary,
                    "photo": _photo_url(request, employee),
                    "onboarding": _refresh_onboarding(employee),
                    "id_card": {
                        "verification_code": employee.public_verification_code,
                        "valid_until": employee.id_card_valid_until,
                        "active": bool(employee.is_active and employee.user.is_active),
                    },
                    "is_active": employee.is_active and employee.user.is_active,
                    "can_edit_customer": can_edit_customers(employee.user),
                    "location_received": (
                        employee.last_latitude is not None
                        and employee.last_longitude is not None
                    ),
                    "last_location_updated": employee.last_location_updated,
                }
                for employee in employees
            ],
        })

    @transaction.atomic
    def post(self, request):
        company = _request_company(request)
        if company is None:
            return Response({"success": False, "message": "Active company workspace not found."}, status=403)
        subscription = getattr(company, "subscription", None)
        if subscription is None or not subscription.has_access:
            return Response({"success": False, "message": "An active company subscription is required."}, status=403)
        if EmployeeProfile.objects.filter(company=company, is_active=True).count() >= subscription.plan.employee_limit:
            return Response({"success": False, "message": "Employee limit reached for the current subscription plan."}, status=409)

        first_name = str(request.data.get("first_name", "")).strip()
        last_name = str(request.data.get("last_name", "")).strip()
        phone = str(request.data.get("phone", "")).strip()
        email = str(request.data.get("email", "")).strip()
        designation = str(request.data.get("designation", "")).upper()
        gender = str(request.data.get("gender", "OTHER")).upper()
        joining_date = request.data.get("joining_date")
        initial_password = str(request.data.get("initial_password", ""))
        if not first_name or len(phone) != 10 or not phone.isdigit():
            return Response({"success": False, "message": "Employee name and valid 10-digit phone are required."}, status=400)
        if designation not in {choice[0] for choice in EmployeeProfile.DESIGNATION_CHOICES}:
            return Response({"success": False, "message": "Select a valid employee designation."}, status=400)
        if gender not in {choice[0] for choice in EmployeeProfile.GENDER_CHOICES}:
            return Response({"success": False, "message": "Select a valid gender."}, status=400)
        if not joining_date:
            return Response({"success": False, "message": "Joining date is required."}, status=400)
        try:
            validate_password(initial_password)
        except DjangoValidationError as exc:
            return Response({"success": False, "message": " ".join(exc.messages)}, status=400)
        if User.objects.filter(phone=phone).exists():
            return Response({"success": False, "message": "This phone already belongs to an existing account."}, status=409)

        reporting_manager = None
        reporting_manager_id = request.data.get("reporting_manager_id")
        if reporting_manager_id:
            reporting_manager = EmployeeProfile.objects.filter(
                pk=reporting_manager_id,
                company=company,
                is_active=True,
            ).first()
            if reporting_manager is None:
                return Response({"success": False, "message": "Select a valid reporting manager."}, status=400)

        role = "MANAGER" if designation == "MANAGER" else designation
        user = User.objects.create_user(
            phone=phone, password=initial_password, first_name=first_name,
            last_name=last_name, email=email, role=role, is_verified=True, is_active=True,
        )
        employee = EmployeeProfile.objects.create(
            company=company, user=user, designation=designation, gender=gender,
            joining_date=joining_date, salary=request.data.get("salary") or 0,
            job_title=str(request.data.get("job_title", "")).strip(),
            department=str(request.data.get("department", "")).strip(),
            grade=str(request.data.get("grade", "")).strip(),
            reporting_manager=reporting_manager,
            onboarding_status="SECURITY_PENDING",
            id_card_issued_at=timezone.now(),
            id_card_valid_until=timezone.localdate() + timedelta(days=365 * 3),
            address=str(request.data.get("address", "")).strip(),
            city=str(request.data.get("city", "")).strip(),
            state=str(request.data.get("state", "")).strip(),
            pincode=str(request.data.get("pincode", "")).strip(),
            emergency_name=str(request.data.get("emergency_name", "")).strip(),
            emergency_contact=str(request.data.get("emergency_contact", "")).strip(),
        )
        owner_membership = CompanyMembership.objects.filter(user=request.user, company=company).first()
        CompanyMembership.objects.create(
            company=company, user=user,
            role="MANAGER" if designation == "MANAGER" else "STAFF",
            branch=owner_membership.branch if owner_membership else None,
        )
        return Response({
            "success": True, "message": "Employee account created successfully.",
            "employee": {"id": employee.id, "employee_id": employee.employee_id, "name": user.get_full_name()},
        }, status=201)


class EmployeeCustomerEditPermissionAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, employee_id):
        company = _request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)

        employee = EmployeeProfile.objects.select_related("user").filter(
            pk=employee_id,
            company=company,
        ).first()
        if employee is None:
            return Response({"detail": "Employee not found in this workspace."}, status=404)

        allowed = bool(request.data.get("is_allowed", False))
        permission = Permission.objects.filter(
            codename="change_customer",
            content_type__app_label="customers",
            content_type__model="customer",
        ).first()
        if permission is None:
            return Response({"detail": "Customer edit permission is unavailable."}, status=500)

        if allowed:
            employee.user.user_permissions.add(permission)
        else:
            employee.user.user_permissions.remove(permission)

        return Response({
            "success": True,
            "employee_id": employee.id,
            "can_edit_customer": can_edit_customers(employee.user),
            "detail": (
                "Customer edit permission granted."
                if allowed else
                "Customer edit permission revoked."
            ),
        })


class EmployeeIdCardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = EmployeeProfile.objects.filter(user=request.user).select_related(
            "user", "company"
        ).first()
        if employee is None:
            return Response({"detail": "Employee profile not found."}, status=404)
        return Response(_employee_id_card_payload(request, employee))


class EmployeeIdVerifyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        employee = EmployeeProfile.objects.filter(
            public_verification_code=str(code).strip().upper(),
        ).select_related("user", "company").first()
        if employee is None:
            return Response({"verified": False, "detail": "Employee ID not found."}, status=404)
        payload = _employee_id_card_payload(request, employee)
        # Never expose private contact, salary, home address or HR records.
        return Response({"verified": bool(payload["active"]), "employee": payload})


class FaceEnrollmentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            employee = EmployeeProfile.objects.get(user=request.user)
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # First-ever enrollment is allowed. Once a face/device exists, only an
        # explicit admin authorization can open one re-enrollment attempt.
        already_enrolled = bool(employee.face_enrolled_at or employee.attendance_device_id)
        if already_enrolled and not employee.face_enrollment_allowed:
            return Response(
                {
                    "success": False,
                    "message": "Face/device re-enrollment is locked. Ask an admin to allow it.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        enrollment_photo = request.FILES.get("photo")
        device_id = (request.data.get("device_id") or "").strip()

        if enrollment_photo is None:
            return Response(
                {"success": False, "message": "Live enrollment photo is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not device_id or len(device_id) > 128:
            return Response(
                {"success": False, "message": "Valid attendance device ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if enrollment_photo.content_type not in {"image/jpeg", "image/png"}:
            return Response(
                {"success": False, "message": "Enrollment photo must be JPEG or PNG."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if enrollment_photo.size > 5 * 1024 * 1024:
            return Response(
                {"success": False, "message": "Enrollment photo must be 5 MB or smaller."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee.photo = enrollment_photo
        employee.face_enrolled_at = timezone.now()
        employee.face_enrollment_verified = False
        employee.attendance_device_id = device_id
        employee.face_enrollment_allowed = False
        employee.save(update_fields=[
            "photo",
            "face_enrolled_at",
            "face_enrollment_verified",
            "attendance_device_id",
            "face_enrollment_allowed",
        ])

        return Response({
            "success": True,
            "message": "Real enrollment photo saved and this device is bound for attendance.",
            "face_enrolled": True,
            "face_enrollment_verified": False,
            "face_enrollment_allowed": False,
            "face_enrolled_at": employee.face_enrolled_at,
            "device_bound": True,
        })


class AdminFaceEnrollmentListAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        employees = EmployeeProfile.objects.filter(
            is_active=True,
            user__is_active=True,
        ).select_related("user").order_by(
            "designation",
            "user__first_name",
            "user__last_name",
            "employee_id",
        )

        return Response([
            {
                "id": employee.id,
                "employee_id": employee.employee_id,
                "name": employee.user.get_full_name() or employee.user.phone,
                "phone": employee.user.phone,
                "designation": employee.designation,
                "face_enrolled": bool(employee.face_enrolled_at and employee.photo),
                "face_enrollment_verified": employee.face_enrollment_verified,
                "face_enrollment_allowed": employee.face_enrollment_allowed,
                "attendance_device_bound": bool(employee.attendance_device_id),
            }
            for employee in employees
        ])


class AdminFaceEnrollmentControlAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, employee_id):
        if getattr(request.user, "role", "") != "ADMIN":
            return Response(
                {"success": False, "message": "Only an admin can control face enrollment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            employee = EmployeeProfile.objects.select_related("user").get(id=employee_id)
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Employee not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        action = (request.data.get("action") or "").strip().lower()
        if action == "allow_reenrollment":
            employee.face_enrollment_allowed = True
            employee.save(update_fields=["face_enrollment_allowed"])
            return Response({
                "success": True,
                "message": "One face/device re-enrollment has been authorized by admin.",
                "employee_id": employee.id,
                "face_enrollment_allowed": True,
                "face_enrolled": bool(employee.face_enrolled_at and employee.photo),
                "attendance_device_bound": bool(employee.attendance_device_id),
            })

        if action == "cancel_reenrollment":
            employee.face_enrollment_allowed = False
            employee.save(update_fields=["face_enrollment_allowed"])
            return Response({
                "success": True,
                "message": "Face/device re-enrollment authorization cancelled.",
                "employee_id": employee.id,
                "face_enrollment_allowed": False,
                "face_enrolled": bool(employee.face_enrolled_at and employee.photo),
                "attendance_device_bound": bool(employee.attendance_device_id),
            })

        return Response(
            {"success": False, "message": "Invalid action."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class UpdateLiveLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            employee = request.user.employee_profile
        except Exception:
            return Response({"error": "Employee profile not found."}, status=404)

        serializer = EmployeeLocationSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(last_location_updated=timezone.now(), is_online=True)
            return Response({"message": "Location Updated Successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EngineerLiveMapAPIView(APIView):
    permission_classes = [IsOperationsUser]

    def get(self, request):
        engineers = EmployeeProfile.objects.filter(
            designation="ENGINEER", is_active=True,
            last_latitude__isnull=False, last_longitude__isnull=False,
        ).select_related("user")
        return Response([{
            "id": e.id,
            "employee_id": e.employee_id,
            "name": e.user.get_full_name(),
            "phone": e.user.phone,
            "photo": request.build_absolute_uri(e.photo.url) if e.photo else None,
            "latitude": e.last_latitude,
            "longitude": e.last_longitude,
            "updated_at": e.last_location_updated,
            "online": e.is_online,
        } for e in engineers])


class EmployeeProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = EmployeeProfile.objects.get(user=request.user)
        except EmployeeProfile.DoesNotExist:
            return Response({"error": "Employee profile not found."}, status=404)
        serializer = EmployeeProfileSerializer(profile, context={"request": request})
        data = dict(serializer.data)
        data["face_enrolled"] = profile.face_enrolled_at is not None
        data["face_enrollment_verified"] = profile.face_enrollment_verified
        data["face_enrollment_allowed"] = profile.face_enrollment_allowed
        data["attendance_device_bound"] = bool(profile.attendance_device_id)
        return Response(data)

    def put(self, request):
        try:
            profile = EmployeeProfile.objects.get(user=request.user)
        except EmployeeProfile.DoesNotExist:
            return Response({"error": "Employee profile not found."}, status=404)
        serializer = EmployeeProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "message": "Profile updated successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EngineerListAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        engineers = EmployeeProfile.objects.filter(
            designation="ENGINEER", is_active=True,
        ).select_related("user")
        return Response([{
            "id": e.id,
            "employee_id": e.employee_id,
            "name": e.user.get_full_name() or e.user.phone,
            "phone": e.user.phone,
            "face_enrolled": e.face_enrolled_at is not None,
            "face_enrollment_verified": e.face_enrollment_verified,
            "face_enrollment_allowed": e.face_enrollment_allowed,
            "attendance_device_bound": bool(e.attendance_device_id),
        } for e in engineers])


class AssignmentEmployeeListAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        employees = EmployeeProfile.objects.filter(
            designation__in=["ENGINEER", "OFFICE"], is_active=True,
        ).select_related("user").order_by(
            "designation", "user__first_name", "user__last_name",
        )
        return Response(AssignmentEmployeeSerializer(employees, many=True).data)


# ============================================================
# EMPLOYEE LIFECYCLE / SAFE TEST ACCOUNT REMOVAL
# ============================================================

class EmployeeLifecycleAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "employee_management"

    def _profile_has_operational_history(self, employee):
        for relation in employee._meta.related_objects:
            accessor = relation.get_accessor_name()
            if not accessor:
                continue
            try:
                related = getattr(employee, accessor)
            except Exception:
                continue
            try:
                if relation.one_to_one:
                    if related is not None:
                        return True
                elif related.exists():
                    return True
            except Exception:
                continue
        return False

    @transaction.atomic
    def post(self, request, employee_id):
        if not has_feature_access(request, "employee_career_manage"):
            return Response({"detail": "Career management permission is required."}, status=403)
        company = _request_company(request)
        if company is None:
            return Response({"success": False, "message": "Active company workspace not found."}, status=403)

        try:
            employee = EmployeeProfile.objects.select_related("user").select_for_update().get(
                pk=employee_id,
                company=company,
            )
        except EmployeeProfile.DoesNotExist:
            return Response({"detail": "Employee not found."}, status=404)

        if employee.user_id == request.user.id:
            return Response({"detail": "You cannot deactivate or delete your own admin account."}, status=400)

        action = str(request.data.get("action") or "").strip().lower()

        if action == "deactivate":
            employee.is_active = False
            employee.is_online = False
            employee.save(update_fields=["is_active", "is_online"])
            employee.user.is_active = False
            employee.user.save(update_fields=["is_active"])
            CompanyMembership.objects.filter(company=company, user=employee.user).update(is_active=False)
            return Response({"success": True, "message": "Employee deactivated. Login access is disabled."})

        if action == "reactivate":
            employee.is_active = True
            employee.save(update_fields=["is_active"])
            employee.user.is_active = True
            employee.user.save(update_fields=["is_active"])
            CompanyMembership.objects.filter(company=company, user=employee.user).update(is_active=True)
            return Response({"success": True, "message": "Employee reactivated successfully."})

        if action == "permanent_delete":
            if str(request.data.get("confirm") or "").strip().upper() != "DELETE":
                return Response({"detail": "Type DELETE to confirm permanent deletion."}, status=400)
            if self._profile_has_operational_history(employee):
                return Response({
                    "detail": (
                        "This employee has linked attendance/jobs/payroll/customer history and cannot be "
                        "permanently deleted. Deactivate the employee instead."
                    )
                }, status=409)

            user = employee.user
            name = user.get_full_name() or user.phone
            CompanyMembership.objects.filter(company=company, user=user).delete()
            employee.delete()
            user.delete()
            return Response({"success": True, "message": f"{name} permanently deleted."})

        return Response({"detail": "Invalid employee lifecycle action."}, status=400)


# ============================================================
# CORPORATE CAREER MOVEMENT / PROMOTION WORKFLOW
# ============================================================

class EmployeeCareerMovementAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id):
        if not has_feature_access(request, "employee_career_manage"):
            return Response({"detail": "Career management permission is required."}, status=403)
        company = _request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)
        employee = EmployeeProfile.objects.filter(pk=employee_id, company=company).select_related(
            "user", "reporting_manager__user"
        ).first()
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        rows = employee.career_movements.select_related(
            "created_by", "approved_by", "old_reporting_manager__user", "new_reporting_manager__user"
        )[:200]
        return Response({
            "employee": {
                "id": employee.id,
                "employee_id": employee.employee_id,
                "name": employee.user.get_full_name() or employee.user.phone,
                "designation": employee.designation,
                "job_title": employee.job_title,
                "department": employee.department,
                "grade": employee.grade,
                "salary": employee.salary,
                "reporting_manager": None if employee.reporting_manager is None else {
                    "id": employee.reporting_manager_id,
                    "name": employee.reporting_manager.user.get_full_name() or employee.reporting_manager.user.phone,
                },
            },
            "history": [{
                "id": row.id,
                "movement_type": row.movement_type,
                "effective_date": row.effective_date,
                "old_designation": row.old_designation,
                "new_designation": row.new_designation,
                "old_job_title": row.old_job_title,
                "new_job_title": row.new_job_title,
                "old_department": row.old_department,
                "new_department": row.new_department,
                "old_grade": row.old_grade,
                "new_grade": row.new_grade,
                "old_salary": row.old_salary,
                "new_salary": row.new_salary,
                "old_reporting_manager": None if row.old_reporting_manager is None else (
                    row.old_reporting_manager.user.get_full_name() or row.old_reporting_manager.user.phone
                ),
                "new_reporting_manager": None if row.new_reporting_manager is None else (
                    row.new_reporting_manager.user.get_full_name() or row.new_reporting_manager.user.phone
                ),
                "reason": row.reason,
                "status": row.status,
                "created_by": row.created_by.get_full_name() or row.created_by.phone,
                "approved_by": None if row.approved_by is None else (row.approved_by.get_full_name() or row.approved_by.phone),
                "approved_at": row.approved_at,
            } for row in rows],
        })

    @transaction.atomic
    def post(self, request, employee_id):
        company = _request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)
        employee = EmployeeProfile.objects.select_for_update().filter(
            pk=employee_id, company=company, is_active=True
        ).first()
        if employee is None:
            return Response({"detail": "Active employee not found."}, status=404)

        movement_type = str(request.data.get("movement_type") or "PROMOTION").upper()
        allowed_types = {choice[0] for choice in EmployeeCareerMovement.TYPE_CHOICES}
        if movement_type not in allowed_types:
            return Response({"detail": "Invalid career movement type."}, status=400)

        try:
            effective_date = date.fromisoformat(str(request.data.get("effective_date") or ""))
        except ValueError:
            return Response({"detail": "Valid effective date is required."}, status=400)

        reason = str(request.data.get("reason") or "").strip()
        if not reason:
            return Response({"detail": "Reason is required."}, status=400)

        new_designation = str(request.data.get("new_designation") or employee.designation).upper()
        if new_designation not in {choice[0] for choice in EmployeeProfile.DESIGNATION_CHOICES}:
            return Response({"detail": "Invalid new designation."}, status=400)

        new_job_title = str(request.data.get("new_job_title") or employee.job_title).strip()[:120]
        new_department = str(request.data.get("new_department") or employee.department).strip()[:100]
        new_grade = str(request.data.get("new_grade") or employee.grade).strip()[:50]

        raw_salary = request.data.get("new_salary")
        try:
            new_salary = employee.salary if raw_salary in (None, "") else Decimal(str(raw_salary))
        except Exception:
            return Response({"detail": "Valid new salary is required."}, status=400)
        if new_salary < 0:
            return Response({"detail": "Salary cannot be negative."}, status=400)

        manager_id = request.data.get("new_reporting_manager_id")
        new_manager = employee.reporting_manager
        if manager_id not in (None, ""):
            new_manager = EmployeeProfile.objects.filter(
                pk=manager_id, company=company, is_active=True
            ).first()
            if new_manager is None:
                return Response({"detail": "Reporting manager not found."}, status=400)
            if new_manager.id == employee.id:
                return Response({"detail": "Employee cannot report to themselves."}, status=400)

        row = EmployeeCareerMovement.objects.create(
            employee=employee,
            movement_type=movement_type,
            effective_date=effective_date,
            old_designation=employee.designation,
            new_designation=new_designation,
            old_job_title=employee.job_title,
            new_job_title=new_job_title,
            old_department=employee.department,
            new_department=new_department,
            old_grade=employee.grade,
            new_grade=new_grade,
            old_salary=employee.salary,
            new_salary=new_salary,
            old_reporting_manager=employee.reporting_manager,
            new_reporting_manager=new_manager,
            reason=reason[:500],
            created_by=request.user,
        )
        return Response({
            "id": row.id,
            "status": row.status,
            "detail": "Career movement saved as draft for approval.",
        }, status=201)


class EmployeeCareerMovementActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, employee_id, movement_id):
        if not has_feature_access(request, "employee_career_manage"):
            return Response({"detail": "Career management permission is required."}, status=403)
        company = _request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)

        row = EmployeeCareerMovement.objects.select_for_update().select_related(
            "employee__user"
        ).filter(
            pk=movement_id,
            employee_id=employee_id,
            employee__company=company,
            status="DRAFT",
        ).first()
        if row is None:
            return Response({"detail": "Draft career movement not found."}, status=404)

        action = str(request.data.get("action") or "").upper()
        if action == "CANCEL":
            row.status = "CANCELLED"
            row.cancelled_at = timezone.now()
            row.save(update_fields=["status", "cancelled_at"])
            return Response({"detail": "Career movement cancelled.", "status": row.status})

        if action != "APPROVE":
            return Response({"detail": "Action must be APPROVE or CANCEL."}, status=400)

        if row.effective_date > timezone.localdate():
            return Response({
                "detail": (
                    "Future-dated career movement is scheduled as a draft. "
                    "Approve it on or after its effective date."
                )
            }, status=400)

        employee = row.employee
        employee.designation = row.new_designation or employee.designation
        employee.job_title = row.new_job_title
        employee.department = row.new_department
        employee.grade = row.new_grade
        if row.new_salary is not None:
            employee.salary = row.new_salary
        employee.reporting_manager = row.new_reporting_manager
        employee.save(update_fields=[
            "designation", "job_title", "department", "grade", "salary", "reporting_manager"
        ])

        role = "MANAGER" if employee.designation == "MANAGER" else employee.designation
        employee.user.role = role
        employee.user.save(update_fields=["role"])
        CompanyMembership.objects.filter(company=company, user=employee.user).update(
            role="MANAGER" if employee.designation == "MANAGER" else "STAFF"
        )

        row.status = "APPROVED"
        row.approved_by = request.user
        row.approved_at = timezone.now()
        row.save(update_fields=["status", "approved_by", "approved_at"])

        return Response({
            "detail": "Career movement approved and employee profile updated.",
            "status": row.status,
        })
