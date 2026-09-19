from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/bootstrap", views.api_bootstrap),
    path("api/slots", views.api_slots),
    path("api/month", views.api_month),
    path("api/book", views.api_book),
    path("api/cancel", views.api_cancel),
    path("api/reschedule", views.api_reschedule),
    path("api/waitlist", views.api_waitlist),
    path("api/intake", views.api_intake),
    path("api/product", views.api_product),
    path("api/prepay", views.api_prepay),
    path("api/status", views.api_status),
    path("api/settings", views.api_settings),
    path("api/service", views.api_service),
    path("api/service/delete", views.api_service_delete),
    path("api/care/category", views.api_care_category),
    path("api/care/product", views.api_care_product),
    path("api/care/delete", views.api_care_delete),
    path("api/schedule", views.api_schedule),
    path("api/schedule/save", views.api_schedule_save),
    path("api/block-day", views.api_block_day),
    path("api/notifications/read", views.api_notifications_read),
    path("api/telegram", views.api_telegram),
]
