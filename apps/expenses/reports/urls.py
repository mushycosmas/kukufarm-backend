from django.urls import path

from .views import ExpensePDFReportView


urlpatterns = [
    path(
        "expenses/pdf/",
        ExpensePDFReportView.as_view(),
        name="expense-pdf-report",
    ),
]