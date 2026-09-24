from django.contrib.auth.models import Permission, User

from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from .models import UserProfile, Role
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    RoleSerializer,
)


class IsAdminUser(permissions.BasePermission):
    """
    Only Django superusers or users with the KukuFarm
    Administrator role can manage system users and roles.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Django superusers always have access.
        if request.user.is_superuser:
            return True

        try:
            profile = request.user.profile

            return (
                profile.active
                and profile.role is not None
                and profile.role.active
                and profile.role.code == "admin"
            )

        except UserProfile.DoesNotExist:
            return False


class UserViewSet(viewsets.ModelViewSet):
    """
    User management API.

    GET    /api/accounts/users/
    POST   /api/accounts/users/
    GET    /api/accounts/users/<id>/
    PUT    /api/accounts/users/<id>/
    PATCH  /api/accounts/users/<id>/
    DELETE /api/accounts/users/<id>/
    """

    queryset = (
        User.objects
        .select_related(
            "profile",
            "profile__role",
        )
        .all()
        .order_by("username")
    )

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "profile__phone",
        "profile__job_title",
        "profile__role__name",
        "profile__role__code",
    ]

    ordering_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "date_joined",
    ]

    ordering = ["username"]

    def get_permissions(self):
        """
        Authenticated users can view users.

        Only administrators can create, update or delete users.
        """

        if self.action in {"list", "retrieve"}:
            return [
                permissions.IsAuthenticated()
            ]

        return [
            IsAdminUser()
        ]

    def get_serializer_class(self):
        if self.action in {
            "create",
            "update",
            "partial_update",
        }:
            return UserCreateSerializer

        return UserSerializer


class RoleViewSet(viewsets.ModelViewSet):
    """
    Dynamic KukuFarm role management API.

    GET    /api/accounts/roles/
    POST   /api/accounts/roles/
    GET    /api/accounts/roles/<id>/
    PUT    /api/accounts/roles/<id>/
    PATCH  /api/accounts/roles/<id>/
    DELETE /api/accounts/roles/<id>/
    """

    queryset = (
        Role.objects
        .prefetch_related("permissions")
        .all()
        .order_by("name")
    )

    serializer_class = RoleSerializer

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "name",
        "code",
        "description",
    ]

    ordering_fields = [
        "name",
        "code",
        "active",
        "created_at",
        "updated_at",
    ]

    ordering = ["name"]

    permission_classes = [
        IsAdminUser
    ]


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    """
    Return the currently authenticated user.

    GET /api/auth/me/
    """

    user = (
        User.objects
        .select_related(
            "profile",
            "profile__role",
        )
        .get(pk=request.user.pk)
    )

    return Response(
        UserSerializer(user).data
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def roles(request):
    """
    Legacy endpoint for active roles.

    GET /api/accounts/roles/
    """

    roles_queryset = (
        Role.objects
        .filter(active=True)
        .order_by("name")
    )

    data = []

    for role in roles_queryset:
        data.append(
            {
                "id": role.id,
                "name": role.name,
                "code": role.code,
                "description": role.description,
                "active": role.active,
            }
        )

    return Response(data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def permissions_list(request):
    """
    Return available Django permissions in a
    frontend-friendly format.

    GET /api/accounts/permissions/
    """

    permissions_queryset = (
        Permission.objects
        .select_related("content_type")
        .filter(
            content_type__app_label__in=[
                "accounts",
                "flocks",
                "production",
                "feed",
                "health",
                "customers",
                "sales",
                "expenses",
                "suppliers",
                "reports",
                "settings",
            ]
        )
        .order_by(
            "content_type__app_label",
            "codename",
        )
    )

    data = []

    for permission in permissions_queryset:
        app_label = permission.content_type.app_label
        codename = permission.codename

        if codename.startswith("add_"):
            action = "create"

        elif codename.startswith("change_"):
            action = "edit"

        elif codename.startswith("delete_"):
            action = "delete"

        elif codename.startswith("view_"):
            action = "view"

        else:
            action = codename

        data.append(
            {
                "id": permission.id,
                "code": f"{app_label}.{action}",
                "name": permission.name,
                "codename": permission.codename,
                "app_label": app_label,
                "action": action,
            }
        )

    return Response(data)

