from django.contrib import admin

from .models import FarmSettings


@admin.register(FarmSettings)
class FarmSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "farm_name",
        "owner_name",
        "phone",
        "currency",
        "timezone",
        "updated_at",
    )

    search_fields = (
        "farm_name",
        "owner_name",
        "phone",
        "email",
        "location",
    )

    list_filter = (
        "currency",
        "timezone",
        "email_notifications",
        "sms_notifications",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

