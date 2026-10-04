from django.urls import path

from .views import HealthPDFReportView
from .mortality_views import MortalityPDFReportView


urlpatterns = [
    path(
        "health/pdf/",
        HealthPDFReportView.as_view(),
        name="health-pdf-report",
    ),

    path(
        "mortality/pdf/",
        MortalityPDFReportView.as_view(),
        name="mortality-pdf-report",
    ),
]