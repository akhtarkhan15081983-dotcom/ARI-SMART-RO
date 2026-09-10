from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import ProductCategory, ROModel


class CustomerShopCatalogTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            phone='9999999999',
            password='test-pass-123',
        )
        self.client.force_authenticate(self.user)
        self.category = ProductCategory.objects.create(name='Domestic RO')

    def _model(
        self,
        name,
        business_type='SALE',
        price=10000,
        rent=0,
        active=True,
        for_sale=None,
        for_rent=None,
    ):
        return ROModel.objects.create(
            category=self.category,
            model_name=name,
            capacity='12 LPH',
            business_type=business_type,
            selling_price=price,
            monthly_rent=rent,
            available_for_sale=business_type == 'SALE' if for_sale is None else for_sale,
            available_for_rent=business_type == 'RENT' if for_rent is None else for_rent,
            warranty_months=12,
            is_active=active,
        )

    def test_catalog_returns_sellable_and_rentable_active_products(self):
        visible = self._model('Visible RO')
        rental = self._model('Rental RO', business_type='RENT', rent=300)
        self._model('Free RO', price=0)
        self._model('Inactive RO', active=False)
        response = self.client.get(reverse('customer-shop-catalog'))
        self.assertEqual(response.status_code, 200)
        ids = [item['id'] for item in response.data['products']]
        self.assertEqual(ids, [rental.id, visible.id])

    def test_catalog_search_filters_products(self):
        self._model('Aqua Prime')
        self._model('Crystal Max')
        response = self.client.get(reverse('customer-shop-catalog'), {'q': 'Aqua'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['products']), 1)
        self.assertEqual(response.data['products'][0]['model_name'], 'Aqua Prime')

    def test_catalog_is_available_without_login(self):
        visible = self._model('Guest Visible RO')
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('customer-shop-catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['products'][0]['id'], visible.id)

    def test_catalog_supports_sale_rent_or_both_per_product(self):
        sale_only = self._model('Sale only')
        rent_only = self._model('Rent only', business_type='RENT', price=0, rent=450)
        both = self._model('Buy or rent', rent=550, for_sale=True, for_rent=True)

        response = self.client.get(reverse('customer-shop-catalog'))
        self.assertEqual(response.status_code, 200)
        products = {item['id']: item for item in response.data['products']}
        self.assertTrue(products[sale_only.id]['available_for_sale'])
        self.assertFalse(products[sale_only.id]['available_for_rent'])
        self.assertFalse(products[rent_only.id]['available_for_sale'])
        self.assertTrue(products[rent_only.id]['available_for_rent'])
        self.assertTrue(products[both.id]['available_for_sale'])
        self.assertTrue(products[both.id]['available_for_rent'])
