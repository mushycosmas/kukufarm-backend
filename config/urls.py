
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    # Admin
    path(
        "admin/",
        admin.site.urls,
    ),

    # Authentication
    path(
        "api/auth/",
        include("apps.accounts.urls"),
    ),

    # Accounts
    path(
        "api/accounts/",
        include("apps.accounts.api_urls"),
    ),

    # Flocks
    path(
        "api/flocks/",
        include("apps.flocks.urls"),
    ),

    # Egg Production
    path(
        "api/production/",
        include("apps.production.urls"),
    ),

    # Egg Inventory
    path(
        "api/egg-inventory/",
        include("apps.production.inventory_urls"),
    ),

    # Feed
    path(
        "api/feed/",
        include("apps.feed.urls"),
    ),

    # Health
    path(
        "api/health/",
        include("apps.health.urls"),
    ),

    # Customers
    path(
        "api/customers/",
        include("apps.customers.urls"),
    ),

    # Sales
    path(
        "api/sales/",
        include("apps.sales.urls"),
    ),
# Sale Payments
    path(
        "api/sale-payments/",
        include("apps.sales.payment_urls"),
    ),
    # Expenses
    path(
        "api/expenses/",
        include("apps.expenses.urls"),
    ),

    # Suppliers
    path(
        "api/suppliers/",
        include("apps.suppliers.urls"),
    ),

    # Reports
    path(
        "api/reports/",
        include("apps.reports.urls"),
    ),

    # Settings
    path(
        "api/settings/",
        include("apps.settings.urls"),
    ),
]
