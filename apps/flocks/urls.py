from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import FlockViewSet
router = DefaultRouter()
router.register("", FlockViewSet, basename="flocks")
urlpatterns = router.urls
