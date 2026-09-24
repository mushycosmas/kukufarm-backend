
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FeedViewSet,
    FeedPurchaseViewSet,
    FeedStockViewSet,
    FeedConsumptionViewSet,
)


router = DefaultRouter()

router.register(
    "feeds",
    FeedViewSet,
    basename="feeds",
)

router.register(
    "purchases",
    FeedPurchaseViewSet,
    basename="feed-purchases",
)

router.register(
    "consumption",
    FeedConsumptionViewSet,
    basename="feed-consumption",
)

router.register(
    "stock",
    FeedStockViewSet,
    basename="feed-stock",
)


urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]

