from django.urls import path

from .views import EggInventoryView


urlpatterns = [
    path(
        "",
        EggInventoryView.as_view(),
        name="egg-inventory",
    ),
]
