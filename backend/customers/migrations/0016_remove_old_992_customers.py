from django.db import migrations, transaction


BATCH = "EXCEL-2026-09-18-1059"


def _first_unique(qs):
    items = list(qs.order_by("id")[:2])
    return items[0] if len(items) == 1 else None


def remove_old_customers(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    CustomerRentHistory = apps.get_model("customers", "CustomerRentHistory")
    CustomerRentPayment = apps.get_model("customers", "CustomerRentPayment")
    CustomerLocationLog = apps.get_model("customers", "CustomerLocationLog")
    Job = apps.get_model("jobs", "Job")
    Complaint = apps.get_model("complaints", "Complaint")
    Installation = apps.get_model("installation", "Installation")
    Service = apps.get_model("service", "Service")
    ROAsset = apps.get_model("assets", "ROAsset")
    Referral = apps.get_model("referrals", "Referral")

    new_customers = Customer.objects.filter(import_batch=BATCH)

    def target_for(old):
        if old.old_card_number:
            candidates = new_customers.filter(old_card_number=old.old_card_number)
            one = _first_unique(candidates)
            if one is not None:
                return one

            if old.phone:
                one = _first_unique(candidates.filter(phone=old.phone))
                if one is not None:
                    return one

            if old.name:
                one = _first_unique(candidates.filter(name__iexact=old.name))
                if one is not None:
                    return one

        if old.phone:
            candidates = new_customers.filter(phone=old.phone)
            one = _first_unique(candidates)
            if one is not None:
                return one
            if old.name:
                one = _first_unique(candidates.filter(name__iexact=old.name))
                if one is not None:
                    return one

        if old.name:
            one = _first_unique(new_customers.filter(name__iexact=old.name))
            if one is not None:
                return one

        return None

    old_ids = list(
        Customer.objects
        .exclude(import_batch=BATCH)
        .order_by("id")
        .values_list("id", flat=True)
    )

    for old_id in old_ids:
        old = Customer.objects.get(pk=old_id)
        target = target_for(old)

        if target is not None:
            # Preserve customer-app linkage and useful operational coordinates.
            if old.user_id and not target.user_id:
                user_id = old.user_id
                old.user_id = None
                old.save(update_fields=["user"])
                target.user_id = user_id

            update_fields = []
            if target.user_id:
                update_fields.append("user")
            if target.assigned_engineer_id is None and old.assigned_engineer_id is not None:
                target.assigned_engineer_id = old.assigned_engineer_id
                update_fields.append("assigned_engineer")
            if target.latitude is None and old.latitude is not None:
                target.latitude = old.latitude
                update_fields.append("latitude")
            if target.longitude is None and old.longitude is not None:
                target.longitude = old.longitude
                update_fields.append("longitude")
            if update_fields:
                target.save(update_fields=sorted(set(update_fields)))

            # Preserve all non-Excel operational records by relinking them.
            Job.objects.filter(customer_id=old.id).update(customer_id=target.id)
            Complaint.objects.filter(customer_id=old.id).update(customer_id=target.id)
            Installation.objects.filter(customer_id=old.id).update(customer_id=target.id)
            Service.objects.filter(customer_id=old.id).update(customer_id=target.id)
            ROAsset.objects.filter(current_customer_id=old.id).update(current_customer_id=target.id)
            CustomerLocationLog.objects.filter(customer_id=old.id).update(customer_id=target.id)
            Referral.objects.filter(referred_customer_id=old.id).update(referred_customer_id=target.id)

            # Merge rent history month-by-month so app-entered history/payments survive.
            histories = list(
                CustomerRentHistory.objects
                .filter(customer_id=old.id)
                .order_by("id")
            )
            for history in histories:
                target_history = (
                    CustomerRentHistory.objects
                    .filter(customer_id=target.id, rent_month=history.rent_month)
                    .order_by("id")
                    .first()
                )
                if target_history is None:
                    history.customer_id = target.id
                    history.save(update_fields=["customer"])
                    CustomerRentPayment.objects.filter(
                        rent_history_id=history.id
                    ).update(customer_id=target.id)
                else:
                    CustomerRentPayment.objects.filter(
                        rent_history_id=history.id
                    ).update(
                        customer_id=target.id,
                        rent_history_id=target_history.id,
                    )
                    history.delete()

            CustomerRentPayment.objects.filter(customer_id=old.id).update(customer_id=target.id)

        else:
            # Records with no corresponding Excel customer are old test/legacy-only
            # entries. Remove their protected operational records first so the
            # old customer master can be deleted cleanly as requested.
            Referral.objects.filter(referred_customer_id=old.id).update(referred_customer_id=None)
            Service.objects.filter(customer_id=old.id).delete()
            Complaint.objects.filter(customer_id=old.id).delete()
            Installation.objects.filter(customer_id=old.id).delete()
            Job.objects.filter(customer_id=old.id).delete()
            ROAsset.objects.filter(current_customer_id=old.id).update(current_customer_id=None)

        old.delete()

    remaining_old = Customer.objects.exclude(import_batch=BATCH).count()
    batch_count = Customer.objects.filter(import_batch=BATCH).count()
    if remaining_old != 0:
        raise RuntimeError(f"Old customer cleanup incomplete: {remaining_old} old customers remain.")
    if batch_count != 1059:
        raise RuntimeError(f"Expected 1059 Excel customers after cleanup, found {batch_count}.")


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0015_import_exact_excel_20260918"),
        ("jobs", "0012_workscheduleoverride"),
        ("complaints", "0001_initial"),
        ("installation", "0004_installation_input_tds_installation_latitude_and_more"),
        ("service", "0001_initial"),
        ("assets", "0002_alter_roasset_status"),
        ("referrals", "0003_walletreward_app_referral_points"),
    ]

    operations = [
        migrations.RunPython(remove_old_customers, migrations.RunPython.noop),
    ]
