
from django.urls import path

from .views import FlockPDFReportView


urlpatterns = [
    path(
        "flocks/pdf/",
        FlockPDFReportView.as_view(),
        name="flock-pdf-report",
    ),
]

