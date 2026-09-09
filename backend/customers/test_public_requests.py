from django.urls import reverse
from rest_framework.test import APITestCase

from products.models import ProductCategory, ROModel
from .models import PublicCustomerRequest


class PublicCustomerRequestTests(APITestCase):
    def setUp(self):
        category = ProductCategory.objects.create(name="Guest Checkout")
        self.product = ROModel.objects.create(
            category=category,
            model_name="Guest RO",
            capacity="12 L",
            business_type="SALE",
            selling_price="8999.00",
            stock_quantity=3,
            is_active=True,
        )
        self.url = reverse("public-customer-request")
        self.contact = {
            "customer_name": "Guest Customer",
            "phone": "9876543210",
            "address": "12 Test Road",
            "city": "Agra",
            "state": "Uttar Pradesh",
            "pincode": "282001",
        }

    def test_guest_can_place_product_order_without_login(self):
        response = self.client.post(
            self.url,
            {
                **self.contact,
                "request_type": "PURCHASE",
                "product": self.product.id,
                "quantity": 2,
                "payment_method": "COD",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        order = PublicCustomerRequest.objects.get()
        self.assertEqual(order.total_amount, 17998)
        self.assertEqual(order.status, "NEW")
        self.assertTrue(response.data["request_number"].startswith("ARI-"))

    def test_guest_can_submit_service_amc_and_referral_requests(self):
        for request_type in ("SERVICE", "AMC", "REFERRAL"):
            response = self.client.post(
                self.url,
                {
                    **self.contact,
                    "request_type": request_type,
                    "plan_name": f"{request_type} plan",
                },
                format="json",
            )
            self.assertEqual(response.status_code, 201)
        self.assertEqual(PublicCustomerRequest.objects.count(), 3)

    def test_purchase_rejects_quantity_above_stock(self):
        response = self.client.post(
            self.url,
            {
                **self.contact,
                "request_type": "PURCHASE",
                "product": self.product.id,
                "quantity": 4,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
