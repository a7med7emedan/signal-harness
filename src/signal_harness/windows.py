"""Per desk freshness windows.

A window of N days means nothing published before today minus N days may be
printed under that desk. Fast moving desks keep a tight window. Slow desks
look back further, so a desk can be filled without reaching for filler.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

DEFAULT_WINDOWS: dict[str, int] = {
    "clinic": 3,
    "bio": 3,
    "machine": 7,
    "policy": 10,
    "record": 10,
    "geek": 10,
    "frontier": 30,
}

MINIMUM_ENTRIES_PER_DESK = 4


@dataclass(frozen=True)
class Window:
    desk: str
    days: int

    def oldest(self, issue_date: _dt.date) -> _dt.date:
        return issue_date - _dt.timedelta(days=self.days)

    def contains(self, published: _dt.date, issue_date: _dt.date) -> bool:
        return self.oldest(issue_date) <= published <= issue_date

    def describe(self, issue_date: _dt.date) -> str:
        return f"Window: {self.oldest(issue_date).isoformat()} to {issue_date.isoformat()}"


def window_for(desk: str, windows: dict[str, int] | None = None) -> Window:
    table = windows or DEFAULT_WINDOWS
    if desk not in table:
        raise KeyError(f"no window configured for desk {desk!r}")
    return Window(desk=desk, days=table[desk])


def filter_to_window(
    candidates, desk: str, issue_date: _dt.date, windows: dict[str, int] | None = None
):
    """Keep only candidates inside the desk window.

    ``candidates`` is any iterable of objects carrying a ``published`` date.
    """
    window = window_for(desk, windows)
    return [c for c in candidates if window.contains(c.published, issue_date)]
