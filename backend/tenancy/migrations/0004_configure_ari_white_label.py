from django.db import migrations


def configure_ari(apps, schema_editor):
    Company = apps.get_model("tenancy", "Company")
    Company.objects.filter(slug="ari-smart-ro").update(
        app_display_name="ARI SMART RO",
        tagline="Pure water. Smart living.",
        welcome_message="Shop water purifiers and manage your complete RO journey in one secure app.",
        show_public_shop=True,
        enabled_modules=["SHOP", "SERVICE", "RENT", "COMPLAINT", "REFERRAL", "ACCOUNT"],
    )


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0003_company_app_display_name_company_enabled_modules_and_more")]
    operations = [migrations.RunPython(configure_ari, migrations.RunPython.noop)]
