from django.core.management.base import BaseCommand

from clinic.telegram import set_webhook


class Command(BaseCommand):
    help = "Ставит webhook бота на MINI_APP_URL/api/telegram"

    def handle(self, *args, **options):
        set_webhook()
        self.stdout.write(self.style.SUCCESS("webhook обновлён"))
