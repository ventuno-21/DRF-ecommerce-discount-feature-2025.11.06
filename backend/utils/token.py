from datetime import datetime, timedelta

import jwt
from django.conf import settings


def generate_password_reset_token(user):
    exp = datetime.utcnow() + timedelta(
        hours=getattr(settings, "PASSWORD_RESET_TOKEN_EXP_HOURS", 1)
    )
    payload = {
        "user_id": user.id,
        "email": user.email,
        "exp": exp,
        "type": "password_reset",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def verify_password_reset_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "password_reset":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
