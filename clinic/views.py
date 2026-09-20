from __future__ import annotations

import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import engine
from .models import (
    Appointment,
    CareCategory,
    CareProduct,
    Client,
    Notification,
    OpenDay,
    Service,
    Setting,
    TimeBlock,
    Waitlist,
)
from .slots import parse_ymd, time_to_min
from .telegram import admin_id, admin_ids, extract_user, parse_init_data, telegram_send


def _body(request) -> dict:
    if request.content_type and "json" in request.content_type:
        try:
            return json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()


def _identity(request, data: dict) -> dict | None:
    user = parse_init_data(data.get("initData") or request.headers.get("X-Telegram-Init-Data") or "")
    if user:
        return user
    tg = data.get("telegram") or {}
    if tg.get("telegramId") or tg.get("telegram_id"):
        if getattr(settings, "TELEGRAM_BOT_TOKEN", ""):
            return None
        return {
            "telegram_id": str(tg.get("telegramId") or tg.get("telegram_id")),
            "first_name": tg.get("firstName") or tg.get("first_name") or "Гость",
            "last_name": tg.get("lastName") or tg.get("last_name") or "",
            "username": tg.get("username") or "",
        }
    return None


def _actor(request) -> tuple[str, bool, str, dict]:
    data = _body(request)
    ident = _identity(request, data)
    if ident:
        role = engine.upsert_client(ident)
        tid = ident["telegram_id"]
        return f"tg-{tid}", role == "admin", tid, data
    unsigned = extract_user(data.get("initData") or "")
    if not unsigned:
        tg = data.get("telegram") or {}
        tid = str(tg.get("telegramId") or tg.get("telegram_id") or "")
        if tid:
            unsigned = {
                "telegram_id": tid,
                "first_name": tg.get("firstName") or tg.get("first_name") or "Гость",
                "last_name": tg.get("lastName") or tg.get("last_name") or "",
                "username": tg.get("username") or "",
            }
    if unsigned:
        tid = unsigned["telegram_id"]
        return f"tg-{tid}", False, tid, data
    if getattr(settings, "TELEGRAM_BOT_TOKEN", "") and not settings.DEBUG:
        raise PermissionError("Откройте кабинет из Telegram")
    return "anna", False, "anna", data


def _err(exc: Exception, status: int = 400):
    return JsonResponse({"error": str(exc)}, status=status)


@ensure_csrf_cookie
@require_GET
def index(request):
    return render(request, "clinic/index.html", {"admin_ids_json": json.dumps(admin_ids())})


@require_POST
def api_bootstrap(request):
    try:
        key, is_admin, tid, _ = _actor(request)
    except PermissionError as e:
        return _err(e, 401)
    return JsonResponse(engine.bootstrap(key, is_admin, tid))


@require_POST
def api_slots(request):
    data = _body(request)
    service = Service.objects.filter(id=data.get("serviceId")).first()
    if not service:
        return JsonResponse({"slots": [], "deposit": 0})
    settings_obj = engine.load_settings()
    engine.expire_holds()
    day = parse_ymd(data.get("date") or "")
    return JsonResponse(
        {"slots": engine.slots_for(service, day, settings_obj), "deposit": engine.prepay_for(service, settings_obj)}
    )


@require_POST
def api_month(request):
    data = _body(request)
    return JsonResponse(engine.month_grid(int(data["serviceId"]), int(data["year"]), int(data["month"])))


@require_POST
def api_book(request):
    try:
        key, is_admin, tid, data = _actor(request)
        ident = _identity(request, data)
        name = (ident or {}).get("first_name") or data.get("clientName") or "Гость"
        appt = engine.create_booking(
            key,
            name,
            int(data["serviceId"]),
            data["day"],
            int(data["startMin"]),
            "admin" if is_admin and data.get("source") == "admin" else data.get("source") or "app",
            bool(data.get("force")),
        )
        return JsonResponse(appt)
    except PermissionError as e:
        return _err(e, 401)
    except ValueError as e:
        return _err(e)


@require_POST
def api_cancel(request):
    try:
        key, is_admin, _, data = _actor(request)
        engine.cancel_booking(key, is_admin, int(data["appointmentId"]))
        return JsonResponse({"ok": True})
    except (PermissionError, ValueError) as e:
        return _err(e, 401 if isinstance(e, PermissionError) else 400)


@require_POST
def api_reschedule(request):
    try:
        key, is_admin, _, data = _actor(request)
        return JsonResponse(
            engine.reschedule_booking(key, is_admin, int(data["appointmentId"]), data["day"], int(data["startMin"]))
        )
    except (PermissionError, ValueError) as e:
        return _err(e, 401 if isinstance(e, PermissionError) else 400)


@require_POST
def api_waitlist(request):
    try:
        key, _, _, data = _actor(request)
        ident = _identity(request, data)
        name = (ident or {}).get("first_name") or data.get("clientName") or "Гость"
        Waitlist.objects.create(
            client_key=key,
            client_name=name,
            service_id=int(data["serviceId"]),
            desired_date=parse_ymd(data["day"]),
        )
        return JsonResponse({"ok": True})
    except PermissionError as e:
        return _err(e, 401)


@require_POST
def api_intake(request):
    try:
        _, _, tid, data = _actor(request)
        answers = engine.parse_intake(data.get("answers") or {})
        obj, _ = Client.objects.get_or_create(telegram_id=tid or data.get("clientKey") or "anna")
        obj.intake = answers
        obj.intake_done = True
        obj.save()
        return JsonResponse({"ok": True, "intake": answers})
    except PermissionError as e:
        return _err(e, 401)


@require_POST
def api_product(request):
    try:
        _, _, tid, data = _actor(request)
        product = CareProduct.objects.filter(id=data.get("productId")).first()
        if not product:
            return _err(ValueError("Средство не найдено"))
        ident = _identity(request, data)
        handle = f"@{(ident or {}).get('username')}" if (ident or {}).get("username") else (ident or {}).get("first_name") or "гость"
        engine.notify("shop", "Заявка на косметику", f"{handle} · {product.title}")
        return JsonResponse({"ok": True, "product": engine.dump_product(product), "adminUsername": engine.resolve_admin_username()})
    except PermissionError as e:
        return _err(e, 401)


@require_POST
def api_prepay(request):
    try:
        key, is_admin, _, data = _actor(request)
        a = Appointment.objects.filter(id=data.get("appointmentId")).first()
        if not a:
            return _err(ValueError("Запись не найдена"))
        if not is_admin and a.client_key != key:
            return _err(ValueError("Это не ваша запись"))
        a.prepay_paid = a.prepay_required
        a.status = "confirmed"
        a.hold_until = None
        a.save()
        engine.notify("prepay", "Предоплата получена", f"{a.client_name} · {a.service.title}", a.id)
        return JsonResponse({"ok": True})
    except PermissionError as e:
        return _err(e, 401)


@require_POST
def api_status(request):
    try:
        _, is_admin, _, data = _actor(request)
        if not is_admin:
            return _err(PermissionError("Только администратор"), 403)
        a = Appointment.objects.filter(id=data.get("appointmentId")).first()
        if not a:
            return _err(ValueError("Запись не найдена"))
        a.status = data.get("status") or a.status
        a.save()
        return JsonResponse({"ok": True})
    except PermissionError as e:
        return _err(e, 403)


@require_POST
def api_settings(request):
    try:
        _, is_admin, _, data = _actor(request)
        if not is_admin:
            return _err(PermissionError("Только администратор"), 403)
        patch = data.get("patch") or data
        mapping = {
            "clinicName": "clinic_name",
            "about": "about",
            "address": "address",
            "workStart": "work_start",
            "workEnd": "work_end",
            "phone": "phone",
            "prepayEnabled": "prepay_enabled",
            "prepayDefaultPercent": "prepay_default_percent",
            "aboutBlocks": "about_blocks",
            "workDays": "work_days",
        }
        for src, key in mapping.items():
            if src not in patch:
                continue
            val = patch[src]
            if src == "prepayEnabled":
                val = "1" if val else "0"
            elif src == "aboutBlocks":
                val = json.dumps(val, ensure_ascii=False)
            elif src == "workDays" and isinstance(val, list):
                val = ",".join(str(x) for x in val)
            Setting.objects.update_or_create(key=key, defaults={"value": str(val)})
        return JsonResponse({"ok": True, "settings": engine.load_settings()})
    except PermissionError as e:
        return _err(e, 403)


@require_POST
def api_service(request):
    try:
        _, is_admin, _, data = _actor(request)
        if not is_admin:
            return _err(PermissionError("Только администратор"), 403)
        payload = data.get("service") or data
        sid = payload.get("id")
        fields = {
            "title": payload.get("title") or "Процедура",
            "category": payload.get("category") or "",
            "description": payload.get("description") or "",
            "duration_min": int(payload.get("durationMin") or 60),
            "price": int(payload.get("price") or 0),
            "indications": payload.get("indications") or "",
            "contraindications": payload.get("contraindications") or "",
            "result_text": payload.get("resultText") or "",
            "reactions_text": payload.get("reactionsText") or "",
            "prep_text": payload.get("prepText") or "",
            "aftercare_text": payload.get("aftercareText") or "",
            "invasive": bool(payload.get("invasive")),
            "active": payload.get("active", True),
        }
        if sid:
            Service.objects.filter(id=sid).update(**fields)
            s = Service.objects.get(id=sid)
        else:
            slug = (payload.get("title") or "proc").lower().replace(" ", "-")[:40]
            s = Service.objects.create(slug=f"{slug}-{Service.objects.count()+1}", **fields)
        return JsonResponse(engine.dump_service(s))
    except PermissionError as e:
        return _err(e, 403)


@require_POST
def api_service_delete(request):
    try:
        _, is_admin, _, data = _actor(request)
        if not is_admin:
            return _err(PermissionError("Только администратор"), 403)
        Service.objects.filter(id=data.get("id")).delete()
        return JsonResponse({"ok": True})
    except PermissionError as e:
        return _err(e, 403)


@require_POST
def api_care_category(request):
    try:
        _, is_admin, _, data = _actor(request)
        if not is_admin:
            return _err(PermissionError("Только администратор"), 403)
        cid = data.get("id")
        if cid:
            CareCategory.objects.filter(id=cid).update(title=data.get("title") or "Категория")
            c = CareCategory.objects.get(id=cid)
        else:
            c = CareCategory.objects.create(title=data.get("title") or "Категория", sort=CareCategory.objects.count() + 1)
        return JsonResponse({"id": c.id, "title": c.title, "sort": c.sort})
    except PermissionError as e:
        return _err(e, 403)


@require_POST
def api_care_product(request):
    try:
        _, is_admin, _, data = _actor(request)
        if not is_admin:
            return _err(PermissionError("Только администратор"), 403)
        pid = data.get("id")
        fields = {
            "category_id": int(data["categoryId"]),
            "title": data.get("title") or "Средство",
            "description": data.get("description") or "",
            "indications": data.get("indications") or "",
            "contraindications": data.get("contraindications") or "",
            "composition": data.get("composition") or "",
            "price": int(data.get("price") or 0),
            "photo": data.get("photo") or "",
        }
        if pid:
            CareProduct.objects.filter(id=pid).update(**fields)
            p = CareProduct.objects.get(id=pid)
        else:
            p = CareProduct.objects.create(**fields)
        return JsonResponse(engine.dump_product(p))
    except PermissionError as e:
        return _err(e, 403)


@require_POST
def api_care_delete(request):
    try:
        _, is_admin, _, data = _actor(request)
        if not is_admin:
            return _err(PermissionError("Только администратор"), 403)
        kind = data.get("kind")
        if kind == "category":
            CareCategory.objects.filter(id=data.get("id")).delete()
        else:
            CareProduct.objects.filter(id=data.get("id")).delete()
        return JsonResponse({"ok": True})
    except PermissionError as e:
        return _err(e, 403)


@require_POST
def api_schedule(request):
    data = _body(request)
    return JsonResponse(engine.schedule_month(int(data["year"]), int(data["month"])))


@require_POST
def api_schedule_save(request):
    try:
        _, is_admin, _, data = _actor(request)
        if not is_admin:
            return _err(PermissionError("Только администратор"), 403)
        work_start = data.get("workStart")
        work_end = data.get("workEnd")
        if work_start:
            Setting.objects.update_or_create(key="work_start", defaults={"value": work_start})
        if work_end:
            Setting.objects.update_or_create(key="work_end", defaults={"value": work_end})
        for row in data.get("days") or []:
            day = parse_ymd(row["date"])
            working = bool(row.get("working"))
            if working:
                TimeBlock.objects.filter(day=day, start_min__lte=0, end_min__gte=1440).delete()
                OpenDay.objects.get_or_create(day=day)
            else:
                OpenDay.objects.filter(day=day).delete()
                TimeBlock.objects.get_or_create(day=day, start_min=0, end_min=1440, defaults={"reason": "Выходной"})
        return JsonResponse({"ok": True})
    except PermissionError as e:
        return _err(e, 403)


@require_POST
def api_block_day(request):
    try:
        _, is_admin, _, data = _actor(request)
        if not is_admin:
            return _err(PermissionError("Только администратор"), 403)
        day = parse_ymd(data["day"])
        if data.get("clear"):
            TimeBlock.objects.filter(day=day).delete()
            OpenDay.objects.get_or_create(day=day)
        else:
            OpenDay.objects.filter(day=day).delete()
            TimeBlock.objects.get_or_create(day=day, start_min=0, end_min=1440, defaults={"reason": data.get("reason") or "Выходной"})
        return JsonResponse({"ok": True})
    except PermissionError as e:
        return _err(e, 403)


@require_POST
def api_notifications_read(request):
    try:
        _, is_admin, _, _ = _actor(request)
        if is_admin:
            Notification.objects.filter(is_read=False).update(is_read=True)
        return JsonResponse({"ok": True})
    except PermissionError as e:
        return _err(e, 401)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_telegram(request):
    if request.method == "GET":
        return JsonResponse({"ok": True, "service": "doc-saya", "bot": bool(getattr(settings, "TELEGRAM_BOT_TOKEN", ""))})
    try:
        update = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)
    msg = update.get("message") or {}
    frm = msg.get("from") or {}
    text = (msg.get("text") or "").strip()
    if not frm.get("id") or not text:
        return JsonResponse({"ok": True})
    role = engine.upsert_client(
        {
            "telegram_id": str(frm["id"]),
            "first_name": frm.get("first_name") or "Гость",
            "last_name": frm.get("last_name") or "",
            "username": frm.get("username") or "",
        },
        touch_seen=True,
    )
    if not text.startswith("/start"):
        return JsonResponse({"ok": True})
    mini = (getattr(settings, "MINI_APP_URL", "") or "").rstrip("/")
    name = (frm.get("first_name") or "").strip()
    extra = {}
    if mini:
        extra["reply_markup"] = {
            "inline_keyboard": [[{"text": "Открыть кабинет", "web_app": {"url": mini}}]]
        }
    if role == "admin":
        hello = "Сая, кабинет на месте. Запись, график и витрина — по кнопке ниже."
    elif name:
        hello = f"Здравствуйте, {name}. Я Сая. Запись на процедуру и уход с полки кабинета — внутри приложения."
    else:
        hello = "Здравствуйте. Я Сая. Запись на процедуру и уход с полки кабинета — внутри приложения."
    telegram_send(frm["id"], hello, extra)
    return JsonResponse({"ok": True})