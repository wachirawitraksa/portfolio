"""What the public may see. One rule, used by the public API and by the question box, so the two cannot disagree."""
from sqlalchemy import or_, select

from .models import Kind, Project


def project_visible() -> list:
    """Published, not in the trash, and not of a hidden or trashed kind.
    Hiding a kind hides what is filed under it; an entry with no kind at all stays visible."""
    out_of_sight = select(Kind.id).where(or_(Kind.hidden.is_(True), Kind.deleted_at.is_not(None)))
    return [
        Project.status == "published",
        Project.deleted_at.is_(None),
        or_(Project.kind_id.is_(None), Project.kind_id.not_in(out_of_sight)),
    ]
