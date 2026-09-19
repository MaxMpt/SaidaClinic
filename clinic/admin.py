from django.contrib import admin

from .models import (
    Affirmation,
    Appointment,
    CareCategory,
    CareProduct,
    Client,
    Notification,
    Service,
    Setting,
)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "duration_min", "active", "sort")
    list_editable = ("price", "active", "sort")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("day", "start_min", "client_name", "service", "status")
    list_filter = ("status", "day")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "first_name", "username", "role", "intake_done")


@admin.register(CareProduct)
class CareProductAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price")


admin.site.register(CareCategory)
admin.site.register(Setting)
admin.site.register(Notification)
admin.site.register(Affirmation)
admin.site.site_header = "Doc Saya"
admin.site.site_title = "Doc Saya"
