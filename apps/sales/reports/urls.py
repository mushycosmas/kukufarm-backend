from django.urls import path

from .views import SalesPDFReportView


urlpatterns = [
    path(
        "sales/pdf/",
        SalesPDFReportView.as_view(),
        name="sales-pdf-report",
    ),
]