import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import HasRequiredFeature, has_feature_access, request_company
from tenancy.models import CompanyMembership

from .hr_lifecycle_models import EmployeeHrLifecycle, EmployeeHrLifecycleEvent
from .hr_phase2_ats_models import CandidateOffer, HrLetter, InterviewFeedback, InterviewRound
from .hr_phase2_recruitment_models import CandidateApplication, RecruitmentAuditEvent
from .models import EmployeeProfile

User = get_user_model()
SUPPORTED_DESIGNATIONS = {row[0] for row in EmployeeProfile.DESIGNATION_CHOICES}
VALID_INTERVIEW_TYPES = {row[0] for row in InterviewRound.TYPE_CHOICES}
VALID_RECOMMENDATIONS = {row[0] for row in InterviewFeedback.RECOMMENDATION_CHOICES}


def _audit(request, *, company, entity_type, entity_id, action, from_status="", to_status="", reason="", metadata=None):
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
    parsed = parse_date(str(value or ""))
    if parsed is None:
        raise ValueError
    return parsed


def _datetime(value):
    parsed = parse_datetime(str(value or ""))
    if parsed is None:
        raise ValueError
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _money(value):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError
    if parsed < 0:
        raise ValueError
    return parsed


def _is_recruitment_manager(request):
    return has_feature_access(request, "hrms_recruitment_manage")


def _user_in_company(company, user):
    if user is None or not user.is_active:
        return False
    if CompanyMembership.objects.filter(company=company, user=user, is_active=True).exists():
        return True
    try:
        return user.employee_profile.company_id == company.id
    except (AttributeError, EmployeeProfile.DoesNotExist):
        return False


def _offer_snapshot(offer):
    candidate = offer.application.candidate
    company = offer.company
    return {
        "candidate": {
            "name": candidate.full_name,
            "phone": candidate.phone,
            "email": candidate.email,
        },
        "company": {
            "id": company.id,
            "name": company.name,
            "legal_name": company.legal_name,
            "email": company.email,
            "phone": company.phone,
            "address": company.address,
        },
        "job_title": offer.job_title,
        "department": offer.department,
        "designation": offer.designation,
        "employment_type": offer.employment_type,
        "compensation": str(offer.compensation),
        "work_location": offer.work_location,
        "proposed_joining_date": offer.proposed_joining_date.isoformat(),
        "probation_terms": offer.probation_terms,
        "validity_date": offer.validity_date.isoformat(),
    }


def _create_offer_letter(request, offer):
    snapshot = _offer_snapshot(offer)
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return HrLetter.objects.create(
        company=offer.company,
        letter_type="OFFER",
        candidate_offer=offer,
        subject=f"Offer Letter - {offer.job_title}",
        snapshot=snapshot,
        content_hash=digest,
        version=1,
        issued_by=request.user,
    )


class InterviewRoundAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    def get(self, request):
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company membership is required."}, status=403)
        rows = InterviewRound.objects.filter(company=company).select_related(
            "application__candidate", "application__job_opening", "interviewer"
        )
        if not _is_recruitment_manager(request):
            rows = rows.filter(interviewer=request.user)
        return Response({"interviews": [{
            "id": row.id,
            "application_id": row.application_id,
            "candidate_name": row.application.candidate.full_name,
            "job_title": row.application.job_opening.title,
            "round_number": row.round_number,
            "round_type": row.round_type,
            "interviewer_id": row.interviewer_id,
            "interviewer_name": row.interviewer.get_full_name() or row.interviewer.phone,
            "scheduled_at": row.scheduled_at,
            "location": row.location,
            "meeting_reference": row.meeting_reference,
            "instructions": row.instructions,
            "status": row.status,
            "feedback_submitted": row.feedback_entries.exists(),
        } for row in rows[:1000]]})

    def post(self, request):
        if not _is_recruitment_manager(request):
            return Response({"detail": "Recruitment management permission is required."}, status=403)
        company = request_company(request)
        application = CandidateApplication.objects.filter(company=company, pk=request.data.get("application_id")).select_related("candidate", "job_opening").first()
        interviewer = User.objects.filter(pk=request.data.get("interviewer_id"), is_active=True).first()
        if application is None:
            return Response({"detail": "Application not found in this company."}, status=404)
        if interviewer is None or not _user_in_company(company, interviewer):
            return Response({"detail": "Interviewer must belong to the same company."}, status=400)
        try:
            round_number = int(request.data.get("round_number"))
            scheduled_at = _datetime(request.data.get("scheduled_at"))
        except (TypeError, ValueError):
            return Response({"detail": "Valid round number and scheduled date/time are required."}, status=400)
        round_type = str(request.data.get("round_type") or "").upper()
        if round_number < 1 or round_type not in VALID_INTERVIEW_TYPES:
            return Response({"detail": "Invalid interview round type or number."}, status=400)
        try:
            with transaction.atomic():
                row = InterviewRound.objects.create(
                    company=company,
                    application=application,
                    round_number=round_number,
                    round_type=round_type,
                    interviewer=interviewer,
                    scheduled_at=scheduled_at,
                    location=str(request.data.get("location") or "").strip()[:160],
                    meeting_reference=str(request.data.get("meeting_reference") or "").strip()[:300],
                    instructions=str(request.data.get("instructions") or "").strip(),
                    created_by=request.user,
                )
                if application.stage == "SCREENING":
                    application.stage = "INTERVIEW"
                    application.save(update_fields=["stage", "updated_at"])
        except IntegrityError:
            return Response({"detail": "This interview round number already exists for the application."}, status=409)
        _audit(request, company=company, entity_type="INTERVIEW_ROUND", entity_id=row.id, action="SCHEDULED", to_status=row.status, metadata={"application_id": application.id, "interviewer_id": interviewer.id})
        return Response({"id": row.id, "status": row.status}, status=201)


class InterviewRoundActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    @transaction.atomic
    def post(self, request, interview_id):
        company = request_company(request)
        row = InterviewRound.objects.select_for_update().filter(company=company, pk=interview_id).first()
        if row is None:
            return Response({"detail": "Interview not found."}, status=404)
        if row.interviewer_id != request.user.id and not _is_recruitment_manager(request):
            return Response({"detail": "You are not authorized for this interview."}, status=403)
        action = str(request.data.get("action") or "").upper()
        reason = str(request.data.get("reason") or "").strip()
        previous = row.status
        if previous != "SCHEDULED":
            return Response({"detail": "Only scheduled interviews can be actioned."}, status=400)
        if action == "COMPLETE":
            if not row.feedback_entries.exists():
                return Response({"detail": "Interview feedback must be submitted before completion."}, status=400)
            row.status = "COMPLETED"
        elif action in {"CANCEL", "NO_SHOW"}:
            if not reason:
                return Response({"detail": "Reason is required."}, status=400)
            row.status = "CANCELLED" if action == "CANCEL" else "NO_SHOW"
        else:
            return Response({"detail": "Invalid interview action."}, status=400)
        row.save(update_fields=["status", "updated_at"])
        _audit(request, company=company, entity_type="INTERVIEW_ROUND", entity_id=row.id, action=action, from_status=previous, to_status=row.status, reason=reason)
        return Response({"id": row.id, "status": row.status})


class InterviewFeedbackAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    def post(self, request, interview_id):
        company = request_company(request)
        row = InterviewRound.objects.filter(company=company, pk=interview_id).first()
        if row is None:
            return Response({"detail": "Interview not found."}, status=404)
        if row.interviewer_id != request.user.id:
            return Response({"detail": "Only the assigned interviewer may submit feedback."}, status=403)
        if row.status != "SCHEDULED":
            return Response({"detail": "Feedback can only be submitted for a scheduled interview."}, status=400)
        try:
            rating = int(request.data.get("rating"))
        except (TypeError, ValueError):
            return Response({"detail": "Rating must be between 1 and 5."}, status=400)
        recommendation = str(request.data.get("recommendation") or "").upper()
        if rating < 1 or rating > 5 or recommendation not in VALID_RECOMMENDATIONS:
            return Response({"detail": "Valid rating and recommendation are required."}, status=400)
        try:
            with transaction.atomic():
                feedback = InterviewFeedback.objects.create(
                    company=company,
                    interview_round=row,
                    interviewer=request.user,
                    rating=rating,
                    recommendation=recommendation,
                    strengths=str(request.data.get("strengths") or "").strip(),
                    concerns=str(request.data.get("concerns") or "").strip(),
                    notes=str(request.data.get("notes") or "").strip(),
                )
        except IntegrityError:
            return Response({"detail": "Final feedback has already been submitted for this interview."}, status=409)
        _audit(request, company=company, entity_type="INTERVIEW_FEEDBACK", entity_id=feedback.id, action="SUBMITTED", metadata={"interview_id": row.id, "recommendation": recommendation, "rating": rating})
        return Response({"id": feedback.id, "submitted_at": feedback.submitted_at}, status=201)


class CandidateDecisionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    @transaction.atomic
    def post(self, request, application_id):
        company = request_company(request)
        row = CandidateApplication.objects.select_for_update().filter(company=company, pk=application_id).first()
        if row is None:
            return Response({"detail": "Application not found."}, status=404)
        action = str(request.data.get("action") or "").upper()
        reason = str(request.data.get("reason") or "").strip()
        previous = row.stage
        if action == "SELECT":
            if not has_feature_access(request, "hrms_recruitment_approve"):
                return Response({"detail": "Recruitment approval permission is required."}, status=403)
            if not reason:
                return Response({"detail": "Selection decision note is required."}, status=400)
            if row.stage != "INTERVIEW":
                return Response({"detail": "Application must be in INTERVIEW stage."}, status=400)
            completed = row.interview_rounds.filter(status="COMPLETED", feedback_entries__isnull=False).distinct().exists()
            if not completed:
                return Response({"detail": "At least one completed interview with feedback is required."}, status=400)
            row.stage = "SELECTED"
            row.rejection_reason = ""
        elif action == "REJECT":
            if not has_feature_access(request, "hrms_recruitment_manage") and not has_feature_access(request, "hrms_recruitment_approve"):
                return Response({"detail": "Recruitment management permission is required."}, status=403)
            if not reason:
                return Response({"detail": "Rejection reason is required."}, status=400)
            if row.stage in {"JOINED", "WITHDRAWN", "REJECTED"}:
                return Response({"detail": "Application cannot be rejected from its current stage."}, status=400)
            row.stage = "REJECTED"
            row.rejection_reason = reason[:500]
        elif action == "REOPEN":
            if not has_feature_access(request, "hrms_recruitment_approve"):
                return Response({"detail": "Recruitment approval permission is required."}, status=403)
            if row.stage != "REJECTED" or not reason:
                return Response({"detail": "Rejected application and reopen reason are required."}, status=400)
            row.stage = "INTERVIEW" if row.interview_rounds.exists() else "SCREENING"
            row.rejection_reason = ""
        else:
            return Response({"detail": "Invalid decision action."}, status=400)
        row.save(update_fields=["stage", "rejection_reason", "updated_at"])
        _audit(request, company=company, entity_type="CANDIDATE_APPLICATION", entity_id=row.id, action=action, from_status=previous, to_status=row.stage, reason=reason)
        return Response({"id": row.id, "stage": row.stage})


class CandidateOfferAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    def get(self, request):
        company = request_company(request)
        rows = CandidateOffer.objects.filter(company=company).select_related("application__candidate")
        return Response({"offers": [{
            "id": row.id,
            "application_id": row.application_id,
            "candidate_name": row.application.candidate.full_name,
            "job_title": row.job_title,
            "department": row.department,
            "designation": row.designation,
            "employment_type": row.employment_type,
            "proposed_joining_date": row.proposed_joining_date,
            "work_location": row.work_location,
            "compensation": row.compensation,
            "validity_date": row.validity_date,
            "status": row.status,
        } for row in rows[:1000]]})

    def post(self, request):
        if not _is_recruitment_manager(request):
            return Response({"detail": "Recruitment management permission is required."}, status=403)
        company = request_company(request)
        application = CandidateApplication.objects.filter(company=company, pk=request.data.get("application_id"), stage="SELECTED").select_related("job_opening__requisition").first()
        if application is None:
            return Response({"detail": "Selected application is required."}, status=400)
        req = application.job_opening.requisition
        try:
            joining_date = _date(request.data.get("proposed_joining_date"))
            validity_date = _date(request.data.get("validity_date"))
            compensation = _money(request.data.get("compensation"))
        except ValueError:
            return Response({"detail": "Valid joining date, validity date and compensation are required."}, status=400)
        if validity_date < timezone.localdate():
            return Response({"detail": "Offer validity date cannot be in the past."}, status=400)
        try:
            with transaction.atomic():
                offer = CandidateOffer.objects.create(
                    company=company,
                    application=application,
                    job_title=application.job_opening.title,
                    department=req.department,
                    designation=req.designation,
                    employment_type=req.employment_type,
                    proposed_joining_date=joining_date,
                    work_location=str(request.data.get("work_location") or req.location).strip()[:120],
                    compensation=compensation,
                    probation_terms=str(request.data.get("probation_terms") or "").strip()[:500],
                    validity_date=validity_date,
                    hr_notes=str(request.data.get("hr_notes") or "").strip(),
                    created_by=request.user,
                )
        except IntegrityError:
            return Response({"detail": "An offer already exists for this application."}, status=409)
        _audit(request, company=company, entity_type="CANDIDATE_OFFER", entity_id=offer.id, action="CREATED", to_status=offer.status)
        return Response({"id": offer.id, "status": offer.status}, status=201)


class CandidateOfferActionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    @transaction.atomic
    def post(self, request, offer_id):
        company = request_company(request)
        offer = CandidateOffer.objects.select_for_update().filter(company=company, pk=offer_id).select_related("application__candidate", "application__job_opening__requisition").first()
        if offer is None:
            return Response({"detail": "Offer not found."}, status=404)
        action = str(request.data.get("action") or "").upper()
        reason = str(request.data.get("reason") or "").strip()
        previous = offer.status
        now = timezone.now()
        today = timezone.localdate()
        if action == "SUBMIT":
            if not _is_recruitment_manager(request) or offer.status != "DRAFT":
                return Response({"detail": "Only a draft offer can be submitted by recruitment management."}, status=400)
            offer.status = "PENDING_APPROVAL"
        elif action == "APPROVE":
            if not has_feature_access(request, "hrms_recruitment_offer_approve"):
                return Response({"detail": "Offer approval permission is required."}, status=403)
            if offer.status != "PENDING_APPROVAL":
                return Response({"detail": "Only pending offers can be approved."}, status=400)
            offer.status = "APPROVED"
            offer.approval_note = reason[:1000]
            offer.approved_by = request.user
            offer.approved_at = now
        elif action == "ISSUE":
            if not _is_recruitment_manager(request) or offer.status != "APPROVED":
                return Response({"detail": "Only an approved offer can be issued."}, status=400)
            if offer.validity_date < today:
                offer.status = "EXPIRED"
                offer.save(update_fields=["status", "updated_at"])
                return Response({"detail": "Offer has expired and cannot be issued."}, status=400)
            if HrLetter.objects.filter(candidate_offer=offer, letter_type="OFFER").exists():
                return Response({"detail": "Offer letter has already been issued."}, status=409)
            offer.status = "ISSUED"
            offer.issued_at = now
            offer.application.stage = "OFFERED"
            offer.application.save(update_fields=["stage", "updated_at"])
            letter = _create_offer_letter(request, offer)
        elif action in {"ACCEPT", "DECLINE"}:
            if not _is_recruitment_manager(request):
                return Response({"detail": "Recruitment management permission is required."}, status=403)
            if offer.status != "ISSUED":
                return Response({"detail": "Only an issued offer can receive a response."}, status=400)
            if offer.validity_date < today:
                offer.status = "EXPIRED"
                offer.save(update_fields=["status", "updated_at"])
                return Response({"detail": "Expired offer cannot be accepted or declined as active."}, status=400)
            offer.status = "ACCEPTED" if action == "ACCEPT" else "DECLINED"
            offer.accepted_at = now if action == "ACCEPT" else None
            offer.declined_at = now if action == "DECLINE" else None
            offer.response_actor = request.user
            offer.response_note = reason[:1000]
            evidence = request.data.get("evidence") or {}
            offer.response_evidence = evidence if isinstance(evidence, dict) else {"reference": str(evidence)[:500]}
        elif action == "EXPIRE":
            if not _is_recruitment_manager(request) or offer.status not in {"DRAFT", "PENDING_APPROVAL", "APPROVED", "ISSUED"}:
                return Response({"detail": "Offer cannot be expired from its current state."}, status=400)
            offer.status = "EXPIRED"
        elif action == "WITHDRAW":
            if not _is_recruitment_manager(request) or offer.status in {"ACCEPTED", "DECLINED", "EXPIRED", "WITHDRAWN"}:
                return Response({"detail": "Offer cannot be withdrawn from its current state."}, status=400)
            if not reason:
                return Response({"detail": "Withdrawal reason is required."}, status=400)
            offer.status = "WITHDRAWN"
        else:
            return Response({"detail": "Invalid offer action."}, status=400)
        offer.save()
        _audit(request, company=company, entity_type="CANDIDATE_OFFER", entity_id=offer.id, action=action, from_status=previous, to_status=offer.status, reason=reason)
        payload = {"id": offer.id, "status": offer.status}
        if action == "ISSUE":
            payload["letter_id"] = letter.id
            payload["content_hash"] = letter.content_hash
        return Response(payload)


class CandidateConvertAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms_recruitment_view"

    @transaction.atomic
    def post(self, request, application_id):
        if not has_feature_access(request, "hrms_recruitment_convert"):
            return Response({"detail": "Recruitment conversion permission is required."}, status=403)
        company = request_company(request)
        application = CandidateApplication.objects.select_for_update().filter(company=company, pk=application_id).select_related("candidate", "job_opening__requisition").first()
        if application is None:
            return Response({"detail": "Application not found."}, status=404)
        if application.converted_employee_id:
            employee = application.converted_employee
            return Response({"employee_id": employee.id, "employee_code": employee.employee_id, "idempotent": True})
        offer = CandidateOffer.objects.select_for_update().filter(company=company, application=application, status="ACCEPTED").first()
        if offer is None:
            return Response({"detail": "Accepted offer is required before conversion."}, status=400)
        if application.candidate.company_id != company.id or application.job_opening.company_id != company.id or offer.company_id != company.id:
            return Response({"detail": "Cross-company conversion is not allowed."}, status=400)

        joined_count = CandidateApplication.objects.filter(job_opening=application.job_opening, converted_employee__isnull=False).exclude(pk=application.pk).count()
        capacity_override = bool(request.data.get("capacity_override"))
        override_reason = str(request.data.get("override_reason") or "").strip()
        if joined_count >= application.job_opening.vacancies:
            if not capacity_override or str(getattr(request.user, "role", "")).upper() != "ADMIN" or not override_reason:
                return Response({"detail": "Approved vacancy capacity is exhausted. Admin override with reason is required."}, status=409)
            _audit(request, company=company, entity_type="JOB_OPENING", entity_id=application.job_opening_id, action="VACANCY_OVERRIDE", reason=override_reason, metadata={"joined_count": joined_count, "vacancies": application.job_opening.vacancies})

        designation = str(offer.designation or "").upper()
        if designation not in SUPPORTED_DESIGNATIONS:
            return Response({"detail": "Offer designation must be one of ENGINEER, MANAGER, OFFICE or CALLING before conversion."}, status=400)

        phone = application.candidate.phone.strip()
        if len(phone) != 10 or not phone.isdigit():
            return Response({"detail": "Candidate phone must be a valid 10-digit staff login number."}, status=400)
        user = User.objects.select_for_update().filter(phone=phone).first()
        if user is not None:
            if str(user.role or "").upper() == "CUSTOMER":
                return Response({"detail": "Candidate phone belongs to a customer account and cannot be reused silently."}, status=409)
            try:
                existing_profile = user.employee_profile
            except EmployeeProfile.DoesNotExist:
                existing_profile = None
            if existing_profile is not None:
                return Response({"detail": "Candidate phone already belongs to an employee account."}, status=409)
            if not CompanyMembership.objects.filter(company=company, user=user, is_active=True).exists():
                return Response({"detail": "Existing staff account is not an active member of this company."}, status=409)
        else:
            names = application.candidate.full_name.strip().split(maxsplit=1)
            user = User.objects.create_user(
                phone=phone,
                password=None,
                first_name=names[0][:100],
                last_name=names[1][:100] if len(names) > 1 else "",
                email=application.candidate.email,
                role=designation,
                is_verified=False,
            )
            CompanyMembership.objects.get_or_create(company=company, user=user, defaults={"role": "STAFF", "is_active": True})

        employee = EmployeeProfile.objects.create(
            company=company,
            user=user,
            joining_date=offer.proposed_joining_date,
            designation=designation,
            job_title=offer.job_title,
            department=offer.department,
            salary=offer.compensation,
            gender="OTHER",
        )
        lifecycle = EmployeeHrLifecycle.objects.select_for_update().get(employee=employee)
        lifecycle.employment_type = offer.employment_type
        lifecycle.work_location = offer.work_location
        lifecycle.compensation_profile = {
            "source": "RECRUITMENT_OFFER",
            "offer_id": offer.id,
            "annual_or_monthly_value": str(offer.compensation),
        }
        lifecycle.employment_status = "ONBOARDING"
        lifecycle.hr_stage = "CREATED"
        lifecycle.save(update_fields=["employment_type", "work_location", "compensation_profile", "employment_status", "hr_stage", "updated_at"])
        EmployeeHrLifecycleEvent.objects.create(
            employee=employee,
            event_type="RECRUITMENT_CONVERSION",
            from_status="SELECTED",
            to_status="ONBOARDING",
            note="Converted from accepted recruitment offer.",
            metadata={"application_id": application.id, "offer_id": offer.id, "candidate_id": application.candidate_id},
            created_by=request.user,
        )
        application.converted_employee = employee
        application.stage = "JOINED"
        application.save(update_fields=["converted_employee", "stage", "updated_at"])
        _audit(request, company=company, entity_type="CANDIDATE_APPLICATION", entity_id=application.id, action="CONVERTED_TO_EMPLOYEE", from_status="OFFERED", to_status="JOINED", reason=override_reason, metadata={"employee_id": employee.id, "offer_id": offer.id})
        return Response({"employee_id": employee.id, "employee_code": employee.employee_id, "idempotent": False}, status=201)
