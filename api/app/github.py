"""GitHub OAuth (authorization code flow with state and PKCE). Only the numeric GitHub user id is used,
and only to match a user who already exists; an OAuth login never creates an account."""
import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
from fastapi.responses import RedirectResponse

from .config import get_settings

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"

OAUTH_COOKIE = "oauth_state"
MODES = ("login", "link")


def enabled() -> bool:
    s = get_settings()
    return bool(s.github_client_id and s.github_client_secret and s.github_redirect_uri)


def challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def start(mode: str) -> RedirectResponse:
    """Send the browser to GitHub. State and PKCE verifier wait in a short-lived httpOnly cookie."""
    s = get_settings()
    state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    query = urlencode(
        {
            "client_id": s.github_client_id,
            "redirect_uri": s.github_redirect_uri,
            "state": state,
            "code_challenge": challenge(verifier),
            "code_challenge_method": "S256",
            "allow_signup": "false",
        }
    )
    resp = RedirectResponse(f"{AUTHORIZE_URL}?{query}", status_code=303)
    resp.set_cookie(
        OAUTH_COOKIE, f"{mode}.{state}.{verifier}", httponly=True, samesite="lax", secure=s.cookie_secure, max_age=600
    )
    return resp


def read_cookie(raw: str) -> tuple[str, str, str]:
    """(mode, state, verifier) from the cookie, or empty strings when it is missing or malformed."""
    mode, _, rest = raw.partition(".")
    state, _, verifier = rest.partition(".")
    return (mode, state, verifier) if mode in MODES else ("", "", "")


class GitHub:
    async def user_id(self, code: str, verifier: str) -> int | None:
        """Trade the code for a token, then read the account's numeric id. None on any failure."""
        s = get_settings()
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                token_resp = await http.post(
                    TOKEN_URL,
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": s.github_client_id,
                        "client_secret": s.github_client_secret,
                        "code": code,
                        "redirect_uri": s.github_redirect_uri,
                        "code_verifier": verifier,
                    },
                )
                token = token_resp.json().get("access_token") if token_resp.status_code == 200 else None
                if not token:
                    return None
                user_resp = await http.get(
                    USER_URL, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
                )
                github_id = user_resp.json().get("id") if user_resp.status_code == 200 else None
                return github_id if isinstance(github_id, int) else None
        except (httpx.HTTPError, ValueError):
            return None


def get_github() -> GitHub:
    return GitHub()
