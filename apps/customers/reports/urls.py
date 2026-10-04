from django.urls import path

from .views import CustomerPDFReportView


urlpatterns = [
    path(
        "customers/pdf/",
        CustomerPDFReportView.as_view(),
        name="customers-pdf-report",
    ),
]