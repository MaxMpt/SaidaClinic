from django.core.management.base import BaseCommand

from clinic.models import Affirmation, CareCategory, CareProduct, Client, Service, Setting
from clinic.telegram import admin_id

SETTINGS = {
    "clinic_name": "Doc Saya",
    "about": "Кабинет эстетической медицины. Врач Сая — дерматокосметолог. Работаю одна, поэтому каждое окно в календаре настоящее.",
    "address": "",
    "timezone": "Europe/Moscow",
    "work_days": "6,7",
    "work_start": "10:00",
    "work_end": "20:00",
    "slot_step_min": "30",
    "buffer_min": "15",
    "cancel_hours": "12",
    "prepay_enabled": "0",
    "prepay_default_percent": "30",
    "prepay_default_amount": "0",
    "hold_minutes": "15",
    "phone": "+7 999 120 45 67",
    "admin_telegram_id": admin_id(),
    "about_blocks": "[]",
}

SERVICES = [
    dict(slug="consult", title="Консультация врача", category="Приём", description="Разбор кожи, план на сезон, что можно и чего нельзя. Без продажи «пакета».", duration_min=30, price=4000, prep_text="Приходите без декоративной косметики, если это возможно.", aftercare_text="После консультации пришлю план ухода.", indications="Тусклый цвет, неровный рельеф, вопросы по домашнему уходу.", contraindications="Острое воспаление, температура, обострение герпеса.", result_text="План и понимание — сразу.", reactions_text="Обычно никаких.", image_key="hero", invasive=False, recommend_days=180, sort=1),
    dict(slug="cleaning", title="Чистка лица", category="Уход", description="Комбинированная чистка: ультразвук, механическая работа, успокаивающая маска.", duration_min=90, price=8500, prep_text="За 3 дня без кислот и ретинола. В день визита — без макияжа.", aftercare_text="24 часа не краситься, не париться, не трогать кожу руками. SPF обязательно.", indications="Чёрные точки, плотный себум, тусклость.", contraindications="Герпес в обострении, свежий загар, активный дерматит.", result_text="Кожа чище в этот же день.", reactions_text="Покраснение 2–6 часов.", image_key="room", invasive=False, recommend_days=45, sort=2),
    dict(slug="hydra", title="HydraFacial", category="Уход", description="Вакуумная чистка, сыворотки, сияние к вечеру. Можно в день события.", duration_min=75, price=12000, prep_text="Без агрессивного домашнего ухода за сутки.", aftercare_text="Можно краситься через 4 часа.", indications="Тусклость, обезвоженность, событие вечером.", contraindications="Повреждённый барьер, гнойнички, свежий пилинг.", result_text="Сияние в тот же день.", reactions_text="Лёгкий румянец до вечера.", image_key="still", invasive=False, recommend_days=30, sort=3),
    dict(slug="peel", title="Химический пилинг", category="Уход", description="Поверхностный или срединный — выбираем на консультации.", duration_min=50, price=9500, prep_text="Неделю без ретинола и кислот. Солнце — только с SPF 50.", aftercare_text="Шелушение — это нормально. Не сдирать. Только пантенол и SPF.", indications="Пятна, неровный тон, следы постакне.", contraindications="Беременность, активный герпес, свежий загар.", result_text="Тон выравнивается 7–14 дней.", reactions_text="Жжение в кабинете, затем шелушение.", image_key="skin", invasive=False, recommend_days=40, sort=4),
    dict(slug="biorev", title="Биоревитализация", category="Инъекции", description="Гиалуроновая кислота в кожу. Влажность, плотность.", duration_min=60, price=18000, prep_text="За 3 дня без алкоголя и препаратов, разжижающих кровь.", aftercare_text="Папулы сходят 1–3 дня. Спорт, баня, солнце — через 48 часов.", indications="Сухость, потеря плотности, мелкие морщины.", contraindications="Беременность и ГВ, герпес, препараты крови без согласования.", result_text="Влажность через 3–5 дней.", reactions_text="Папулы 1–3 дня.", image_key="skin", invasive=True, recommend_days=120, sort=5),
    dict(slug="botox", title="Ботулинотерапия", category="Инъекции", description="Лоб, межбровье, глаза. Естественная мимика, не «маска».", duration_min=45, price=16000, prep_text="Нельзя в день процедуры: спорт, алкоголь, наклоны.", aftercare_text="4 часа не ложиться, не трогать зону.", indications="Мимические морщины лба, межбровья, глаз.", contraindications="Беременность, миастения, аллергия на ботулотоксин.", result_text="Первый эффект на 3–5 день.", reactions_text="Точки уколов до вечера.", image_key="room", invasive=True, recommend_days=120, sort=6),
    dict(slug="lips", title="Контурная пластика губ", category="Инъекции", description="Форма и гидратация. Работаю аккуратно, без «уток».", duration_min=60, price=22000, prep_text="За неделю — без алкоголя. Если герпес бывает — курс ацикловира заранее.", aftercare_text="Отёк 2–3 дня. Без помады сутки.", indications="Тонкие губы, асимметрия.", contraindications="Герпес без профилактики, беременность.", result_text="Форма видна сразу.", reactions_text="Отёк 2–3 дня.", image_key="still", invasive=True, recommend_days=270, sort=7),
    dict(slug="meso", title="Мезотерапия", category="Инъекции", description="Коктейль под задачу. Курс из 4–6 процедур.", duration_min=50, price=14000, prep_text="Без алкоголя за сутки. Расскажите про аллергии.", aftercare_text="Точки могут быть красными до вечера.", indications="Тусклость, купероз, выпадение волос.", contraindications="Беременность, воспаление в зоне.", result_text="Сияние после 2–3 процедур.", reactions_text="Красные точки до вечера.", image_key="room", invasive=True, recommend_days=21, sort=8),
]

PRODUCTS = [
    ("Очищение", "Гель с аминокислотами", "Мягко снимает город и SPF, не сушит.", 3200, "/static/care/amino-gel.jpg"),
    ("Очищение", "Энзимная пудра", "Раз в неделю вместо скраба. Кожа гладкая, без микротравм.", 2800, "/static/care/enzyme-powder.jpg"),
    ("Увлажнение", "Сыворотка гиалурон 2%", "Слои влаги без липкости. Под крем утром и вечером.", 5400, "/static/care/hyaluron.jpg"),
    ("Увлажнение", "Крем-барьер с церамидами", "Закрывает влагу. Для тех, кто «всё щиплет».", 6100, "/static/care/ceramide.jpg"),
    ("Антиэйдж", "Ретинол 0.3% ночной", "Плотность и ровный тон. Вводим медленно.", 7800, "/static/care/retinol.jpg"),
    ("Антиэйдж", "Пептидный концентрат", "Для тех, кому рано ретинол. Лифтинг-ощущение к 4 неделе.", 8900, "/static/care/peptide.jpg"),
    ("SPF", "Флюид SPF 50", "Ежедневно, даже в пасмурный день. Не белит.", 4200, "/static/care/spf50.jpg"),
    ("SPF", "Минеральный SPF 30", "Для чувствительных и после пилинга.", 3900, "/static/care/spf30.jpg"),
]

AFFIRMATIONS = [
    "Я доверяю своему ритму.",
    "Кожа, которой хочется касаться.",
    "Сегодня я выбираю мягкость.",
    "Спокойная кожа — спокойный ум.",
    "Моё лицо помнит заботу.",
    "Я не спешу. Кожа не спешит.",
    "Свет идёт изнутри.",
    "Я берегу то, что светится.",
    "Красота без усилия — это уход.",
    "Моя кожа умеет восстанавливаться.",
]


class Command(BaseCommand):
    help = "Заполняет салон услугами, витриной и настройками, если база пустая"

    def handle(self, *args, **options):
        for k, v in SETTINGS.items():
            Setting.objects.get_or_create(key=k, defaults={"value": v})
        if not Setting.objects.filter(key="admin_telegram_id").exists():
            Setting.objects.create(key="admin_telegram_id", value=admin_id())
        Setting.objects.update_or_create(key="admin_telegram_id", defaults={"value": admin_id()})

        if not Service.objects.exists():
            for row in SERVICES:
                Service.objects.create(**row)
            self.stdout.write("услуги добавлены")

        if not CareCategory.objects.exists():
            cats = {}
            for i, title in enumerate(["Очищение", "Увлажнение", "Антиэйдж", "SPF"], start=1):
                cats[title] = CareCategory.objects.create(title=title, sort=i)
            for i, (cat, title, desc, price, photo) in enumerate(PRODUCTS, start=1):
                CareProduct.objects.create(category=cats[cat], title=title, description=desc, price=price, photo=photo, sort=i)
            self.stdout.write("витрина добавлена")

        if not Affirmation.objects.exists():
            for i, body in enumerate(AFFIRMATIONS, start=1):
                Affirmation.objects.create(body=body, sort=i)

        Client.objects.get_or_create(
            telegram_id=admin_id(),
            defaults={"first_name": "Сая", "role": "admin", "username": ""},
        )
        self.stdout.write(self.style.SUCCESS("seed ok"))
