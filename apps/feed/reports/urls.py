from django.urls import path

from .views import FeedPDFReportView


urlpatterns = [
    path(
        "feed/pdf/",
        FeedPDFReportView.as_view(),
        name="feed-pdf-report",
    ),
]