from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import ProductCategory, ROModel


class CustomerShopCatalogTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='shop-test', password='test-pass-123')
        self.client.force_authenticate(self.user)
        self.category = ProductCategory.objects.create(name='Domestic RO')

    def _model(self, name, business_type='SALE', price=10000, active=True):
        return ROModel.objects.create(
            category=self.category,
            model_name=name,
            capacity='12 LPH',
            business_type=business_type,
            selling_price=price,
            warranty_months=12,
            is_active=active,
        )

    def test_catalog_only_returns_sellable_active_products(self):
        visible = self._model('Visible RO')
        self._model('Rental RO', business_type='RENT')
        self._model('Free RO', price=0)
        self._model('Inactive RO', active=False)
        response = self.client.get(reverse('customer-shop-catalog'))
        self.assertEqual(response.status_code, 200)
        ids = [item['id'] for item in response.data['products']]
        self.assertEqual(ids, [visible.id])

    def test_catalog_search_filters_products(self):
        self._model('Aqua Prime')
        self._model('Crystal Max')
        response = self.client.get(reverse('customer-shop-catalog'), {'q': 'Aqua'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['products']), 1)
        self.assertEqual(response.data['products'][0]['model_name'], 'Aqua Prime')
