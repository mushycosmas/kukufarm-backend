from django.urls import path

from .views import EggProductionPDFReportView


app_name = "production_reports"


urlpatterns = [
    path(
        "pdf/",
        EggProductionPDFReportView.as_view(),
        name="egg-production-pdf-report",
    ),
]