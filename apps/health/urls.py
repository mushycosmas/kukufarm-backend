from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HealthRecordViewSet, VaccinationViewSet, MortalityViewSet
router = DefaultRouter()
router.register("records", HealthRecordViewSet, basename="health-records")
router.register("vaccinations", VaccinationViewSet, basename="vaccinations")
router.register("mortality", MortalityViewSet, basename="mortality")
urlpatterns = [path("", include(router.urls))]
