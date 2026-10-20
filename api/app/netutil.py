from fastapi import Request

from .config import get_settings


def client_ip(request: Request) -> str:
    """The visitor's address. Behind the proxy, request.client is the proxy itself, so every visitor
    would share one rate-limit bucket; the proxy puts the real address first in X-Forwarded-For."""
    if get_settings().trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:64]
    return request.client.host if request.client else "unknown"
