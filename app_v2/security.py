import hmac
import secrets
from urllib.parse import urlsplit

from flask import request, session

from . import config


def ensure_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def csrf_valid(value):
    expected = session.get("csrf_token", "")
    supplied = str(value or "")
    return bool(expected) and hmac.compare_digest(expected, supplied)


def auth_configured():
    return bool(config.DASHBOARD_PASSWORD)


def verify_credentials(username, password):
    return (
        hmac.compare_digest(str(username or ""), config.DASHBOARD_USERNAME)
        and hmac.compare_digest(str(password or ""), config.DASHBOARD_PASSWORD)
    )


def logged_in():
    return session.get("authenticated") is True


def safe_next(value):
    if not value:
        return "/"
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return "/"
    if not value.startswith("/"):
        return "/"
    return value


def request_is_api():
    return request.path.startswith("/api/")
