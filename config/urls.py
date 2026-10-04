from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    # ============================================================
    # ADMIN
    # ============================================================
    path(
        "admin/",
        admin.site.urls,
    ),

    # ============================================================
    # AUTHENTICATION
    # ============================================================
    path(
        "api/auth/",
        include("apps.accounts.urls"),
    ),

    # ============================================================
    # ACCOUNTS
    # ============================================================
    path(
        "api/accounts/",
        include("apps.accounts.api_urls"),
    ),

    # ============================================================
    # FLOCKS
    # ============================================================
    path(
        "api/flocks/",
        include("apps.flocks.urls"),
    ),

    # ============================================================
    # EGG PRODUCTION
    # ============================================================
    path(
        "api/production/",
        include("apps.production.urls"),
    ),

    # ============================================================
    # EGG INVENTORY
    # ============================================================
    path(
        "api/egg-inventory/",
        include("apps.production.inventory_urls"),
    ),

    # ============================================================
    # FEED
    # ============================================================
    path(
        "api/feed/",
        include("apps.feed.urls"),
    ),
    path(
         "api/reports/",
        include("apps.feed.reports.urls"),
    ),
    # ============================================================
    # HEALTH
    # ============================================================
    path(
        "api/health/",
        include("apps.health.urls"),
    ),
    path(
    "api/reports/",
    include("apps.health.reports.urls"),
    ),

    # ============================================================
    # CUSTOMERS
    # ============================================================
    path(
        "api/customers/",
        include("apps.customers.urls"),
    ),
    path(
        "api/reports/",
        include("apps.customers.reports.urls"),
    ),
    # ============================================================
    # SALES
    # ============================================================
    path(
        "api/sales/",
        include("apps.sales.urls"),
    ),
    path(
        "api/reports/",
        include("apps.sales.reports.urls"),
    ),
    # ============================================================
    # SALE PAYMENTS
    # ============================================================
    path(
        "api/sale-payments/",
        include("apps.sales.payment_urls"),
    ),

    # ============================================================
    # EXPENSES
    # ============================================================
    path(
        "api/expenses/",
        include("apps.expenses.urls"),
    ),

    # ============================================================
    # SUPPLIERS
    # ============================================================
    path(
        "api/suppliers/",
        include("apps.suppliers.urls"),
    ),
    path(
        "api/reports/",
        include("apps.suppliers.reports.urls"),
    ),
    # ============================================================
    # REPORTS
    # ============================================================

    # Flock Reports
    path(
        "api/reports/",
        include("apps.flocks.reports.urls"),
    ),

    # Egg Production & Egg Inventory Reports
    path(
        "api/reports/",
        include("apps.production.reports.urls"),
    ),

    # Expense Reports
    path(
        "api/reports/",
        include("apps.expenses.reports.urls"),
    ),

    # ============================================================
    # SETTINGS
    # ============================================================
    path(
        "api/settings/",
        include("apps.settings.urls"),
    ),
]


# ================================================================
# MEDIA FILES - DEVELOPMENT ONLY
# ================================================================
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )