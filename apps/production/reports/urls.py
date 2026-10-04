from django.urls import path

from .views import (
    EggProductionPDFReportView,
    EggInventoryPDFReportView,
)

app_name = "production_reports"

urlpatterns = [
    path(
        "pdf/",
        EggProductionPDFReportView.as_view(),
        name="egg-production-pdf-report",
    ),

    path(
        "egg-inventory/pdf/",
        EggInventoryPDFReportView.as_view(),
        name="egg-inventory-pdf-report",
    ),
]