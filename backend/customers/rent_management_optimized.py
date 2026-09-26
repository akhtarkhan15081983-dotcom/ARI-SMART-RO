import calendar
import json
from datetime import date, timedelta
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .models import Customer, CustomerRentHistory
from .rent_policy import RENT_GRACE_DAYS, rent_penalty
from .views import _sync_current_rent_offer


class InspectableStreamingHttpResponse(StreamingHttpResponse):
    """Streaming response with lazy DRF-style ``data`` introspection.

    Normal HTTP delivery remains streaming and memory bounded. The payload is
    materialized only when in-process code (primarily tests) explicitly reads
    ``response.data``; consumed chunks are then restored so the response can
    still be iterated normally.
    """

    _data_cache = None

    @property
    def data(self):
        if self._data_cache is None:
            chunks = list(self.streaming_content)
            self.streaming_content = iter(chunks)
            payload = b"".join(
                chunk
                if isinstance(chunk, bytes)
                else str(chunk).encode(self.charset or "utf-8")
                for chunk in chunks
            )
            self._data_cache = json.loads(payload.decode(self.charset or "utf-8"))
        return self._data_cache


def _collection_bucket(payment_status, balance, due_date, today):
    """Classify a customer for the field collection desk."""

    if payment_status == "PAID" or balance <= 0:
        return "COLLECTED"
    if due_date < today:
        return "OVERDUE"
    if due_date == today:
        return "TODAY"
    if due_date <= today + timedelta(days=7):
        return "NEXT_7_DAYS"
    return "UPCOMING"


class RentManagementAPIView(APIView):
    """Memory-bounded digital rent collection response."""

    permission_classes = [IsAuthenticated]
    ALLOWED_ROLES = {"ADMIN", "MANAGER", "OFFICE", "ENGINEER"}

    def get(self, request):
        if request.user.role not in self.ALLOWED_ROLES:
            return Response(
                {
                    "success": False,
                    "message": "Only Admin, Manager or Engineer can access rent management.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        customers = Customer.objects.filter(is_active=True)
        if request.user.role == "ENGINEER":
            engineer = getattr(request.user, "employee_profile", None)
            customers = (
                Customer.objects.none()
                if engineer is None
                else customers.filter(assigned_engineer=engineer)
            )

        customers = customers.order_by("name", "id")
        total_count = customers.count()
        today = timezone.localdate()
        current_month = today.replace(day=1)

        def customer_payload(customer):
            rent_record, _ = CustomerRentHistory.objects.select_related(
                "applied_offer"
            ).get_or_create(
                customer=customer,
                rent_month=current_month,
                defaults={
                    "expected_rent": customer.monthly_rent,
                    "paid_amount": 0,
                },
            )
            rent_record = _sync_current_rent_offer(customer, rent_record)

            expected = float(rent_record.expected_rent or 0)
            paid = float(rent_record.paid_amount or 0)
            balance = max(expected - paid, 0)
            if expected <= 0:
                payment_status = "NO_RENT"
            elif paid >= expected:
                payment_status = "PAID"
            elif paid > 0:
                payment_status = "PARTIAL"
            else:
                payment_status = "PENDING"

            installation_day = customer.installation_date.day if customer.installation_date else 1
            last_day = calendar.monthrange(today.year, today.month)[1]
            due_date = date(today.year, today.month, min(installation_day, last_day))
            penalty = rent_penalty(Decimal(str(balance)), due_date)
            collection_bucket = _collection_bucket(
                payment_status,
                balance,
                due_date,
                today,
            )
            days_until_due = (due_date - today).days

            history_data = []
            history = CustomerRentHistory.objects.filter(customer=customer).order_by(
                "-rent_month", "-id"
            )
            for item in history.iterator(chunk_size=24):
                item_expected = float(item.expected_rent or 0)
                item_paid = float(item.paid_amount or 0)
                item_balance = max(item_expected - item_paid, 0)
                if item_expected <= 0:
                    item_status = "NO_RENT"
                elif item_paid >= item_expected:
                    item_status = "PAID"
                elif item_paid > 0:
                    item_status = "PARTIAL"
                else:
                    item_status = "PENDING"
                history_data.append(
                    {
                        "id": item.id,
                        "rent_month": item.rent_month.isoformat() if item.rent_month else None,
                        "expected_rent": item_expected,
                        "paid_amount": item_paid,
                        "balance": item_balance,
                        "status": item_status,
                        "raw_value": item.raw_value,
                        "remarks": item.remarks,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    }
                )

            return {
                "customer": {
                    "id": customer.id,
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "phone": customer.phone,
                    "card_number": customer.card_number,
                    "old_card_number": customer.old_card_number,
                    "area": customer.area,
                    "address": customer.address,
                    "city": customer.city,
                    "latitude": str(customer.latitude) if customer.latitude is not None else None,
                    "longitude": str(customer.longitude) if customer.longitude is not None else None,
                },
                "current_rent": {
                    "rent_month": current_month.isoformat(),
                    "base_rent": float(rent_record.base_rent or expected),
                    "discount_amount": float(rent_record.discount_amount or 0),
                    "applied_offer": (
                        {
                            "id": rent_record.applied_offer_id,
                            "title": rent_record.applied_offer.title,
                            "promo_code": rent_record.applied_offer.promo_code,
                        }
                        if rent_record.applied_offer_id
                        else None
                    ),
                    "expected_rent": expected,
                    "paid_amount": paid,
                    "balance": balance,
                    "status": payment_status,
                    "due_date": due_date.isoformat(),
                    "collection_bucket": collection_bucket,
                    "days_until_due": days_until_due,
                    "grace_days": RENT_GRACE_DAYS,
                    "penalty_days": penalty["penalty_days"],
                    "penalty_amount": float(penalty["penalty_amount"]),
                    "total_due": float(Decimal(str(balance)) + penalty["penalty_amount"]),
                },
                "ro": {
                    "model": customer.ro_model,
                    "monthly_rent": float(customer.monthly_rent or 0),
                    "installation_charge": float(customer.installation_charge or 0),
                    "security_deposit": float(customer.security_deposit or 0),
                    "installation_date": (
                        customer.installation_date.isoformat()
                        if customer.installation_date
                        else None
                    ),
                },
                "history": history_data,
            }

        def stream_json():
            yield '{"success":true,"count":'
            yield str(total_count)
            yield ',"generated_for":"'
            yield today.isoformat()
            yield '","customers":['
            first = True
            for customer in customers.iterator(chunk_size=40):
                if not first:
                    yield ","
                first = False
                yield json.dumps(
                    customer_payload(customer),
                    cls=DjangoJSONEncoder,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            yield "]}"

        response = InspectableStreamingHttpResponse(
            stream_json(),
            content_type="application/json; charset=utf-8",
        )
        response["Cache-Control"] = "no-store"
        response["X-Accel-Buffering"] = "no"
        return response
