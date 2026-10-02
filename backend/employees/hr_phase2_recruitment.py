from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import HasRequiredFeature, has_feature_access, request_company

from .hr_lifecycle_models import EmployeeHrLifecycle
from .hr_phase2_recruitment_models import (
    Candidate,
    CandidateApplication,
    JobOpening,
    ManpowerRequisition,
    RecruitmentAuditEvent,
)

VALID_EMPLOYMENT_TYPES = {row[0] for row in EmployeeHrLifecycle.EMPLOYMENT_TYPES}


def _audit(request, *, entity_type, entity_id, action, from_status="", to_status="", reason="", metadata=None):
    company = request_company(request)
    RecruitmentAuditEvent.objects.create(
        company=company,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        metadata=metadata or {},
        performed_by=request.user,
    )


def _date(value):
    if not value:
        return None
    parsed = parse_date(str(value))
    if parsed is None:
        raise ValueError
    return parsed


def _money(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError


class RecruitmentSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    def get(self, request):
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company membership is required."}, status=403)
        reqs = ManpowerRequisition.objects.filter(company=company)
        jobs = JobOpening.objects.filter(company=company)
        apps = CandidateApplication.objects.filter(company=company)
        return Response({
            "requisitions": {
                "total": reqs.count(),
                "pending_approval": reqs.filter(status="PENDING_APPROVAL").count(),
                "approved": reqs.filter(status="APPROVED").count(),
            },
            "jobs": {"open": jobs.filter(status="OPEN").count()},
            "pipeline": {stage: apps.filter(stage=stage).count() for stage, _ in CandidateApplication.STAGE_CHOICES},
            "candidates": Candidate.objects.filter(company=company).count(),
        })


class ManpowerRequisitionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    def get(self, request):
        company = request_company(request)
        rows = ManpowerRequisition.objects.filter(company=company).select_related("requested_by", "approved_by")
        return Response({"requisitions": [{
            "id": row.id,
            "department": row.department,
            "job_title": row.job_title,
            "designation": row.designation,
            "positions": row.positions,
            "employment_type": row.employment_type,
            "location": row.location,
            "target_joining_date": row.target_joining_date,
            "justification": row.justification,
            "status": row.status,
            "requested_by": row.requested_by.get_full_name() or row.requested_by.phone,
            "approved_by": None if row.approved_by is None else (row.approved_by.get_full_name() or row.approved_by.phone),
            "rejection_reason": row.rejection_reason,
            "created_at": row.created_at,
        } for row in rows[:500]]})

    def post(self, request):
        if not has_feature_access(request, "hrms_recruitment_manage"):
            return Response({"detail": "Recruitment management permission is required."}, status=403)
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company membership is required."}, status=403)
        department = str(request.data.get("department") or "").strip()
        job_title = str(request.data.get("job_title") or "").strip()
        justification = str(request.data.get("justification") or "").strip()
        employment_type = str(request.data.get("employment_type") or "PROBATION").upper()
        try:
            positions = int(request.data.get("positions", 1))
            target = _date(request.data.get("target_joining_date"))
        except (TypeError, ValueError):
            return Response({"detail": "Valid positions and target joining date are required."}, status=400)
        if not department or not job_title or not justification or positions < 1:
            return Response({"detail": "Department, job title, positive positions and justification are required."}, status=400)
        if employment_type not in VALID_EMPLOYMENT_TYPES:
            return Response({"detail": "Invalid employment type."}, status=400)
        row = ManpowerRequisition.objects.create(
            company=company,
            department=department[:100],
            job_title=job_title[:120],
            designation=str(request.data.get("designation") or "").strip()[:20],
            positions=positions,
            employment_type=employment_type,
            location=str(request.data.get("location") or "").strip()[:120],
            target_joining_date=target,
            justification=justification,
            status="PENDING_APPROVAL",
            requested_by=request.user,
        )
        _audit(request, entity_type="MANPOWER_REQUISITION", entity_id=row.id, action="CREATED", to_status=row.status)
        return Response({"id": row.id, "status": row.status}, status=201)


class ManpowerRequisitionActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    @transaction.atomic
    def post(self, request, requisition_id):
        if not has_feature_access(request, "hrms_recruitment_approve"):
            return Response({"detail": "Manpower approval permission is required."}, status=403)
        company = request_company(request)
        row = ManpowerRequisition.objects.select_for_update().filter(company=company, pk=requisition_id).first()
        if row is None:
            return Response({"detail": "Requisition not found."}, status=404)
        action = str(request.data.get("action") or "").upper()
        previous = row.status
        if action == "APPROVE" and row.status == "PENDING_APPROVAL":
            row.status = "APPROVED"
            row.approved_by = request.user
            row.approved_at = timezone.now()
            row.rejection_reason = ""
        elif action == "REJECT" and row.status == "PENDING_APPROVAL":
            reason = str(request.data.get("reason") or "").strip()
            if not reason:
                return Response({"detail": "Rejection reason is required."}, status=400)
            row.status = "REJECTED"
            row.rejection_reason = reason[:500]
        elif action == "CLOSE" and row.status == "APPROVED":
            row.status = "CLOSED"
        else:
            return Response({"detail": "Invalid action for current requisition status."}, status=400)
        row.save()
        _audit(request, entity_type="MANPOWER_REQUISITION", entity_id=row.id, action=action, from_status=previous, to_status=row.status, reason=row.rejection_reason)
        return Response({"id": row.id, "status": row.status})


class JobOpeningAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    def get(self, request):
        company = request_company(request)
        rows = JobOpening.objects.filter(company=company).select_related("requisition")
        return Response({"jobs": [{
            "id": row.id, "requisition_id": row.requisition_id, "title": row.title,
            "vacancies": row.vacancies, "status": row.status,
            "description": row.description, "requirements": row.requirements,
        } for row in rows[:500]]})

    @transaction.atomic
    def post(self, request):
        if not has_feature_access(request, "hrms_recruitment_manage"):
            return Response({"detail": "Recruitment management permission is required."}, status=403)
        company = request_company(request)
        requisition = ManpowerRequisition.objects.select_for_update().filter(
            company=company, pk=request.data.get("requisition_id"), status="APPROVED"
        ).first()
        if requisition is None:
            return Response({"detail": "Approved requisition is required."}, status=400)
        if JobOpening.objects.filter(requisition=requisition).exists():
            return Response({"detail": "A job opening already exists for this requisition."}, status=409)
        row = JobOpening.objects.create(
            company=company,
            requisition=requisition,
            title=str(request.data.get("title") or requisition.job_title).strip()[:120],
            description=str(request.data.get("description") or "").strip(),
            requirements=str(request.data.get("requirements") or "").strip(),
            vacancies=requisition.positions,
            status="OPEN",
            opened_at=timezone.now(),
            created_by=request.user,
        )
        _audit(request, entity_type="JOB_OPENING", entity_id=row.id, action="OPENED", to_status="OPEN", metadata={"requisition_id": requisition.id})
        return Response({"id": row.id, "status": row.status}, status=201)


class CandidateAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    def get(self, request):
        company = request_company(request)
        rows = Candidate.objects.filter(company=company)
        query = str(request.query_params.get("q") or "").strip()
        if query:
            from django.db.models import Q
            rows = rows.filter(Q(full_name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query))
        return Response({"candidates": [{
            "id": row.id, "full_name": row.full_name, "phone": row.phone,
            "email": row.email, "city": row.city, "current_company": row.current_company,
            "current_title": row.current_title, "experience_years": row.experience_years,
            "source": row.source,
        } for row in rows[:500]]})

    def post(self, request):
        if not has_feature_access(request, "hrms_recruitment_manage"):
            return Response({"detail": "Recruitment management permission is required."}, status=403)
        company = request_company(request)
        full_name = str(request.data.get("full_name") or "").strip()
        phone = str(request.data.get("phone") or "").strip()
        if not full_name or not phone:
            return Response({"detail": "Candidate name and phone are required."}, status=400)
        try:
            experience = Decimal(str(request.data.get("experience_years", 0)))
        except (InvalidOperation, TypeError, ValueError):
            return Response({"detail": "Experience years must be numeric."}, status=400)
        try:
            row = Candidate.objects.create(
                company=company,
                full_name=full_name[:160], phone=phone[:20],
                email=str(request.data.get("email") or "").strip()[:254],
                city=str(request.data.get("city") or "").strip()[:100],
                current_company=str(request.data.get("current_company") or "").strip()[:160],
                current_title=str(request.data.get("current_title") or "").strip()[:120],
                experience_years=experience,
                source=str(request.data.get("source") or "").strip()[:80],
                resume=request.FILES.get("resume"),
                created_by=request.user,
            )
        except IntegrityError:
            return Response({"detail": "Candidate with this phone already exists in this company."}, status=409)
        _audit(request, entity_type="CANDIDATE", entity_id=row.id, action="CREATED")
        return Response({"id": row.id}, status=201)


class CandidateApplicationAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    def get(self, request):
        company = request_company(request)
        rows = CandidateApplication.objects.filter(company=company).select_related("candidate", "job_opening")
        stage = str(request.query_params.get("stage") or "").upper()
        if stage:
            rows = rows.filter(stage=stage)
        job_id = request.query_params.get("job_id")
        if job_id:
            rows = rows.filter(job_opening_id=job_id)
        return Response({"applications": [{
            "id": row.id, "candidate_id": row.candidate_id,
            "candidate_name": row.candidate.full_name, "job_id": row.job_opening_id,
            "job_title": row.job_opening.title, "stage": row.stage,
            "expected_salary": row.expected_salary, "available_from": row.available_from,
            "notes": row.notes, "rejection_reason": row.rejection_reason,
            "converted_employee_id": row.converted_employee_id,
        } for row in rows[:1000]]})

    def post(self, request):
        if not has_feature_access(request, "hrms_recruitment_manage"):
            return Response({"detail": "Recruitment management permission is required."}, status=403)
        company = request_company(request)
        candidate = Candidate.objects.filter(company=company, pk=request.data.get("candidate_id")).first()
        job = JobOpening.objects.filter(company=company, pk=request.data.get("job_id"), status="OPEN").first()
        if candidate is None or job is None:
            return Response({"detail": "Candidate and open job from the same company are required."}, status=400)
        try:
            expected_salary = _money(request.data.get("expected_salary"))
            available_from = _date(request.data.get("available_from"))
        except ValueError:
            return Response({"detail": "Expected salary or available-from date is invalid."}, status=400)
        try:
            row = CandidateApplication.objects.create(
                company=company, candidate=candidate, job_opening=job,
                expected_salary=expected_salary, available_from=available_from,
                notes=str(request.data.get("notes") or "").strip(), created_by=request.user,
            )
        except IntegrityError:
            return Response({"detail": "Candidate already applied to this job."}, status=409)
        _audit(request, entity_type="CANDIDATE_APPLICATION", entity_id=row.id, action="CREATED", to_status=row.stage)
        return Response({"id": row.id, "stage": row.stage}, status=201)


class CandidateApplicationActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    @transaction.atomic
    def post(self, request, application_id):
        if not has_feature_access(request, "hrms_recruitment_manage"):
            return Response({"detail": "Recruitment management permission is required."}, status=403)
        company = request_company(request)
        row = CandidateApplication.objects.select_for_update().filter(company=company, pk=application_id).first()
        if row is None:
            return Response({"detail": "Application not found."}, status=404)
        target = str(request.data.get("stage") or "").upper()
        allowed = {
            "APPLIED": {"SCREENING", "REJECTED", "WITHDRAWN"},
            "SCREENING": {"INTERVIEW", "REJECTED", "WITHDRAWN"},
            "INTERVIEW": {"SELECTED", "REJECTED", "WITHDRAWN"},
            "SELECTED": {"OFFERED", "REJECTED", "WITHDRAWN"},
            "OFFERED": {"JOINED", "WITHDRAWN"},
            "REJECTED": set(), "JOINED": set(), "WITHDRAWN": set(),
        }
        if target not in allowed.get(row.stage, set()):
            return Response({"detail": f"Cannot move application from {row.stage} to {target}."}, status=400)
        reason = str(request.data.get("reason") or "").strip()
        if target == "REJECTED" and not reason:
            return Response({"detail": "Rejection reason is required."}, status=400)
        previous = row.stage
        row.stage = target
        row.rejection_reason = reason[:500] if target == "REJECTED" else ""
        row.save(update_fields=["stage", "rejection_reason", "updated_at"])
        _audit(request, entity_type="CANDIDATE_APPLICATION", entity_id=row.id, action="STAGE_CHANGED", from_status=previous, to_status=target, reason=reason)
        return Response({"id": row.id, "stage": row.stage})
