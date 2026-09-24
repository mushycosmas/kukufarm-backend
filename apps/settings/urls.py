from django.urls import path

from .views import FarmSettingsView


urlpatterns = [
    path(
        "",
        FarmSettingsView.as_view(),
        name="farm-settings",
    ),
]
