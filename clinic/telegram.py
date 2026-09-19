from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from urllib.parse import parse_qsl

from django.conf import settings

import urllib.request


def admin_ids() -> list[str]:
    raw = str(getattr(settings, "ADMIN_TELEGRAM_ID", "6935237776") or "6935237776")
    ids = [x.strip() for x in raw.replace(";", ",").split(",") if x.strip()]
    return ids or ["6935237776"]


def admin_id() -> str:
    return admin_ids()[0]


def is_admin_tid(tid: str | int | None) -> bool:
    return str(tid or "") in admin_ids()


def parse_init_data(init_data: str) -> dict | None:
    if not init_data:
        return None
    params = dict(parse_qsl(init_data, keep_blank_values=True))
    given = params.pop("hash", "")
    user_raw = params.get("user")
    user = None
    if user_raw:
        try:
            u = json.loads(user_raw)
            if u.get("id"):
                user = {
                    "telegram_id": str(u["id"]),
                    "first_name": u.get("first_name") or "Гость",
                    "last_name": u.get("last_name") or "",
                    "username": u.get("username") or "",
                }
        except json.JSONDecodeError:
            user = None
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    if not token:
        return user
    if not given or not user:
        return None
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, given):
        return None
    return user


def telegram_send(chat_id: str | int, text: str, extra: dict | None = None) -> bool:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    if not token:
        return False
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if extra:
        payload.update(extra)
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as res:
            body = json.loads(res.read().decode())
            return bool(body.get("ok"))
    except Exception:
        return False


def telegram_api(method: str, payload: dict) -> dict:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    if not token:
        return {}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as res:
            return json.loads(res.read().decode())
    except Exception:
        return {}


def set_webhook() -> None:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    origin = getattr(settings, "MINI_APP_URL", "") or ""
    if not token or not origin:
        return
    origin = origin.rstrip("/")
    telegram_api("setWebhook", {"url": f"{origin}/api/telegram", "allowed_updates": ["message"]})
    telegram_api(
        "setChatMenuButton",
        {"menu_button": {"type": "web_app", "text": "Кабинет", "web_app": {"url": origin}}},
    )