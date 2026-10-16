import hmac
import secrets

from flask import current_app, session
from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature
)

SALT = "flip-hunter-review-actions-v1"


def serializer():
    if not current_app.secret_key:
        raise RuntimeError("Brak SECRET_KEY Flask")

    return URLSafeTimedSerializer(
        current_app.secret_key,
        salt=SALT
    )


def make_review_token(search_id, listing_id):
    nonce = session.get("_flip_review_nonce")

    if not nonce:
        nonce = secrets.token_urlsafe(32)
        session["_flip_review_nonce"] = nonce

    return serializer().dumps([
        nonce, int(search_id), str(listing_id)
    ])


def verify_review_token(token, search_id, listing_id):
    nonce = session.get("_flip_review_nonce")

    if not nonce or not token:
        return False

    try:
        data = serializer().loads(token, max_age=86400)
    except (BadSignature, ValueError, TypeError):
        return False

    if not isinstance(data, list) or len(data) != 3:
        return False

    return (
        isinstance(data[0], str)
        and hmac.compare_digest(data[0], nonce)
        and data[1] == search_id
        and data[2] == listing_id
    )
