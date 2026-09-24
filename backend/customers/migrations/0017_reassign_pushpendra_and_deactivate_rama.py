from django.db import migrations


CUSTOMER_ID = "CUS-2026-001803"
RAJKUMAR_EMPLOYEE_ID = "hus2026"
RAMA_EMPLOYEE_ID = "Rama2026"


def apply_change(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    EmployeeProfile = apps.get_model("employees", "EmployeeProfile")

    rajkumar = EmployeeProfile.objects.select_related("user").get(
        employee_id=RAJKUMAR_EMPLOYEE_ID
    )
    rama = EmployeeProfile.objects.select_related("user").get(
        employee_id=RAMA_EMPLOYEE_ID
    )
    customer = Customer.objects.get(customer_id=CUSTOMER_ID)

    customer.assigned_engineer_id = rajkumar.id
    customer.save(update_fields=["assigned_engineer"])

    rama.is_active = False
    rama.save(update_fields=["is_active"])

    rama.user.is_active = False
    rama.user.save(update_fields=["is_active"])


def reverse_change(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    EmployeeProfile = apps.get_model("employees", "EmployeeProfile")

    rama = EmployeeProfile.objects.select_related("user").get(
        employee_id=RAMA_EMPLOYEE_ID
    )
    customer = Customer.objects.get(customer_id=CUSTOMER_ID)

    customer.assigned_engineer_id = rama.id
    customer.save(update_fields=["assigned_engineer"])

    rama.is_active = True
    rama.save(update_fields=["is_active"])

    rama.user.is_active = True
    rama.user.save(update_fields=["is_active"])


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0016_remove_old_992_customers"),
    ]

    operations = [
        migrations.RunPython(apply_change, reverse_change),
    ]
