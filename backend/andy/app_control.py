import re

from django.utils import timezone


class AndyAppControl:
    """Deterministic, permission-scoped ARI SMART RO tools for ANDY.

    Release-candidate read tools are deliberately bounded and role-aware. The
    LLM never receives unrestricted ORM access and this layer never mutates
    business records.
    """

    def __init__(self, user):
        self.user = user

    @staticmethod
    def _norm(text):
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    @staticmethod
    def _has(q, *phrases):
        return any(phrase in q for phrase in phrases)

    def _engineer(self):
        try:
            profile = self.user.employee_profile
        except Exception:
            return None
        return profile if getattr(profile, "designation", None) == "ENGINEER" else None

    def _customer(self):
        try:
            return self.user.customer_profile
        except Exception:
            return None

    def _capabilities(self):
        role = getattr(self.user, "role", "")
        if role == "ENGINEER":
            detail = (
                "aaj aur pending jobs, assigned complaints, services, installations aur "
                "engineer bag inventory dekh sakta hoon"
            )
        elif role == "CUSTOMER":
            detail = "aapki complaints, services aur installations ka status dekh sakta hoon"
        elif role in ("ADMIN", "MANAGER"):
            detail = "operations summary, pending jobs, complaints, services aur installations dekh sakta hoon"
        else:
            detail = "aapke role ke allowed ARI SMART RO records dekh sakta hoon"
        return {
            "handled": True,
            "intent": "capabilities",
            "answer": (
                f"Main ANDY hoon, ARI SMART RO ka private AI assistant. Main {detail}. "
                "Main Hindi, English aur Hinglish mein baat kar sakta hoon. "
                "Data-changing actions abhi approval-gated phase ke liye locked hain."
            ),
        }

    def _engineer_jobs(self, q, engineer):
        if not self._has(q, "job", "jobs", "काम", "kaam"):
            return None
        from jobs.models import Job

        qs = Job.objects.filter(engineer=engineer).select_related("customer").order_by("scheduled_date")
        today = timezone.localdate()
        if self._has(q, "today", "aaj", "आज"):
            qs = qs.filter(scheduled_date__date=today)
            intent, label = "engineer_today_jobs", "aaj"
        elif self._has(q, "pending", "बाकी", "baki", "remaining"):
            qs = qs.exclude(status__in=("COMPLETED", "CANCELLED"))
            intent, label = "engineer_pending_jobs", "pending"
        else:
            return None

        jobs = list(qs[:10])
        if not jobs:
            return {"handled": True, "intent": intent, "answer": f"Aapke {label} koi jobs nahi mile."}
        lines = []
        for job in jobs:
            when = timezone.localtime(job.scheduled_date).strftime("%I:%M %p")
            status = job.status.replace("_", " ").title()
            lines.append(f"{job.job_id}: {job.job_type.title()}, {job.customer}, {when}, status {status}.")
        return {
            "handled": True,
            "intent": intent,
            "answer": f"Aapke {label} {len(jobs)} job mile: " + " ".join(lines),
        }

    def _engineer_complaints(self, q, engineer):
        if not self._has(q, "complaint", "complaints", "शिकायत", "shikayat"):
            return None
        from complaints.models import Complaint

        qs = Complaint.objects.filter(engineer=engineer).select_related("customer").order_by("-complaint_date")
        if self._has(q, "pending", "open", "बाकी", "baki"):
            qs = qs.exclude(status__in=("RESOLVED", "CLOSED", "CANCELLED"))
        rows = list(qs[:10])
        if not rows:
            return {"handled": True, "intent": "engineer_complaints", "answer": "Aapki koi matching complaint nahi mili."}
        lines = [
            f"{x.complaint_id}: {x.customer}, {x.get_complaint_type_display()}, {x.status.replace('_', ' ').title()}, priority {x.priority.title()}."
            for x in rows
        ]
        return {"handled": True, "intent": "engineer_complaints", "answer": f"{len(rows)} complaint mili: " + " ".join(lines)}

    def _engineer_services(self, q, engineer):
        if not self._has(q, "service", "services", "सर्विस"):
            return None
        from service.models import Service

        qs = Service.objects.filter(engineer=engineer).select_related("customer").order_by("scheduled_date")
        if self._has(q, "today", "aaj", "आज"):
            qs = qs.filter(scheduled_date__date=timezone.localdate())
        elif self._has(q, "pending", "बाकी", "baki"):
            qs = qs.exclude(status__in=("COMPLETED", "CANCELLED"))
        rows = list(qs[:10])
        if not rows:
            return {"handled": True, "intent": "engineer_services", "answer": "Aapki koi matching service nahi mili."}
        lines = [
            f"{x.service_id}: {x.customer}, {x.get_service_type_display()}, {x.status.replace('_', ' ').title()}."
            for x in rows
        ]
        return {"handled": True, "intent": "engineer_services", "answer": f"{len(rows)} service mili: " + " ".join(lines)}

    def _engineer_installations(self, q, engineer):
        if not self._has(q, "installation", "installations", "इंस्टॉलेशन", "install"):
            return None
        from installation.models import Installation

        qs = Installation.objects.filter(engineer=engineer).select_related("customer").order_by("scheduled_date")
        if self._has(q, "today", "aaj", "आज"):
            qs = qs.filter(scheduled_date__date=timezone.localdate())
        elif self._has(q, "pending", "बाकी", "baki"):
            qs = qs.exclude(status__in=("COMPLETED", "CANCELLED"))
        rows = list(qs[:10])
        if not rows:
            return {"handled": True, "intent": "engineer_installations", "answer": "Aapki koi matching installation nahi mili."}
        lines = [
            f"{x.installation_id}: {x.customer}, {x.get_business_type_display()}, {x.status.replace('_', ' ').title()}."
            for x in rows
        ]
        return {"handled": True, "intent": "engineer_installations", "answer": f"{len(rows)} installation mili: " + " ".join(lines)}

    def _engineer_bag(self, q, engineer):
        if not self._has(q, "bag", "inventory", "parts", "part", "बैग", "सामान"):
            return None
        from inventory.models import EngineerBagItem

        rows = list(
            EngineerBagItem.objects.filter(engineer=engineer, status="ISSUED")
            .select_related("inventory_item__part")
            .order_by("-issue_date")[:20]
        )
        if not rows:
            return {"handled": True, "intent": "engineer_bag", "answer": "Aapke engineer bag mein koi issued item nahi mila."}
        lines = []
        for row in rows:
            item = row.inventory_item
            serial = item.serial_number or f"Inventory {item.id}"
            lines.append(f"{item.part}: {serial}.")
        return {"handled": True, "intent": "engineer_bag", "answer": f"Aapke bag mein {len(rows)} issued item hain: " + " ".join(lines)}

    def _customer_records(self, q, customer):
        if self._has(q, "complaint", "complaints", "शिकायत", "shikayat"):
            rows = list(customer.complaints.order_by("-complaint_date")[:10])
            if not rows:
                return {"handled": True, "intent": "customer_complaints", "answer": "Aapki koi complaint nahi mili."}
            lines = [f"{x.complaint_id}: {x.get_complaint_type_display()}, status {x.status.replace('_', ' ').title()}." for x in rows]
            return {"handled": True, "intent": "customer_complaints", "answer": f"Aapki {len(rows)} complaint mili: " + " ".join(lines)}

        if self._has(q, "service", "services", "सर्विस"):
            rows = list(customer.services.order_by("-scheduled_date")[:10])
            if not rows:
                return {"handled": True, "intent": "customer_services", "answer": "Aapki koi service nahi mili."}
            lines = [f"{x.service_id}: {x.get_service_type_display()}, status {x.status.replace('_', ' ').title()}." for x in rows]
            return {"handled": True, "intent": "customer_services", "answer": f"Aapki {len(rows)} service mili: " + " ".join(lines)}

        if self._has(q, "installation", "installations", "इंस्टॉलेशन", "install"):
            rows = list(customer.installations.order_by("-scheduled_date")[:10])
            if not rows:
                return {"handled": True, "intent": "customer_installations", "answer": "Aapki koi installation nahi mili."}
            lines = [f"{x.installation_id}: {x.get_business_type_display()}, status {x.status.replace('_', ' ').title()}." for x in rows]
            return {"handled": True, "intent": "customer_installations", "answer": f"Aapki {len(rows)} installation mili: " + " ".join(lines)}
        return None

    def _operations_summary(self, q):
        if getattr(self.user, "role", "") not in ("ADMIN", "MANAGER"):
            return None
        if not self._has(q, "summary", "dashboard", "operations", "status", "सारांश", "overview"):
            return None

        from complaints.models import Complaint
        from installation.models import Installation
        from jobs.models import Job
        from service.models import Service

        pending_jobs = Job.objects.exclude(status__in=("COMPLETED", "CANCELLED")).count()
        open_complaints = Complaint.objects.exclude(status__in=("RESOLVED", "CLOSED", "CANCELLED")).count()
        pending_services = Service.objects.exclude(status__in=("COMPLETED", "CANCELLED")).count()
        pending_installations = Installation.objects.exclude(status__in=("COMPLETED", "CANCELLED")).count()
        return {
            "handled": True,
            "intent": "operations_summary",
            "answer": (
                f"Current operations summary: {pending_jobs} pending jobs, {open_complaints} open complaints, "
                f"{pending_services} pending services aur {pending_installations} pending installations."
            ),
        }

    def try_handle(self, text):
        q = self._norm(text)

        if self._has(q, "taiyar", "tayyar", "ready", "तैयार"):
            return {
                "handled": True,
                "intent": "readiness",
                "answer": "Haan, main taiyar hoon. Batayiye, main aapki kya madad karoon?",
            }

        if "hindi" in q or "हिंदी" in q or "हिन्दी" in q:
            if self._has(q, "aati", "samajh", "understand", "bol", "speak", "आती", "समझ", "बोल"):
                return {
                    "handled": True,
                    "intent": "language_support",
                    "answer": "Haan, mujhe Hindi aur Hinglish samajh aati hai. Aap Hindi mein baat kar sakte hain.",
                }

        if self._has(
            q,
            "what can you do", "what all can you do", "tum kya kar sakte",
            "tum kya kya kar sakte", "aap kya kar sakte", "क्या कर सकते",
            "क्या क्या कर सकते", "kya kar sakte", "kya kya kar sakte",
        ):
            return self._capabilities()

        summary = self._operations_summary(q)
        if summary:
            return summary

        engineer = self._engineer()
        if engineer:
            for handler in (
                self._engineer_jobs,
                self._engineer_complaints,
                self._engineer_services,
                self._engineer_installations,
                self._engineer_bag,
            ):
                result = handler(q, engineer)
                if result:
                    return result

        if getattr(self.user, "role", "") == "CUSTOMER":
            customer = self._customer()
            if customer is None and self._has(q, "complaint", "service", "installation", "status"):
                return {
                    "handled": True,
                    "intent": "customer_profile_missing",
                    "answer": "Aapka customer profile is login se linked nahi hai. Admin se account linking check karwaiye.",
                }
            if customer:
                result = self._customer_records(q, customer)
                if result:
                    return result

        return None
