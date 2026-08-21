import re
from django.utils import timezone


class AndyAppControl:
    """Deterministic, permission-scoped ARI SMART RO tools for ANDY.

    Phase 1 is deliberately read-only. The LLM never gets unrestricted ORM
    access and cannot mutate business data through this layer.
    """

    def __init__(self, user):
        self.user = user

    def _engineer(self):
        try:
            profile = self.user.employee_profile
        except Exception:
            return None
        return profile if getattr(profile, "designation", None) == "ENGINEER" else None

    @staticmethod
    def _norm(text):
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    def try_handle(self, text):
        q = self._norm(text)

        capability_phrases = (
            "what can you do", "what all can you do", "tum kya kar sakte",
            "tum kya kya kar sakte", "aap kya kar sakte", "क्या कर सकते",
            "क्या क्या कर सकते", "kya kar sakte", "kya kya kar sakte",
        )
        if any(p in q for p in capability_phrases):
            return {
                "handled": True,
                "intent": "capabilities",
                "answer": (
                    "Main ANDY hoon. Abhi main ARI SMART RO mein aapke role ke hisaab se "
                    "aaj ke jobs, pending jobs aur job status dekh sakta hoon. Main Hindi, "
                    "English aur Hinglish mein baat kar sakta hoon. Business data badalne wale "
                    "actions ko hum approval ke saath next phase mein jod rahe hain."
                ),
            }

        engineer = self._engineer()
        job_words = ("job", "jobs", "काम", "kaam")
        if engineer and any(w in q for w in job_words):
            from jobs.models import Job

            qs = Job.objects.filter(engineer=engineer).select_related("customer").order_by("scheduled_date")
            today = timezone.localdate()

            if any(p in q for p in ("today", "aaj", "आज")):
                qs = qs.filter(scheduled_date__date=today)
                intent = "engineer_today_jobs"
                label = "aaj"
            elif any(p in q for p in ("pending", "बाकी", "baki", "remaining")):
                qs = qs.exclude(status__in=("COMPLETED", "CANCELLED"))
                intent = "engineer_pending_jobs"
                label = "pending"
            else:
                return None

            jobs = list(qs[:10])
            if not jobs:
                return {"handled": True, "intent": intent, "answer": f"Aapke {label} koi jobs nahi mile."}

            lines = []
            for job in jobs:
                customer = str(job.customer)
                when = timezone.localtime(job.scheduled_date).strftime("%I:%M %p")
                lines.append(f"{job.job_id}: {job.job_type.title()}, {customer}, {when}, status {job.status.replace('_', ' ').title()}.")
            prefix = f"Aapke {label} {len(jobs)} job" + (" hain:" if len(jobs) != 1 else " hai:")
            return {"handled": True, "intent": intent, "answer": prefix + " " + " ".join(lines)}

        return None
