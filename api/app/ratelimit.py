import time
from collections import defaultdict, deque


class LoginLimiter:
    """Sliding one-minute window per IP. In memory: fine for one api process."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, ip: str, limit: int) -> bool:
        now = time.monotonic()
        hits = self._hits[ip]
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


login_limiter = LoginLimiter()
# Password checks on the account page: a stolen session must not be able to guess the password.
password_limiter = LoginLimiter()
# Bursts on the question box. The per-day limit per visitor is counted in the database.
ask_limiter = LoginLimiter()
