from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import healthcheck

urlpatterns = [
    path('health/', healthcheck, name='healthcheck'),
    path('admin/', admin.site.urls),
    path('api/', include('jobs.urls')),
    path('api/', include('partmaster.urls')),
    path('api/', include('purchase.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('inventory.urls')),
    path('api/installations/', include('installation.urls')),
    path('api/customers/', include('customers.urls')),
    path('api/attendance/', include('attendance.urls')),
    path('api/', include('employees.urls')),
    path('api/products/', include('products.urls')),
    path('api/service/', include('service.urls')),
    path('api/assets/', include('assets.urls')),
    path('api/complaints/', include('complaints.urls')),
    path('api/referrals/', include('referrals.urls')),
    path('api/andy/', include('andy.urls')),
    path('api/reports/', include('reporting.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
