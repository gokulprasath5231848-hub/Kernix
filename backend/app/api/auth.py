"""Single-operator authentication.

Credentials are configured server-side (AUTH_EMAIL / AUTH_PASSWORD env vars) and
are never shipped to the browser. The login endpoint verifies them with a
constant-time comparison and issues an HMAC-signed, time-limited session token.
"""
import base64
import hashlib
import hmac
import logging
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    email: str
    expires_at: int


def _issue_token(email: str, secret: str, ttl_seconds: int) -> tuple[str, int]:
    """Return (token, expires_at). Token = base64url(payload).hex(hmac-sha256)."""
    expires_at = int(time.time()) + ttl_seconds
    payload = f"{email}:{expires_at}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    signature = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}", expires_at


def _verify_token(token: str, secret: str) -> bool:
    """Validate a token's signature and expiry."""
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return False
    expected = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        pad = "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64 + pad).decode()
        _, expires_at = payload.rsplit(":", 1)
        return int(expires_at) >= int(time.time())
    except (ValueError, UnicodeDecodeError):
        return False


async def require_auth(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Dependency guarding sensitive endpoints. No-op when login is not
    configured (AUTH_PASSWORD empty), so local/dev use is unaffected."""
    if not settings.AUTH_PASSWORD:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    token = authorization.split(" ", 1)[1].strip()
    if not _verify_token(token, settings.AUTH_SECRET):
        raise HTTPException(status_code=401, detail="Invalid or expired session.")


@router.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, settings: Settings = Depends(get_settings)):
    if not settings.AUTH_EMAIL or not settings.AUTH_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="Login is not configured. Set AUTH_EMAIL and AUTH_PASSWORD on the server.",
        )

    # Constant-time comparison to avoid leaking timing information. Email is
    # matched case-insensitively; the password must match exactly.
    email_ok = hmac.compare_digest(
        body.email.strip().lower(), settings.AUTH_EMAIL.strip().lower()
    )
    password_ok = hmac.compare_digest(body.password, settings.AUTH_PASSWORD)

    if not (email_ok and password_ok):
        logger.info("Failed login attempt for email=%r", body.email)
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token, expires_at = _issue_token(
        settings.AUTH_EMAIL.strip().lower(),
        settings.AUTH_SECRET,
        settings.AUTH_TOKEN_TTL_SECONDS,
    )
    return LoginResponse(
        token=token, email=settings.AUTH_EMAIL.strip().lower(), expires_at=expires_at
    )
