from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/accounts/", include("apps.accounts.api_urls")),
    path("api/flocks/", include("apps.flocks.urls")),
    path("api/production/", include("apps.production.urls")),
    path("api/feed/", include("apps.feed.urls")),
    path("api/health/", include("apps.health.urls")),
    path("api/customers/", include("apps.customers.urls")),
    path("api/sales/", include("apps.sales.urls")),
    path("api/expenses/", include("apps.expenses.urls")),
    path("api/suppliers/", include("apps.suppliers.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/settings/", include("apps.settings.urls")),
]
