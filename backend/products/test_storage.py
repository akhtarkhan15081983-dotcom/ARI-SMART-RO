from django.core.files.storage import storages
from django.test import SimpleTestCase, override_settings

from .storage import product_image_storage


class ProductStorageTests(SimpleTestCase):
    @override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}})
    def test_local_development_uses_default_storage(self):
        self.assertIs(product_image_storage(), storages["default"])

    def test_production_separates_public_and_private_urls(self):
        # Load the actual production configuration without contacting R2.
        import os
        import runpy
        from unittest.mock import patch

        with patch.dict(os.environ, {
            "DJANGO_MEDIA_STORAGE_BACKEND": "s3",
            "AWS_ACCESS_KEY_ID": "test-access",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_STORAGE_BUCKET_NAME": "private-test",
            "AWS_PRODUCT_BUCKET_NAME": "public-test",
            "AWS_PRODUCT_CUSTOM_DOMAIN": "products.example.com",
            "AWS_S3_ENDPOINT_URL": "https://example.r2.cloudflarestorage.com",
            "AWS_S3_REGION_NAME": "auto",
            "AWS_S3_CUSTOM_DOMAIN": "old-public.example.com",
        }):
            config = runpy.run_module("config.settings")
        overrides = {key: value for key, value in config.items() if key.startswith("AWS_")}
        overrides["STORAGES"] = config["STORAGES"]
        with override_settings(**overrides):
            private = storages["default"]
            public = product_image_storage()
            self.assertEqual(private.bucket_name, "private-test")
            self.assertEqual(public.bucket_name, "public-test")
            self.assertIsNone(private.custom_domain)
            self.assertTrue(private.querystring_auth)
            self.assertFalse(public.querystring_auth)
            self.assertEqual(public.url("products/photo.jpg"), "https://products.example.com/products/photo.jpg")
            self.assertIn("X-Amz-Signature=", private.url("invoices/test.pdf"))
