import re

from django.db import transaction
from django.utils import timezone

from .models import AndyPendingAction


class AndyActionControl:
    """Safe write-action layer for ANDY.

    The LLM never writes business data directly. Natural-language requests are
    converted into a pending action. A second explicit confirmation call is
    required before the existing domain service executes the mutation.
    """

    JOB_ID_RE = re.compile(r"\bJOB-\d{4}-\d{6}\b", re.IGNORECASE)

    STATUS_PHRASES = (
        ("ON_THE_WAY", ("on the way", "on my way", "nikal gaya", "nikal raha", "रास्ते", "निकल")),
        ("ARRIVED", ("arrived", "reached", "pahunch gaya", "pahuch gaya", "पहुँच", "पहुंच")),
        ("IN_PROGRESS", ("start work", "start job", "in progress", "kaam start", "काम शुरू", "काम चालू")),
        ("COMPLETED", ("complete job", "job complete", "mark complete", "काम पूरा", "job pura", "job poora")),
        ("ACCEPTED", ("accept job", "job accept", "स्वीकार", "accept karo")),
    )

    def __init__(self, user):
        self.user = user

    @staticmethod
    def _norm(text):
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    def _engineer(self):
        try:
            profile = self.user.employee_profile
        except Exception:
            return None
        return profile if getattr(profile, "designation", None) == "ENGINEER" else None

    def propose(self, text):
        """Return a pending action response when text clearly requests a write."""
        engineer = self._engineer()
        if engineer is None:
            return None

        q = self._norm(text)
        new_status = None
        for status, phrases in self.STATUS_PHRASES:
            if any(phrase in q for phrase in phrases):
                new_status = status
                break
        if new_status is None:
            return None

        match = self.JOB_ID_RE.search((text or "").upper())
        if match is None:
            return {
                "handled": True,
                "intent": "job_action_needs_id",
                "answer": "Action karne ke liye exact job ID boliye, jaise JOB-2026-000123.",
                "requires_confirmation": False,
            }

        from jobs.models import Job

        job_id = match.group(0).upper()
        job = Job.objects.filter(job_id=job_id, engineer=engineer).first()
        if job is None:
            return {
                "handled": True,
                "intent": "job_action_not_allowed",
                "answer": f"{job_id} aapko assigned job ke roop mein nahi mila, isliye main us par action nahi karunga.",
                "requires_confirmation": False,
            }

        existing = AndyPendingAction.objects.filter(
            user=self.user,
            action_type="JOB_STATUS_CHANGE",
            target_type="JOB",
            target_id=job.job_id,
            status="PENDING",
        ).first()
        if existing:
            existing.status = "CANCELLED"
            existing.resolved_at = timezone.now()
            existing.result = {"reason": "superseded_by_new_request"}
            existing.save(update_fields=["status", "resolved_at", "result"])

        summary = f"{job.job_id} ka status {job.status} se {new_status} karna"
        action = AndyPendingAction.objects.create(
            user=self.user,
            action_type="JOB_STATUS_CHANGE",
            target_type="JOB",
            target_id=job.job_id,
            payload={"new_status": new_status},
            summary=summary,
        )
        return {
            "handled": True,
            "intent": "job_status_confirmation",
            "answer": f"Confirm karein: kya main {summary.replace('_', ' ')}?",
            "requires_confirmation": True,
            "pending_action_id": action.id,
            "action_summary": action.summary,
        }

    @transaction.atomic
    def resolve(self, action_id, confirm):
        action = AndyPendingAction.objects.select_for_update().filter(
            id=action_id,
            user=self.user,
        ).first()
        if action is None:
            return {"ok": False, "status_code": 404, "message": "Pending ANDY action not found."}
        if action.status != "PENDING":
            return {"ok": False, "status_code": 409, "message": f"Action already {action.status.lower()}."}

        if not confirm:
            action.status = "CANCELLED"
            action.resolved_at = timezone.now()
            action.result = {"cancelled_by_user": True}
            action.save(update_fields=["status", "resolved_at", "result"])
            return {"ok": True, "status": "CANCELLED", "answer": "Theek hai, action cancel kar diya."}

        engineer = self._engineer()
        if engineer is None:
            return self._fail(action, "Only the assigned engineer can confirm this action.")

        if action.action_type != "JOB_STATUS_CHANGE" or action.target_type != "JOB":
            return self._fail(action, "Unsupported ANDY action type.")

        from jobs.models import Job
        from jobs.services import change_job_status

        job = Job.objects.select_for_update().filter(
            job_id=action.target_id,
            engineer=engineer,
        ).first()
        if job is None:
            return self._fail(action, "Job is no longer assigned to this engineer.")

        new_status = (action.payload or {}).get("new_status")
        try:
            change_job_status(job, new_status)
        except ValueError as exc:
            return self._fail(action, str(exc))

        action.status = "CONFIRMED"
        action.resolved_at = timezone.now()
        action.result = {"job_id": job.job_id, "new_status": job.status}
        action.save(update_fields=["status", "resolved_at", "result"])
        return {
            "ok": True,
            "status": "CONFIRMED",
            "answer": f"Done. {job.job_id} ka status ab {job.status.replace('_', ' ').title()} hai.",
            "job_id": job.job_id,
            "new_status": job.status,
        }

    @staticmethod
    def _fail(action, message):
        action.status = "FAILED"
        action.resolved_at = timezone.now()
        action.result = {"error": message}
        action.save(update_fields=["status", "resolved_at", "result"])
        return {"ok": False, "status_code": 422, "message": message}
