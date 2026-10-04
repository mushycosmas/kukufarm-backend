from django.urls import path

from .views import SupplierPDFReportView


urlpatterns = [
    path(
        "suppliers/pdf/",
        SupplierPDFReportView.as_view(),
        name="suppliers-pdf-report",
    ),
]