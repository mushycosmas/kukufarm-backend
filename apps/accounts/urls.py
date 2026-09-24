
from django.urls import path

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    UserViewSet,
    me,
    roles,
    permissions_list,
)


router = DefaultRouter()

router.register(
    "users",
    UserViewSet,
    basename="users",
)


urlpatterns = [
    # Authentication
    path(
        "login/",
        TokenObtainPairView.as_view(),
        name="login",
    ),

    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
        "verify/",
        TokenVerifyView.as_view(),
        name="token_verify",
    ),

    # Current authenticated user
    path(
        "me/",
        me,
        name="me",
    ),

    # User roles
    path(
        "roles/",
        roles,
        name="roles",
    ),

    # System permissions
    path(
        "permissions/",
        permissions_list,
        name="permissions",
    ),
] + router.urls
