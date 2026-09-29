from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    FeedViewSet,
    FeedStockViewSet,
    FeedStockMovementViewSet,
    FeedConsumptionViewSet,
)


router = DefaultRouter()


router.register(
    "feeds",
    FeedViewSet,
    basename="feeds",
)


router.register(
    "stock",
    FeedStockViewSet,
    basename="feed-stock",
)


router.register(
    "movements",
    FeedStockMovementViewSet,
    basename="feed-stock-movements",
)


router.register(
    "consumption",
    FeedConsumptionViewSet,
    basename="feed-consumption",
)


urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]