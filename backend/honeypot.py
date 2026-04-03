import time
import json


HONEYPOT_ENDPOINTS = [
    "/api/v1/internal/users",
    "/api/v1/admin/dump",
    "/api/v1/system/config",
    "/api/v1/debug/login",
    "/api/v1/hidden/export",
]

HONEYPOT_FIELDS = ["email_confirm", "phone_verify", "hidden_token", "bot_check"]

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "you are now",
    "SYSTEM:",
    "override",
    "jailbreak",
    "DAN",
    "act as",
]


def check_endpoint_honeypot(endpoint):
    return endpoint in HONEYPOT_ENDPOINTS


def check_form_honeypot(form_data: dict):
    for key in form_data:
        if key in HONEYPOT_FIELDS:
            return {"triggered": True, "trigger_type": "hidden_field"}

    for value in form_data.values():
        if isinstance(value, str):
            value_lower = value.lower()
            for pattern in INJECTION_PATTERNS:
                if pattern.lower() in value_lower:
                    return {"triggered": True, "trigger_type": "injection_pattern"}

    return {"triggered": False, "trigger_type": "none"}


def get_fake_response(endpoint):
    if endpoint == "/api/v1/internal/users":
        return {"users": ["admin", "root", "system"], "count": 3}
    if endpoint == "/api/v1/admin/dump":
        return {"status": "ok", "rows": 0, "data": []}
    if endpoint == "/api/v1/system/config":
        return {"version": "3.0", "env": "production", "debug": False}
    if endpoint == "/api/v1/debug/login":
        return {"token": "debug-disabled", "status": "ok"}
    return {"status": "ok"}
