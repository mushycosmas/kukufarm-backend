from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import EggProductionViewSet


# =========================================================
# ROUTER
# =========================================================

router = DefaultRouter()

router.register(
    "",
    EggProductionViewSet,
    basename="egg-production",
)


# =========================================================
# URLS
# =========================================================

urlpatterns = [
    # Egg Production CRUD
    path(
        "",
        include(router.urls),
    ),

    # Egg Production Reports
    path(
        "reports/",
        include(
            "apps.production.reports.urls"
        ),
    ),
]