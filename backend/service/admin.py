from django.contrib import admin

from .models import (
    Service,
    ServicePart,
    ServicePhoto,
    ServiceSignature,
)


admin.site.register(Service)
admin.site.register(ServicePart)
admin.site.register(ServicePhoto)
admin.site.register(ServiceSignature)