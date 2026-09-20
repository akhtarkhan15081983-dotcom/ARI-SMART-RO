from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from accounts.models import CustomerEngagement
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

    def test_checkout_rejects_an_option_disabled_for_product(self):
        self.product.available_for_sale = False
        self.product.available_for_rent = True
        self.product.monthly_rent = "499.00"
        self.product.save(
            update_fields=["available_for_sale", "available_for_rent", "monthly_rent"]
        )
        sale_response = self.client.post(
            self.url,
            {**self.contact, "request_type": "PURCHASE", "product": self.product.id},
            format="json",
        )
        rent_response = self.client.post(
            self.url,
            {**self.contact, "request_type": "RENTAL", "product": self.product.id},
            format="json",
        )
        self.assertEqual(sale_response.status_code, 400)
        self.assertEqual(rent_response.status_code, 201)


    def test_purchase_promo_code_reduces_total(self):
        CustomerEngagement.objects.create(
            kind="OFFER",
            audience="ALL",
            title="Festival Purchase Offer",
            message="₹1000 off",
            discount_type="FIXED",
            discount_value=Decimal("1000.00"),
            promo_code="FEST1000",
            offer_scope="PURCHASE",
            auto_apply=False,
            valid_from=timezone.now(),
            priority=90,
            action="SHOP",
        )
        response = self.client.post(
            self.url,
            {
                **self.contact,
                "request_type": "PURCHASE",
                "product": self.product.id,
                "quantity": 1,
                "offer_code": "FEST1000",
                "payment_method": "COD",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        order = PublicCustomerRequest.objects.get()
        self.assertEqual(order.base_amount, Decimal("8999.00"))
        self.assertEqual(order.discount_amount, Decimal("1000.00"))
        self.assertEqual(order.total_amount, Decimal("7999.00"))
        self.assertEqual(order.applied_offer.title, "Festival Purchase Offer")
        self.assertEqual(response.data["total_amount"], "7999.00")

    def test_invalid_purchase_promo_code_is_rejected(self):
        response = self.client.post(
            self.url,
            {
                **self.contact,
                "request_type": "PURCHASE",
                "product": self.product.id,
                "offer_code": "INVALID",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
