"""Paged users listing: filters, counts, clamp, and slicing for the owner
table. Lives beside the service because that file sits near the line cap.
Usable without FastAPI."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.models import User

StatusFilter = Literal["all", "active", "inactive"]
PAGE_SIZES = (10, 25, 50)
DEFAULT_PAGE_SIZE = 10

__all__ = [
    "DEFAULT_PAGE_SIZE",
    "PAGE_SIZES",
    "UsersPage",
    "escape_like",
    "list_page",
]


@dataclass(frozen=True)
class UsersPage:
    """One page of rows plus both counts; `total` drives the page count."""

    items: list[User]
    total: int
    total_all: int
    page: int
    page_size: int


def escape_like(needle: str) -> str:
    """Escape LIKE wildcards so user input matches literally."""
    return needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtered(query, q: str, status: StatusFilter):
    if q:
        query = query.where(User.email.ilike(f"%{escape_like(q)}%"))
    if status == "active":
        query = query.where(User.is_active.is_(True))
    if status == "inactive":
        query = query.where(User.is_active.is_(False))
    return query


def list_page(
    session: Session,
    q: str = "",
    status: StatusFilter = "all",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> UsersPage:
    """One page in stable id order; a page past the end clamps to the last."""
    needle = q.strip()
    query = _filtered(select(User), needle, status)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_all = session.scalar(select(func.count()).select_from(User)) or 0
    last_page = max(1, math.ceil(total / page_size))
    effective = min(max(1, page), last_page)
    items = list(
        session.scalars(
            query.order_by(User.id).offset((effective - 1) * page_size).limit(page_size)
        )
    )
    return UsersPage(
        items=items,
        total=total,
        total_all=total_all,
        page=effective,
        page_size=page_size,
    )
