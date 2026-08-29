from django.contrib import admin

from apps.settings_app.models import StoredCredential, UserSettings


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ["user", "in_app_notifications_enabled"]


@admin.register(StoredCredential)
class StoredCredentialAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "provider", "label", "revoked"]
    readonly_fields = ["encrypted_value"]

