
from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet,
    RoleViewSet,
    me,
    permissions_list,
)


router = DefaultRouter()

router.register(
    "users",
    UserViewSet,
    basename="users",
)

router.register(
    "roles",
    RoleViewSet,
    basename="roles",
)


urlpatterns = [
    # Current authenticated user
    path(
        "me/",
        me,
        name="accounts-me",
    ),

    # Available system permissions
    path(
        "permissions/",
        permissions_list,
        name="accounts-permissions",
    ),
] + router.urls
