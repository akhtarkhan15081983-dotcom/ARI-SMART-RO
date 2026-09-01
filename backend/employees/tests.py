from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from .models import EmployeeProfile
from tenancy.models import Company, CompanyMembership, CompanySubscription, SubscriptionPlan
from django.utils import timezone
from datetime import timedelta


class EmployeeAPITests(TestCase):

    def setUp(self):

        self.client = APIClient()

        # ====================================================
        # ENGINEER USER
        # ====================================================

        self.engineer_user = User.objects.create_user(
            phone="9200000001",
            password="Test@123",
            first_name="Test",
            last_name="Engineer",
            email="engineer@test.com",
            role="ENGINEER",
            is_verified=True,
        )

        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="EMP-TEST-0001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            city="Delhi",
            state="Delhi",
            pincode="110001",
            address="Engineer Address",
            emergency_name="Emergency Person",
            emergency_contact="9200000099",
            is_active=True,
        )

        # ====================================================
        # OFFICE USER
        # ====================================================

        self.office_user = User.objects.create_user(
            phone="9200000002",
            password="Test@123",
            first_name="Office",
            last_name="Staff",
            email="office@test.com",
            role="OFFICE",
            is_verified=True,
        )

        self.office = EmployeeProfile.objects.create(
            user=self.office_user,
            employee_id="EMP-TEST-0002",
            gender="FEMALE",
            joining_date=date(2026, 1, 2),
            designation="OFFICE",
            salary=Decimal("22000.00"),
            city="Delhi",
            state="Delhi",
            pincode="110002",
            is_active=True,
        )

        # ====================================================
        # MANAGER USER
        # ====================================================

        self.manager_user = User.objects.create_user(
            phone="9200000003",
            password="Test@123",
            first_name="Test",
            last_name="Manager",
            email="manager@test.com",
            role="MANAGER",
            is_verified=True,
        )

        self.manager = EmployeeProfile.objects.create(
            user=self.manager_user,
            employee_id="EMP-TEST-0003",
            gender="MALE",
            joining_date=date(2026, 1, 3),
            designation="MANAGER",
            salary=Decimal("40000.00"),
            city="Delhi",
            state="Delhi",
            pincode="110003",
            is_active=True,
        )

    # ========================================================
    # HELPER
    # ========================================================

    def authenticate_engineer(self):

        self.client.force_authenticate(
            user=self.engineer_user
        )

    # ========================================================
    # PROFILE GET
    # ========================================================

    def test_employee_can_view_own_profile(self):

        self.authenticate_engineer()

        response = self.client.get(
            "/api/employees/profile/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["employee_id"],
            self.engineer.employee_id,
        )

        self.assertEqual(
            response.data["first_name"],
            "Test",
        )

        self.assertEqual(
            response.data["last_name"],
            "Engineer",
        )

        self.assertEqual(
            response.data["phone"],
            "9200000001",
        )

        self.assertEqual(
            response.data["email"],
            "engineer@test.com",
        )

        self.assertEqual(
            response.data["role"],
            "ENGINEER",
        )

        self.assertEqual(
            response.data["designation"],
            "ENGINEER",
        )

    # ========================================================
    # PROFILE AUTHENTICATION
    # ========================================================

    def test_profile_requires_authentication(self):

        response = self.client.get(
            "/api/employees/profile/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    # ========================================================
    # PROFILE NOT FOUND
    # ========================================================

    def test_user_without_employee_profile_gets_404(self):

        user = User.objects.create_user(
            phone="9200000010",
            password="Test@123",
            first_name="No",
            last_name="Employee",
            role="ENGINEER",
            is_verified=True,
        )

        self.client.force_authenticate(
            user=user
        )

        response = self.client.get(
            "/api/employees/profile/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertEqual(
            response.data["error"],
            "Employee profile not found.",
        )

    # ========================================================
    # PROFILE UPDATE
    # ========================================================

    def test_employee_can_update_profile(self):

        self.authenticate_engineer()

        response = self.client.put(
            "/api/employees/profile/",
            {
                "first_name": "Updated",
                "last_name": "Engineer",
                "email": "updated@test.com",
                "address": "New Address",
                "city": "Noida",
                "state": "Uttar Pradesh",
                "pincode": "201301",
                "emergency_name": "New Emergency",
                "emergency_contact": "9211111111",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.engineer_user.refresh_from_db()
        self.engineer.refresh_from_db()

        self.assertEqual(
            self.engineer_user.first_name,
            "Updated",
        )

        self.assertEqual(
            self.engineer_user.last_name,
            "Engineer",
        )

        self.assertEqual(
            self.engineer_user.email,
            "updated@test.com",
        )

        self.assertEqual(
            self.engineer.address,
            "New Address",
        )

        self.assertEqual(
            self.engineer.city,
            "Noida",
        )

        self.assertEqual(
            self.engineer.state,
            "Uttar Pradesh",
        )

        self.assertEqual(
            self.engineer.pincode,
            "201301",
        )

    # ========================================================
    # PROFILE PARTIAL UPDATE
    # ========================================================

    def test_employee_can_partially_update_profile(self):

        self.authenticate_engineer()

        response = self.client.put(
            "/api/employees/profile/",
            {
                "city": "Gurgaon",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.engineer.refresh_from_db()

        self.assertEqual(
            self.engineer.city,
            "Gurgaon",
        )

        self.assertEqual(
            self.engineer.state,
            "Delhi",
        )

    # ========================================================
    # PROTECTED EMPLOYEE FIELDS
    # ========================================================

    def test_profile_update_cannot_change_employee_id(
        self
    ):

        self.authenticate_engineer()

        original_id = self.engineer.employee_id

        response = self.client.put(
            "/api/employees/profile/",
            {
                "employee_id": "HACKED-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.engineer.refresh_from_db()

        self.assertEqual(
            self.engineer.employee_id,
            original_id,
        )

    def test_profile_update_cannot_change_salary(
        self
    ):

        self.authenticate_engineer()

        original_salary = self.engineer.salary

        response = self.client.put(
            "/api/employees/profile/",
            {
                "salary": "999999",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.engineer.refresh_from_db()

        self.assertEqual(
            self.engineer.salary,
            original_salary,
        )

    def test_profile_update_cannot_change_designation(
        self
    ):

        self.authenticate_engineer()

        response = self.client.put(
            "/api/employees/profile/",
            {
                "designation": "MANAGER",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.engineer.refresh_from_db()

        self.assertEqual(
            self.engineer.designation,
            "ENGINEER",
        )

    # ========================================================
    # LIVE LOCATION
    # ========================================================

    def test_engineer_can_update_live_location(self):

        self.authenticate_engineer()

        response = self.client.post(
            "/api/employees/live-location/",
            {
                "live_latitude": "28.6139000",
                "live_longitude": "77.2090000",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["message"],
            "Location Updated Successfully",
        )

        self.engineer.refresh_from_db()

        self.assertEqual(
            self.engineer.last_latitude,
            Decimal("28.6139000"),
        )

        self.assertEqual(
            self.engineer.last_longitude,
            Decimal("77.2090000"),
        )

        self.assertTrue(
            self.engineer.is_online
        )

        self.assertIsNotNone(
            self.engineer.last_location_updated
        )

    # ========================================================
    # LIVE LOCATION AUTH
    # ========================================================

    def test_live_location_requires_authentication(self):

        response = self.client.post(
            "/api/employees/live-location/",
            {
                "live_latitude": "28.6139000",
                "live_longitude": "77.2090000",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    # ========================================================
    # LIVE LOCATION WITHOUT PROFILE
    # ========================================================

    def test_live_location_without_employee_profile(
        self
    ):

        user = User.objects.create_user(
            phone="9200000020",
            password="Test@123",
            first_name="No",
            last_name="Profile",
            role="ENGINEER",
            is_verified=True,
        )

        self.client.force_authenticate(
            user=user
        )

        response = self.client.post(
            "/api/employees/live-location/",
            {
                "live_latitude": "28.6139000",
                "live_longitude": "77.2090000",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    # ========================================================
    # INVALID LOCATION
    # ========================================================

    def test_invalid_latitude_is_rejected(self):

        self.authenticate_engineer()

        response = self.client.post(
            "/api/employees/live-location/",
            {
                "live_latitude": "999.0000000",
                "live_longitude": "77.2090000",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_invalid_longitude_is_rejected(self):

        self.authenticate_engineer()

        response = self.client.post(
            "/api/employees/live-location/",
            {
                "live_latitude": "28.6139000",
                "live_longitude": "999.0000000",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    # ========================================================
    # LIVE MAP
    # ========================================================

    def test_live_map_returns_engineers_with_location(
        self
    ):

        self.engineer.last_latitude = Decimal(
            "28.6139000"
        )

        self.engineer.last_longitude = Decimal(
            "77.2090000"
        )

        self.engineer.is_online = True

        self.engineer.save()

        self.client.force_authenticate(
            user=self.manager_user
        )

        response = self.client.get(
            "/api/employees/live-map/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        engineer_data = response.data[0]

        self.assertEqual(
            engineer_data["id"],
            self.engineer.id,
        )

        self.assertEqual(
            engineer_data["employee_id"],
            self.engineer.employee_id,
        )

        self.assertEqual(
            engineer_data["name"],
            "Test Engineer",
        )

        self.assertEqual(
            engineer_data["phone"],
            "9200000001",
        )

        self.assertEqual(
            str(engineer_data["latitude"]),
            "28.6139000",
        )

        self.assertEqual(
            str(engineer_data["longitude"]),
            "77.2090000",
        )

        self.assertTrue(
            engineer_data["online"]
        )

    # ========================================================
    # LIVE MAP EXCLUDES ENGINEERS WITHOUT LOCATION
    # ========================================================

    def test_live_map_excludes_engineer_without_location(
        self
    ):

        self.client.force_authenticate(
            user=self.manager_user
        )

        response = self.client.get(
            "/api/employees/live-map/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            0,
        )

    # ========================================================
    # LIVE MAP EXCLUDES INACTIVE ENGINEER
    # ========================================================

    def test_live_map_excludes_inactive_engineer(self):

        self.engineer.last_latitude = Decimal(
            "28.6139000"
        )

        self.engineer.last_longitude = Decimal(
            "77.2090000"
        )

        self.engineer.is_active = False

        self.engineer.save()

        self.client.force_authenticate(
            user=self.manager_user
        )

        response = self.client.get(
            "/api/employees/live-map/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            0,
        )

    # ========================================================
    # ENGINEER LIST
    # ========================================================

    def test_engineer_list_returns_active_engineers(
        self
    ):

        self.client.force_authenticate(
            user=self.manager_user
        )

        response = self.client.get(
            "/api/employees/engineers/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        engineer_data = response.data[0]

        self.assertEqual(
            engineer_data["id"],
            self.engineer.id,
        )

        self.assertEqual(
            engineer_data["employee_id"],
            self.engineer.employee_id,
        )

        self.assertEqual(
            engineer_data["name"],
            "Test Engineer",
        )

        self.assertEqual(
            engineer_data["phone"],
            "9200000001",
        )

    # ========================================================
    # ENGINEER LIST EXCLUDES INACTIVE
    # ========================================================

    def test_engineer_list_excludes_inactive_engineers(
        self
    ):

        self.engineer.is_active = False

        self.engineer.save(
            update_fields=[
                "is_active"
            ]
        )

        self.client.force_authenticate(
            user=self.manager_user
        )

        response = self.client.get(
            "/api/employees/engineers/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            0,
        )

    # ========================================================
    # ASSIGNMENT EMPLOYEE LIST
    # ========================================================

    def test_assignment_employee_list_returns_engineer_and_office(
        self
    ):

        self.client.force_authenticate(
            user=self.manager_user
        )

        response = self.client.get(
            "/api/employees/assignment-employees/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            2,
        )

        designations = {
            item["designation"]
            for item in response.data
        }

        self.assertIn(
            "ENGINEER",
            designations,
        )

        self.assertIn(
            "OFFICE",
            designations,
        )

    # ========================================================
    # ASSIGNMENT LIST EXCLUDES MANAGER
    # ========================================================

    def test_assignment_employee_list_excludes_manager(
        self
    ):

        self.client.force_authenticate(
            user=self.manager_user
        )

        response = self.client.get(
            "/api/employees/assignment-employees/"
        )

        designations = [
            item["designation"]
            for item in response.data
        ]

        self.assertNotIn(
            "MANAGER",
            designations,
        )

    # ========================================================
    # ASSIGNMENT LIST EXCLUDES INACTIVE EMPLOYEE
    # ========================================================

    def test_assignment_employee_list_excludes_inactive_employee(
        self
    ):

        self.office.is_active = False

        self.office.save(
            update_fields=[
                "is_active"
            ]
        )

        self.client.force_authenticate(
            user=self.manager_user
        )

        response = self.client.get(
            "/api/employees/assignment-employees/"
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["designation"],
            "ENGINEER",
        )

    # ========================================================
    # EMPLOYEE ID GENERATION
    # ========================================================

    def test_employee_id_is_generated_when_missing(self):

        user = User.objects.create_user(
            phone="9200000030",
            password="Test@123",
            first_name="Generated",
            last_name="Employee",
            role="ENGINEER",
            is_verified=True,
        )

        employee = EmployeeProfile.objects.create(
            user=user,
            gender="MALE",
            joining_date=date.today(),
            designation="ENGINEER",
        )

        self.assertTrue(
            employee.employee_id
        )

        self.assertTrue(
            employee.employee_id.startswith("EMP-")
        )

        self.assertRegex(
            employee.employee_id,
            r"^EMP-\d{4}-\d{6}$",
        )

    # ========================================================
    # EMPLOYEE STRING
    # ========================================================

    def test_employee_string_representation(self):

        expected = (
            f"{self.engineer.employee_id} - "
            f"{self.engineer_user.get_full_name()}"
        )

        self.assertEqual(
            str(self.engineer),
            expected,
        )


class TenantEmployeeManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            phone="9300000001", password="AdminStrong@123", role="ADMIN",
            first_name="Bhawna", is_verified=True,
        )
        self.company = Company.objects.create(
            name="Bhawna RO", slug="bhawna-ro-employees", phone="9300000001"
        )
        CompanyMembership.objects.create(company=self.company, user=self.admin_user, role="OWNER")
        plan = SubscriptionPlan.objects.get(code="starter")
        CompanySubscription.objects.create(
            company=self.company, plan=plan, status="ACTIVE",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self.client.force_authenticate(self.admin_user)

    def test_company_admin_can_create_and_only_list_own_employee(self):
        response = self.client.post(
            "/api/employees/manage/",
            {
                "first_name": "Ravi", "last_name": "Engineer",
                "phone": "9300000002", "email": "ravi@example.com",
                "designation": "ENGINEER", "gender": "MALE",
                "joining_date": "2026-09-01", "salary": "24000",
                "initial_password": "EmployeeStrong@123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        employee = EmployeeProfile.objects.get(user__phone="9300000002")
        self.assertEqual(employee.company, self.company)
        self.assertTrue(CompanyMembership.objects.filter(company=self.company, user=employee.user).exists())
        listed = self.client.get("/api/employees/manage/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([row["phone"] for row in listed.data["employees"]], ["9300000002"])
