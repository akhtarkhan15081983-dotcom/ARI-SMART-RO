from django.conf import settings
from django.core.files.storage import storages


def product_image_storage():
    """Public catalogue bucket in production; normal local media in development."""
    return storages["products"] if "products" in settings.STORAGES else storages["default"]
