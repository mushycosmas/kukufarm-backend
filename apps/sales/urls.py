from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import SaleViewSet
router = DefaultRouter()
router.register("", SaleViewSet, basename="sales")
urlpatterns = router.urls
