from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet
router = DefaultRouter()
router.register("", ExpenseViewSet, basename="expenses")
urlpatterns = router.urls
