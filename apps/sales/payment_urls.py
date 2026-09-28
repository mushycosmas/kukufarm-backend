from rest_framework.routers import DefaultRouter

from .views import SalePaymentViewSet


router = DefaultRouter()

router.register(
    "",
    SalePaymentViewSet,
    basename="sale-payments",
)

urlpatterns = router.urls