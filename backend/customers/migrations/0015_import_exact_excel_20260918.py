import gzip
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.db import migrations


BATCH = "EXCEL-2026-09-18-1059"
EXPECTED = 1059
KEY_ENV = "ARI_EXCEL_IMPORT_20260918_KEY"


def _clean(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _decimal(value):
    text = _clean(value)
    if not text:
        return Decimal("0")
    try:
        return Decimal(text.replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _excel_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
        except Exception:
            return None
    text = _clean(value)
    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%A, %B %d, %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _load_payload():
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise RuntimeError("Exact Excel import decryption key is missing from Render environment.")

    encrypted_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "customer_import_20260918.enc"
    )
    if not encrypted_path.exists():
        raise RuntimeError("Encrypted Excel import payload file is missing.")

    encrypted = encrypted_path.read_bytes().strip()
    try:
        compressed = Fernet(key.encode("ascii")).decrypt(encrypted)
        raw = gzip.decompress(compressed)
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Unable to decrypt/read exact Excel import payload.") from exc

    if payload.get("batch") != BATCH or int(payload.get("expected_records") or 0) != EXPECTED:
        raise RuntimeError("Exact Excel import payload metadata does not match the expected batch.")
    return payload


def import_exact_excel(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    CustomerRentHistory = apps.get_model("customers", "CustomerRentHistory")
    EmployeeProfile = apps.get_model("employees", "EmployeeProfile")

    if Customer.objects.filter(import_batch=BATCH).count() >= EXPECTED:
        return

    payload = _load_payload()
    records = payload.get("records") or []
    if len(records) != EXPECTED:
        raise RuntimeError(f"Expected {EXPECTED} Excel customer records, received {len(records)}.")

    max_number = 0
    for customer_id in Customer.objects.exclude(customer_id="").values_list("customer_id", flat=True):
        try:
            max_number = max(max_number, int(str(customer_id).split("-")[-1]))
        except (TypeError, ValueError):
            continue
    next_number = max_number + 1

    employee_map = {}
    for profile in EmployeeProfile.objects.select_related("user").all():
        user = profile.user
        full_name = " ".join(
            part for part in [getattr(user, "first_name", ""), getattr(user, "last_name", "")] if part
        ).strip().upper()
        if "RAJKUMAR" in full_name or "RAJ KUMAR" in full_name:
            employee_map["RAJKUMAR"] = profile
        if "HASNAIN" in full_name or "HUSNAIN" in full_name:
            employee_map["HASNAIN"] = profile
        if "RUPESH" in full_name:
            employee_map["RUPESH"] = profile
        if full_name.startswith("RAMA"):
            employee_map["RAMA"] = profile

    headers = payload.get("sheet1_headers") or []
    payment_headers = headers[20:]
    pending_history = []

    for item in records:
        sheet = item.get("source_sheet") or ""
        source_row = int(item.get("source_row") or 0)
        row = item.get("raw_row") or []

        if sheet == "Sheet1":
            old_card = _clean(row[1] if len(row) > 1 else None)
            name = _clean(row[2] if len(row) > 2 else None)
            employee = _clean(row[6] if len(row) > 6 else None)
            reference = _clean(row[7] if len(row) > 7 else None)
            installer = _clean(row[9] if len(row) > 9 else None)
            remarks = _clean(row[10] if len(row) > 10 else None)
            mh = _clean(row[11] if len(row) > 11 else None)
            raw_phone = _clean(row[12] if len(row) > 12 else None)
            area = _clean(row[13] if len(row) > 13 else None)
            address = _clean(row[14] if len(row) > 14 else None)
            install_value = row[16] if len(row) > 16 else None
            installation_charge = _decimal(row[18] if len(row) > 18 else None)
            monthly_rent = _decimal(row[19] if len(row) > 19 else None)
            payment_values = row[20:]
        else:
            old_card = _clean(row[0] if len(row) > 0 else None)
            name = _clean(row[1] if len(row) > 1 else None)
            employee = _clean(row[5] if len(row) > 5 else None)
            reference = _clean(row[6] if len(row) > 6 else None)
            installer = _clean(row[8] if len(row) > 8 else None)
            remarks = _clean(row[9] if len(row) > 9 else None)
            mh = _clean(row[10] if len(row) > 10 else None)
            raw_phone = _clean(row[11] if len(row) > 11 else None)
            area = _clean(row[12] if len(row) > 12 else None)
            address = _clean(row[13] if len(row) > 13 else None)
            install_value = row[15] if len(row) > 15 else None
            installation_charge = _decimal(row[17] if len(row) > 17 else None)
            monthly_rent = _decimal(row[18] if len(row) > 18 else None)
            payment_values = row[19:]

        if not name:
            raise RuntimeError(f"Source {sheet} row {source_row} unexpectedly has no customer name.")

        while Customer.objects.filter(customer_id=f"CUS-2026-{next_number:06d}").exists():
            next_number += 1

        normalized_employee = employee.upper().replace(" ", "")
        assigned = None
        if normalized_employee == "RAJKUMAR":
            assigned = employee_map.get("RAJKUMAR")
        elif normalized_employee in {"HASNAIN", "HUSNAIN"}:
            assigned = employee_map.get("HASNAIN")
        elif normalized_employee == "RUPESH":
            assigned = employee_map.get("RUPESH")
        elif normalized_employee == "RAMA":
            assigned = employee_map.get("RAMA")

        customer = Customer.objects.create(
            customer_id=f"CUS-2026-{next_number:06d}",
            card_number=f"ARI-2026-{next_number:06d}",
            old_card_number=old_card,
            name=name,
            phone=raw_phone[:30],
            alternate_phone="",
            email="",
            gender="",
            address=address,
            area=area,
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="UNKNOWN",
            installation_charge=installation_charge,
            monthly_rent=monthly_rent,
            security_deposit=Decimal("0"),
            installation_date=_excel_date(install_value),
            assigned_engineer=assigned,
            is_active=True,
            import_batch=BATCH,
            legacy_source_sheet=sheet,
            legacy_source_row=source_row or None,
            legacy_raw_phone=raw_phone[:80],
            legacy_employee=employee[:120],
            legacy_reference=reference[:150],
            legacy_installer=installer[:120],
            legacy_remarks=remarks,
            legacy_mh=mh[:20],
            legacy_excel_payload={"row": row},
        )
        next_number += 1

        seen_dates = set()
        for idx, raw_value in enumerate(payment_values):
            if raw_value in (None, ""):
                continue
            if idx >= len(payment_headers):
                break
            rent_month = _excel_date(payment_headers[idx])
            if rent_month is None or rent_month in seen_dates:
                continue
            seen_dates.add(rent_month)
            pending_history.append(
                CustomerRentHistory(
                    customer=customer,
                    rent_month=rent_month,
                    expected_rent=monthly_rent,
                    paid_amount=_decimal(raw_value),
                    raw_value=_clean(raw_value)[:100],
                    remarks="Imported from CUSTUMER DATA NEW.xlsx",
                )
            )
            if len(pending_history) >= 4000:
                CustomerRentHistory.objects.bulk_create(pending_history, batch_size=1000)
                pending_history.clear()

    if pending_history:
        CustomerRentHistory.objects.bulk_create(pending_history, batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [("customers", "0014_exact_excel_fields")]

    operations = [
        migrations.RunPython(import_exact_excel, migrations.RunPython.noop),
    ]
