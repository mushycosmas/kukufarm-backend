
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EggProductionViewSet


router = DefaultRouter()

router.register(
    "",
    EggProductionViewSet,
    basename="egg-production",
)


urlpatterns = [
    path("", include(router.urls)),
]
