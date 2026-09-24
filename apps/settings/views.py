from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FarmSettings
from .serializers import FarmSettingsSerializer


class FarmSettingsView(APIView):
    """
    Global KukuFarm settings.

    GET
        /api/settings/

    PUT
        /api/settings/

    PATCH
        /api/settings/
    """

    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_object(self):
        """
        Return the single farm settings record.

        If it does not exist, create it automatically.
        """

        settings, created = FarmSettings.objects.get_or_create(
            pk=1,
            defaults={
                "farm_name": "KukuFarm",
                "currency": FarmSettings.Currency.TZS,
                "timezone": "Africa/Dar_es_Salaam",
                "date_format": FarmSettings.DateFormat.DD_MM_YYYY,
            },
        )

        return settings

    def get(self, request):
        settings = self.get_object()

        serializer = FarmSettingsSerializer(
            settings
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def put(self, request):
        settings = self.get_object()

        serializer = FarmSettingsSerializer(
            settings,
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        settings = self.get_object()

        serializer = FarmSettingsSerializer(
            settings,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
