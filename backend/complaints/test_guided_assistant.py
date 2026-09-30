from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from assets.models import ROAsset
from customers.models import Customer
from products.models import ProductCategory, ROModel
from tenancy.models import Company

from .guidance import SYMPTOM_GUIDANCE, complaint_guidance
from .models import Complaint


class ComplaintGuidanceSafetyTests(SimpleTestCase):
    def test_required_customer_symptoms_are_supported(self):
        expected = {
            "WATER_NOT_COMING",
            "SLOW_FLOW",
            "BAD_TASTE",
            "BAD_SMELL",
            "HIGH_TDS",
            "LEAKAGE",
            "UNUSUAL_SOUND",
            "PUMP_NOT_WORKING",
            "RO_NOT_STARTING",
            "TANK_NOT_FILLING",
            "TANK_OVERFLOWING",
            "CONTINUOUS_REJECT_WATER",
            "SERVICE_DUE_ALERT",
            "OTHER",
        }
        self.assertEqual(set(SYMPTOM_GUIDANCE), expected)

    def test_every_guided_symptom_maps_to_supported_complaint_type(self):
        allowed = {value for value, _ in Complaint.COMPLAINT_TYPE_CHOICES}
        mapped = {value["complaint_type"] for value in SYMPTOM_GUIDANCE.values()}
        self.assertTrue(mapped.issubset(allowed), mapped - allowed)

    def test_leakage_is_high_priority_and_never_gives_internal_repair_steps(self):
        guidance = complaint_guidance("LEAKAGE")
        self.assertEqual(guidance["priority"], "EMERGENCY")
        joined = " ".join(guidance["checks"]).lower()
        self.assertIn("do not open", joined)
        self.assertNotIn("bypass the", joined)
        self.assertNotIn("touch exposed wires", joined)
        self.assertNotIn("repair the pump", joined)

    def test_unknown_symptom_falls_back_to_safe_other_guidance(self):
        guidance = complaint_guidance("something-new")
        self.assertEqual(guidance["symptom"], "OTHER")
        self.assertIn("Raise Complaint", guidance["cta"])


class ComplaintAssistantIsolationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(
            name="Complaint Assistant Company",
            slug="complaint-assistant-company",
            phone="9000088001",
        )
        self.other_company = Company.objects.create(
            name="Complaint Assistant Other",
            slug="complaint-assistant-other",
            phone="9000088002",
        )
        self.user = User.objects.create_user(
            phone="8111188001",
            password="TestPassword123!",
            role="CUSTOMER",
            is_verified=True,
            is_active=True,
        )
        self.other_user = User.objects.create_user(
            phone="8111188002",
            password="TestPassword123!",
            role="CUSTOMER",
            is_verified=True,
            is_active=True,
        )
        self.customer = Customer.objects.create(
            company=self.company,
            user=self.user,
            name="Assistant Customer",
            phone=self.user.phone,
            address="Own Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Assistant RO",
        )
        self.other_customer = Customer.objects.create(
            company=self.other_company,
            user=self.other_user,
            name="Other Customer",
            phone=self.other_user.phone,
            address="Other Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Assistant RO",
        )
        category = ProductCategory.objects.create(name="Complaint Assistant Category")
        model = ROModel.objects.create(
            category=category,
            model_name="Assistant RO",
            capacity="12 LPH",
            business_type="RENT",
            monthly_rent=Decimal("900.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("0.00"),
            selling_price=Decimal("10000.00"),
            warranty_months=12,
        )
        self.asset = ROAsset.objects.create(
            ro_model=model,
            serial_number="ASSIST-ASSET-001",
            status="INSTALLED",
            current_customer=self.customer,
        )
        self.other_asset = ROAsset.objects.create(
            ro_model=model,
            serial_number="ASSIST-ASSET-002",
            status="INSTALLED",
            current_customer=self.other_customer,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_customer_can_prepare_context_only_for_own_asset(self):
        own = self.client.get(
            reverse("complaint-assistant"),
            {"symptom": "LEAKAGE", "asset_id": self.asset.asset_id},
        )
        self.assertEqual(own.status_code, 200)
        self.assertEqual(
            own.data["complaint_context"]["customer_reference"],
            self.customer.customer_id,
        )
        self.assertEqual(
            own.data["complaint_context"]["ro_asset_id"],
            self.asset.asset_id,
        )
        self.assertNotIn("phone", own.data["complaint_context"])
        self.assertNotIn("address", own.data["complaint_context"])

        other = self.client.get(
            reverse("complaint-assistant"),
            {"symptom": "LEAKAGE", "asset_id": self.other_asset.asset_id},
        )
        self.assertEqual(other.status_code, 404)

    def test_guided_leakage_raise_preserves_emergency_priority(self):
        response = self.client.post(
            reverse("complaint-assistant"),
            {"symptom": "LEAKAGE", "description": "Water is leaking outside."},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        complaint = Complaint.objects.get(pk=response.data["complaint"]["id"])
        self.assertEqual(complaint.customer, self.customer)
        self.assertEqual(complaint.priority, "EMERGENCY")
        self.assertEqual(complaint.complaint_type, "WATER_LEAKAGE")
        self.assertIn("Guided Complaint Context", complaint.description)
        self.assertIn(self.customer.customer_id, complaint.description)
        self.assertNotIn(self.customer.phone, complaint.description)
