from django.test import TestCase
from django.core.management import call_command
from io import StringIO

from accounts.models import User
from customers.models import Customer
from products.models import ProductCategory, ROModel
from tenancy.models import Company


class MaxProTestCustomerSeedCommandTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="ARI Max-Pro Test Workspace",
            slug="ari-max-pro-test",
            phone="9000000000",
            city="Test City",
            state="Test State",
            pincode="000000",
            show_public_shop=True,
        )
        category = ProductCategory.objects.create(name="Domestic RO Test")
        self.sale_ro = ROModel.objects.create(
            category=category,
            model_name="ARI Test Sale RO",
            capacity="12 LPH",
            business_type="SALE",
            available_for_sale=True,
            available_for_rent=False,
            selling_price="12999.00",
            stock_quantity=5,
            installation_charge="600.00",
        )
        self.rent_ro = ROModel.objects.create(
            category=category,
            model_name="ARI Test Rental RO",
            capacity="12 LPH",
            business_type="RENT",
            available_for_sale=True,
            available_for_rent=True,
            selling_price="14999.00",
            monthly_rent="900.00",
            security_deposit="2400.00",
            installation_charge="600.00",
            stock_quantity=4,
        )

    def test_dry_run_changes_nothing(self):
        output = StringIO()
        call_command(
            "seed_max_pro_test_customers",
            company=self.company.slug,
            count=8,
            stdout=output,
        )
        self.assertIn("DRY RUN ONLY", output.getvalue())
        self.assertEqual(User.objects.filter(role="CUSTOMER").count(), 0)
        self.assertEqual(Customer.objects.count(), 0)

    def test_apply_creates_repeatable_verified_customers_linked_to_shop_ro(self):
        password = "MaxPro-Test@2026"
        output = StringIO()
        call_command(
            "seed_max_pro_test_customers",
            company=self.company.slug,
            count=8,
            password=password,
            apply=True,
            stdout=output,
        )
        self.assertEqual(User.objects.filter(role="CUSTOMER").count(), 8)
        self.assertEqual(Customer.objects.filter(company=self.company).count(), 8)
        self.assertEqual(Customer.objects.filter(import_batch="MAX_PRO_CERTIFICATION").count(), 8)
        first = User.objects.get(phone="9199001001")
        self.assertTrue(first.is_verified)
        self.assertTrue(first.check_password(password))
        customer = first.customer_profile
        self.assertEqual(customer.company, self.company)
        self.assertIn(customer.ro_model, {self.sale_ro.model_name, self.rent_ro.model_name})

        # Re-running updates the same fixtures instead of creating duplicates.
        call_command(
            "seed_max_pro_test_customers",
            company=self.company.slug,
            count=8,
            password=password,
            apply=True,
            stdout=StringIO(),
        )
        self.assertEqual(User.objects.filter(role="CUSTOMER").count(), 8)
        self.assertEqual(Customer.objects.filter(company=self.company).count(), 8)
