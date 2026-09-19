from __future__ import annotations

import json
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from .models import (
    Affirmation,
    Appointment,
    CareCategory,
    CareProduct,
    Client,
    DayHours,
    Loyalty,
    Notification,
    OpenDay,
    Review,
    Service,
    Setting,
    TimeBlock,
    Waitlist,
)
from .slots import (
    clinic_now,
    compute_slots,
    format_day_short,
    iso_weekday,
    min_to_time,
    parse_ymd,
    time_to_min,
    ymd,
)
from .telegram import admin_id, admin_ids, is_admin_tid, telegram_api, telegram_send

EMPTY_INTAKE = {
    "pregnancy": False,
    "herpes": False,
    "blood": False,
    "lidocaine": False,
    "autoimmune": False,
    "keloid": False,
    "retinoids": False,
    "diabetes": False,
    "sun": False,
    "note": "",
}


def parse_intake(raw) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    out = dict(EMPTY_INTAKE)
    for k in EMPTY_INTAKE:
        if k == "note":
            note = str(raw.get("note") or "")[:400]
            if "овчарк" in note.lower():
                note = ""
            out["note"] = note
        else:
            out[k] = bool(raw.get(k))
    return out


def get_map() -> dict[str, str]:
    return {s.key: s.value for s in Setting.objects.all()}


def load_settings() -> dict:
    m = get_map()
    about = m.get("about") or ""
    try:
        blocks = json.loads(m.get("about_blocks") or "[]")
        if not isinstance(blocks, list) or not blocks:
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        blocks = [
            {"type": "image", "src": "/static/about/saya.jpg"},
            {"type": "text", "text": about},
            {"type": "image", "src": "/static/about/diploma.jpg"},
        ]
    work_days = [int(x) for x in (m.get("work_days") or "6,7").split(",") if x.strip().isdigit()]
    return {
        "clinicName": m.get("clinic_name") or "Doc Saya",
        "about": about,
        "aboutBlocks": blocks,
        "address": m.get("address") or "",
        "timezone": m.get("timezone") or "Europe/Moscow",
        "workDays": work_days or [6, 7],
        "workStart": m.get("work_start") or "10:00",
        "workEnd": m.get("work_end") or "20:00",
        "slotStepMin": int(m.get("slot_step_min") or 30),
        "bufferMin": int(m.get("buffer_min") or 15),
        "cancelHours": int(m.get("cancel_hours") or 12),
        "prepayEnabled": m.get("prepay_enabled") == "1",
        "prepayDefaultPercent": int(m.get("prepay_default_percent") or 30),
        "prepayDefaultAmount": int(m.get("prepay_default_amount") or 0),
        "holdMinutes": int(m.get("hold_minutes") or 15),
        "phone": m.get("phone") or "",
        "adminTelegramId": admin_id(),
        "adminIds": admin_ids(),
        "adminUsername": "",
    }


def dump_service(s: Service) -> dict:
    return {
        "id": s.id,
        "slug": s.slug,
        "title": s.title,
        "category": s.category,
        "description": s.description,
        "durationMin": s.duration_min,
        "price": s.price,
        "prepayAmount": s.prepay_amount,
        "prepayPercent": s.prepay_percent,
        "prepText": s.prep_text,
        "aftercareText": s.aftercare_text,
        "indications": s.indications,
        "contraindications": s.contraindications,
        "resultText": s.result_text,
        "reactionsText": s.reactions_text,
        "imageKey": s.image_key,
        "invasive": s.invasive,
        "recommendDays": s.recommend_days,
        "sort": s.sort,
        "active": s.active,
    }


def dump_appt(a: Appointment) -> dict:
    s = a.service
    return {
        "id": a.id,
        "clientKey": a.client_key,
        "clientName": a.client_name,
        "serviceId": s.id,
        "serviceTitle": s.title,
        "category": s.category,
        "durationMin": s.duration_min,
        "price": a.price or s.price,
        "imageKey": s.image_key,
        "day": ymd(a.day),
        "startMin": a.start_min,
        "endMin": a.end_min,
        "status": a.status,
        "comment": a.comment,
        "source": a.source,
        "prepayRequired": a.prepay_required,
        "prepayPaid": a.prepay_paid,
        "holdUntil": a.hold_until.isoformat() if a.hold_until else None,
        "adminNote": a.admin_note,
        "prepText": s.prep_text,
        "aftercareText": s.aftercare_text,
    }


def expire_holds() -> None:
    Appointment.objects.filter(status="hold", hold_until__isnull=False, hold_until__lt=timezone.now()).update(
        status="expired"
    )


def occupied(day: date) -> list[tuple[int, int]]:
    busy = []
    for a in Appointment.objects.filter(day=day, status__in=["hold", "confirmed", "arrived"]):
        busy.append((a.start_min, a.end_min))
    for b in TimeBlock.objects.filter(day=day):
        busy.append((b.start_min, b.end_min))
    return busy


def hours_for(day: date, settings: dict) -> tuple[str, str]:
    row = DayHours.objects.filter(day=day).first()
    if row:
        return min_to_time(row.start_min), min_to_time(row.end_min)
    return settings["workStart"], settings["workEnd"]


def prepay_for(service: Service, settings: dict) -> int:
    if service.prepay_amount > 0:
        return service.prepay_amount
    if service.prepay_percent > 0:
        return max(0, round(service.price * service.prepay_percent / 100))
    if not settings["prepayEnabled"]:
        return 0
    if settings["prepayDefaultAmount"] > 0:
        return settings["prepayDefaultAmount"]
    if settings["prepayDefaultPercent"] > 0:
        return max(0, round(service.price * settings["prepayDefaultPercent"] / 100))
    return 0


def slots_for(service: Service, day: date, settings: dict) -> list[int]:
    start, end = hours_for(day, settings)
    return compute_slots(
        day,
        service.duration_min,
        settings["workDays"],
        start,
        end,
        settings["slotStepMin"],
        settings["bufferMin"],
        occupied(day),
        OpenDay.objects.filter(day=day).exists(),
        settings["timezone"],
    )


def upsert_client(user: dict, touch_seen: bool = False) -> str:
    tid = str(user["telegram_id"])
    username = user.get("username") or ""
    first = user.get("first_name") or "Гость"
    last = user.get("last_name") or ""
    obj, created = Client.objects.get_or_create(
        telegram_id=tid,
        defaults={
            "username": username,
            "first_name": first,
            "last_name": last,
            "role": "admin" if is_admin_tid(tid) else "client",
        },
    )
    role = "admin" if is_admin_tid(tid) or obj.role == "admin" else "client"
    if not created:
        changed = (
            obj.username != username
            or obj.first_name != first
            or obj.last_name != last
            or obj.role != role
        )
        if changed or touch_seen:
            obj.username = username
            obj.first_name = first
            obj.last_name = last
            obj.role = role
            obj.save()
    return role


def resolve_admin_username(*, fetch: bool = False) -> str:
    card = (
        Client.objects.filter(telegram_id__in=admin_ids())
        .exclude(username="")
        .first()
    )
    if card and card.username:
        return card.username
    if not fetch:
        return ""
    data = telegram_api("getChat", {"chat_id": admin_id()})
    result = data.get("result") or {}
    username = result.get("username") or ""
    if result:
        upsert_client(
            {
                "telegram_id": admin_id(),
                "username": username,
                "first_name": result.get("first_name") or "Сая",
                "last_name": result.get("last_name") or "",
            }
        )
    return username


def notify(kind: str, title: str, body: str, appointment_id: int | None = None) -> None:
    Notification.objects.create(kind=kind, title=title, body=body, appointment_id=appointment_id)


def notify_admin_telegram(text: str) -> None:
    username = resolve_admin_username(fetch=True)
    if username:
        if telegram_send(f"@{username.lstrip('@')}", text):
            return
    telegram_send(admin_id(), text)


def dump_client(tid: str) -> dict:
    c = Client.objects.filter(telegram_id=tid).first()
    if not c:
        return {
            "telegramId": tid or "",
            "username": "",
            "firstName": "",
            "lastName": "",
            "intake": dict(EMPTY_INTAKE),
            "intakeDone": False,
        }
    return {
        "telegramId": c.telegram_id,
        "username": c.username,
        "firstName": c.first_name,
        "lastName": c.last_name,
        "intake": parse_intake(c.intake),
        "intakeDone": c.intake_done,
    }


def dump_product(p: CareProduct) -> dict:
    photo = p.photo or ""
    if photo.startswith("/care/"):
        photo = "/static" + photo
    return {
        "id": p.id,
        "categoryId": p.category_id,
        "title": p.title,
        "description": p.description,
        "indications": p.indications,
        "contraindications": p.contraindications,
        "composition": p.composition,
        "price": p.price,
        "photo": photo,
        "sort": p.sort,
    }


def next_slots(settings: dict, services: list[Service], limit: int = 4) -> list[dict]:
    today, _ = clinic_now(settings["timezone"])
    found = []
    seen = set()
    for i in range(14):
        day = today + timedelta(days=i)
        for s in services:
            if s.id in seen:
                continue
            slots = slots_for(s, day, settings)
            if slots:
                found.append(
                    {
                        "serviceId": s.id,
                        "serviceTitle": s.title,
                        "day": ymd(day),
                        "startMin": slots[0],
                        "price": s.price,
                        "durationMin": s.duration_min,
                    }
                )
                seen.add(s.id)
            if len(found) >= limit:
                return found
    return found


def bootstrap(client_key: str, is_admin: bool, telegram_id: str) -> dict:
    expire_holds()
    settings_obj = load_settings()
    settings_obj["adminUsername"] = resolve_admin_username(fetch=False)
    qs = Service.objects.all() if is_admin else Service.objects.filter(active=True)
    services = list(qs)
    appts_qs = Appointment.objects.select_related("service").order_by("day", "start_min")
    if not is_admin:
        appts_qs = appts_qs.filter(client_key=client_key)
    today, _ = clinic_now(settings_obj["timezone"])
    closed = [
        ymd(b.day)
        for b in TimeBlock.objects.filter(day__gte=today, start_min__lte=0, end_min__gte=1440)
    ]
    notes = list(Notification.objects.order_by("-id")[:40]) if is_admin else []
    affirmation = Affirmation.objects.filter(active=True).order_by("sort")
    aff = ""
    if affirmation.exists():
        idx = today.toordinal() % affirmation.count()
        aff = list(affirmation)[idx].body
    loyalty, _ = Loyalty.objects.get_or_create(client_key=client_key)
    wait = []
    if is_admin:
        wait = [
            {
                "id": w.id,
                "clientKey": w.client_key,
                "clientName": w.client_name,
                "serviceId": w.service_id,
                "serviceTitle": w.service.title,
                "desiredDate": ymd(w.desired_date),
                "createdAt": w.created_at.isoformat(),
            }
            for w in Waitlist.objects.filter(active=True).select_related("service")[:30]
        ]
    cats = [{"id": c.id, "title": c.title, "sort": c.sort} for c in CareCategory.objects.all()]
    products = [dump_product(p) for p in CareProduct.objects.select_related("category")]
    return {
        "settings": settings_obj,
        "services": [dump_service(s) for s in services],
        "appointments": [dump_appt(a) for a in appts_qs],
        "nextSlots": next_slots(settings_obj, [s for s in services if s.active]),
        "loyalty": {"stamps": loyalty.stamps, "points": loyalty.points},
        "notifications": [
            {
                "id": n.id,
                "kind": n.kind,
                "title": n.title,
                "body": n.body,
                "appointmentId": n.appointment_id,
                "createdAt": n.created_at.isoformat(),
                "isRead": n.is_read,
            }
            for n in notes
        ],
        "unread": sum(1 for n in notes if not n.is_read),
        "waitlist": wait,
        "affirmation": aff,
        "closedDays": closed,
        "careCategories": cats,
        "careProducts": products,
        "reviews": [],
        "reviewable": [],
        "client": dump_client(telegram_id),
        "me": {
            "telegramId": telegram_id,
            "isAdmin": bool(is_admin),
            "name": dump_client(telegram_id).get("firstName") or "",
        },
    }


def create_booking(client_key: str, client_name: str, service_id: int, day_s: str, start_min: int, source: str, force: bool = False) -> dict:
    expire_holds()
    settings_obj = load_settings()
    service = Service.objects.filter(id=service_id, active=True).first()
    if not service:
        raise ValueError("Услуга недоступна")
    day = parse_ymd(day_s)
    busy = occupied(day)
    if any(s <= 0 and e >= 1440 for s, e in busy):
        raise ValueError("Этот день закрыт как выходной")
    slots = slots_for(service, day, settings_obj)
    if not force and start_min not in slots:
        raise ValueError("Это окно уже занято. Выберите другое время.")
    deposit = 0 if source == "admin" else prepay_for(service, settings_obj)
    status = "hold" if deposit > 0 else "confirmed"
    hold = timezone.now() + timedelta(minutes=settings_obj["holdMinutes"]) if deposit > 0 else None
    a = Appointment.objects.create(
        client_key=client_key,
        client_name=client_name,
        service=service,
        day=day,
        start_min=start_min,
        end_min=start_min + service.duration_min + settings_obj["bufferMin"],
        status=status,
        source=source,
        prepay_required=deposit,
        hold_until=hold,
        price=service.price,
    )
    when = f"{format_day_short(day)} в {min_to_time(start_min)}"
    title = "Новый холд — ждёт предоплату" if status == "hold" else "Новая запись"
    notify("booking", title, f"{client_name} · {service.title} · {when}", a.id)
    if source != "admin":
        extra = f"\nПредоплата {deposit} ₽" if deposit else ""
        notify_admin_telegram(f"Новая запись\n{client_name}\n{service.title}\n{when}{extra}")
    Waitlist.objects.filter(active=True, service=service, desired_date=day, client_key=client_key).update(active=False)
    return dump_appt(a)


def cancel_booking(client_key: str, is_admin: bool, appointment_id: int) -> None:
    a = Appointment.objects.select_related("service").filter(id=appointment_id).first()
    if not a:
        raise ValueError("Запись не найдена")
    if not is_admin and a.client_key != client_key:
        raise ValueError("Это не ваша запись")
    settings_obj = load_settings()
    if not is_admin:
        if a.status not in ("hold", "confirmed"):
            raise ValueError("Эту запись уже нельзя изменить")
        today, minutes = clinic_now(settings_obj["timezone"])
        now_abs = today.toordinal() * 1440 + minutes
        then_abs = a.day.toordinal() * 1440 + a.start_min
        if then_abs - now_abs < settings_obj["cancelHours"] * 60:
            raise ValueError(
                f"Перенос и отмена — не позже чем за {settings_obj['cancelHours']} часов. Если не успеваете — позвоните по {settings_obj['phone']}."
            )
    a.status = "cancelled"
    a.cancelled_at = timezone.now()
    a.save()
    notify("cancel", "Отмена", f"{a.client_name} · {a.service.title} · {format_day_short(a.day)} {min_to_time(a.start_min)}", a.id)


def reschedule_booking(client_key: str, is_admin: bool, appointment_id: int, day_s: str, start_min: int) -> dict:
    a = Appointment.objects.select_related("service").filter(id=appointment_id).first()
    if not a:
        raise ValueError("Запись не найдена")
    if not is_admin and a.client_key != client_key:
        raise ValueError("Это не ваша запись")
    settings_obj = load_settings()
    day = parse_ymd(day_s)
    slots = slots_for(a.service, day, settings_obj)
    if start_min not in slots:
        raise ValueError("Это окно уже занято. Выберите другое время.")
    a.day = day
    a.start_min = start_min
    a.end_min = start_min + a.service.duration_min + settings_obj["bufferMin"]
    a.save()
    notify("reschedule", "Перенос", f"{a.client_name} · {a.service.title} · {format_day_short(day)} {min_to_time(start_min)}", a.id)
    return dump_appt(a)


def month_grid(service_id: int, year: int, month: int) -> dict:
    expire_holds()
    settings_obj = load_settings()
    service = Service.objects.filter(id=service_id).first()
    if not service:
        return {"days": []}
    import calendar

    n = calendar.monthrange(year, month)[1]
    days = []
    for d in range(1, n + 1):
        day = date(year, month, d)
        slots = slots_for(service, day, settings_obj)
        closed = any(s <= 0 and e >= 1440 for s, e in occupied(day))
        days.append({"date": ymd(day), "available": bool(slots), "count": len(slots), "closed": closed})
    return {"days": days}


def schedule_month(year: int, month: int) -> dict:
    settings_obj = load_settings()
    import calendar

    n = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, n)
    closed = {ymd(b.day) for b in TimeBlock.objects.filter(day__gte=start, day__lte=end, start_min__lte=0, end_min__gte=1440)}
    opened = {ymd(o.day) for o in OpenDay.objects.filter(day__gte=start, day__lte=end)}
    hours = {ymd(h.day): (min_to_time(h.start_min), min_to_time(h.end_min)) for h in DayHours.objects.filter(day__gte=start, day__lte=end)}
    days = []
    for d in range(1, n + 1):
        day = date(year, month, d)
        key = ymd(day)
        default_work = iso_weekday(day) in settings_obj["workDays"]
        working = key in opened or (default_work and key not in closed)
        start_s, end_s = hours.get(key, (settings_obj["workStart"], settings_obj["workEnd"]))
        days.append({"date": key, "working": working, "start": start_s, "end": end_s})
    return {"days": days, "workStart": settings_obj["workStart"], "workEnd": settings_obj["workEnd"]}
