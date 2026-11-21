from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, Response

SESSION_COOKIE = "clouddeck_session"
CSRF_COOKIE = "clouddeck_csrf"
SESSION_TTL_SECONDS = 12 * 60 * 60


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt_bytes = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt_bytes, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${base64.urlsafe_b64encode(salt_bytes).decode()}${base64.urlsafe_b64encode(derived).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_text, expected_text = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(expected_text.encode())
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=len(expected))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SessionSecurity:
    def __init__(self, cookie_secret: str) -> None:
        self.secret = _unb64(cookie_secret)

    def issue(self) -> tuple[str, str, int]:
        csrf = secrets.token_urlsafe(24)
        expires = int(time.time()) + SESSION_TTL_SECONDS
        nonce = secrets.token_urlsafe(12)
        payload = f"{expires}.{csrf}.{nonce}".encode("utf-8")
        signature = hmac.new(self.secret, payload, hashlib.sha256).digest()
        return f"{_b64(payload)}.{_b64(signature)}", csrf, expires

    def decode(self, token: str | None) -> tuple[str, int] | None:
        if not token or "." not in token:
            return None
        try:
            payload_text, signature_text = token.split(".", 1)
            payload = _unb64(payload_text)
            supplied = _unb64(signature_text)
            expected = hmac.new(self.secret, payload, hashlib.sha256).digest()
            if not hmac.compare_digest(supplied, expected):
                return None
            expires_text, csrf, _nonce = payload.decode("utf-8").split(".", 2)
            expires = int(expires_text)
            if expires < int(time.time()):
                return None
            return csrf, expires
        except (ValueError, UnicodeDecodeError):
            return None

    def set_cookies(self, response: Response, token: str, csrf: str, expires: int) -> None:
        max_age = max(0, expires - int(time.time()))
        common = {"secure": True, "samesite": "strict", "path": "/", "max_age": max_age}
        response.set_cookie(SESSION_COOKIE, token, httponly=True, **common)
        response.set_cookie(CSRF_COOKIE, csrf, httponly=False, **common)

    @staticmethod
    def clear_cookies(response: Response) -> None:
        response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
        response.delete_cookie(CSRF_COOKIE, path="/", secure=True, httponly=False, samesite="strict")

    @staticmethod
    def ensure_same_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        host = request.headers.get("host", "")
        if not origin:
            raise HTTPException(status_code=403, detail="Missing request origin.")
        parsed = urlsplit(origin)
        if not parsed.netloc or not hmac.compare_digest(parsed.netloc.lower(), host.lower()):
            raise HTTPException(status_code=403, detail="Cross-origin request rejected.")

    def require(self, request: Request, mutation: bool = False) -> str:
        decoded = self.decode(request.cookies.get(SESSION_COOKIE))
        if decoded is None:
            raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
        csrf, _expires = decoded
        if mutation:
            self.ensure_same_origin(request)
            cookie_csrf = request.cookies.get(CSRF_COOKIE, "")
            header_csrf = request.headers.get("x-csrf-token", "")
            if not hmac.compare_digest(csrf, cookie_csrf) or not hmac.compare_digest(csrf, header_csrf):
                raise HTTPException(status_code=403, detail="Request verification failed. Refresh and try again.")
        return csrf
