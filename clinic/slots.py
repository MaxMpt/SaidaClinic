from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

CLINIC_TZ = "Europe/Moscow"


def pad2(n: int) -> str:
    return f"{n:02d}"


def min_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def time_to_min(hhmm: str) -> int:
    parts = (hhmm or "0:0").split(":")
    return int(parts[0] or 0) * 60 + int(parts[1] or 0)


def ymd(d: date) -> str:
    return d.isoformat()


def parse_ymd(s: str) -> date:
    y, m, d = [int(x) for x in s[:10].split("-")]
    return date(y, m, d)


def iso_weekday(d: date) -> int:
    return d.isoweekday()


def clinic_now(tz: str = CLINIC_TZ) -> tuple[date, int]:
    now = datetime.now(ZoneInfo(tz))
    return now.date(), now.hour * 60 + now.minute


def overlaps(a1: int, a2: int, b1: int, b2: int) -> bool:
    return a1 < b2 and b1 < a2


def is_full_day(start: int, end: int) -> bool:
    return start <= 0 and end >= 1440


def compute_slots(
    day: date,
    duration_min: int,
    work_days: list[int],
    work_start: str,
    work_end: str,
    slot_step: int,
    buffer_min: int,
    busy: list[tuple[int, int]],
    force_open: bool,
    tz: str,
) -> list[int]:
    if any(is_full_day(s, e) for s, e in busy):
        return []
    if not force_open and iso_weekday(day) not in work_days:
        return []
    work_from = time_to_min(work_start)
    work_to = time_to_min(work_end)
    span = duration_min + buffer_min
    today, minutes = clinic_now(tz)
    slots: list[int] = []
    t = work_from
    while t + duration_min <= work_to:
        end = t + span
        if day < today:
            t += slot_step
            continue
        if day == today and t <= minutes + 20:
            t += slot_step
            continue
        if any(overlaps(t, end, b1, b2) for b1, b2 in busy):
            t += slot_step
            continue
        slots.append(t)
        t += slot_step
    return slots


def format_day_short(d: date) -> str:
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    return f"{d.day} {months[d.month - 1]}"


def format_day_long(d: date) -> str:
    names = [
        "понедельник", "вторник", "среда", "четверг",
        "пятница", "суббота", "воскресенье",
    ]
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    return f"{names[d.isoweekday() - 1]}, {d.day} {months[d.month - 1]}"
