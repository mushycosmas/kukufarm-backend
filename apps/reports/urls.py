from django.urls import path
from .views import dashboard, summary, production_chart
urlpatterns = [
    path("dashboard/", dashboard),
    path("summary/", summary),
    path("production-chart/", production_chart),
]
