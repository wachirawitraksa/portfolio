from urllib.parse import urlparse

from .models import PROJECT_TEXT_FIELDS


def split_lines(text: str) -> list[str]:
    """One entry per line or comma, trimmed, no blanks, no repeats (case-insensitive)."""
    seen: dict[str, str] = {}
    for part in text.replace(",", "\n").splitlines():
        part = part.strip()
        if part:
            seen.setdefault(part.lower(), part)
    return list(seen.values())


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def untranslated(project) -> list[str]:
    """Names of text fields filled in one language and empty in the other."""
    return [
        name
        for name in PROJECT_TEXT_FIELDS
        if bool(getattr(project, f"{name}_th").strip()) != bool(getattr(project, f"{name}_en").strip())
    ]
