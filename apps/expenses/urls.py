from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import ExpenseViewSet
from .reports.views import ExpensePDFReportView


router = DefaultRouter()

router.register(
    "",
    ExpenseViewSet,
    basename="expenses",
)


urlpatterns = router.urls + [
    path(
        "reports/expenses/pdf/",
        ExpensePDFReportView.as_view(),
        name="expense-pdf-report",
    ),
]