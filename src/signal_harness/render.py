"""Render a validated issue to one self contained HTML file.

Everything is inlined: no stylesheet request, no font request, no script. The
output opens from a local file with no network at all. The same input always
produces the same bytes, so a build can be checksummed and compared.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .models import DESK_TITLES, DESKS, Entry, Issue
from .windows import window_for

TEMPLATE_DIR = Path(__file__).parent / "templates"
MASTHEAD = "SIGNAL"
TAGLINE = "AI for medicine, biology and policy"

METERS = {"WEAK": "▁", "EARLY": "▃", "SOLID": "▅", "HARD": "▇"}

DESK_TAGS = {
    "policy": "Policy",
    "clinic": "Clinic",
    "bio": "Bio",
    "machine": "Machine",
    "frontier": "Frontier",
    "record": "Off record",
    "geek": "Geek",
}


# Month and weekday names are fixed tables rather than strftime, which reads
# the process locale. The same issue must render to the same bytes on every
# machine, whatever language its operating system is set to.
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def pretty_date(value: str) -> str:
    date = _dt.date.fromisoformat(value)
    return f"{date.day} {MONTHS[date.month - 1][:3]} {date.year}"


def long_date(value: str) -> str:
    date = _dt.date.fromisoformat(value)
    return f"{WEEKDAYS[date.weekday()]}, {date.day} {MONTHS[date.month - 1]} {date.year}"


def split_columns(entries: list[Entry]) -> list[list[Entry]]:
    """Distribute entries between two columns without reordering them.

    Full stories weigh three times a brief, so the cut balances visual height
    rather than count. Everything in the first column precedes everything in
    the second, which keeps ids ascending in document order.
    """
    if not entries:
        return [[], []]
    weights = [3 if e.is_full else 1 for e in entries]
    half = sum(weights) / 2
    running = 0
    for index, weight in enumerate(weights):
        running += weight
        if running >= half:
            return [entries[: index + 1], entries[index + 1 :]]
    return [entries, []]  # pragma: no cover - the loop always returns


def build_environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    env.filters["pretty_date"] = pretty_date
    env.filters["split_columns"] = split_columns
    return env


def render_issue(issue: Issue, *, masthead: str = MASTHEAD, tagline: str = TAGLINE) -> str:
    """Return the complete HTML document for one issue."""
    issue_date = _dt.date.fromisoformat(issue.date)
    desks = [d for d in DESKS if issue.by_desk(d)]
    window_lines = {d: window_for(d, issue.windows).describe(issue_date) for d in desks}
    template = build_environment().get_template("issue.html.j2")
    return template.render(
        issue=issue,
        masthead=masthead,
        tagline=tagline,
        css=(TEMPLATE_DIR / "issue.css").read_text(encoding="utf-8").strip(),
        desks=desks,
        desk_titles=DESK_TITLES,
        desk_tags=DESK_TAGS,
        meters=METERS,
        window_lines=window_lines,
        long_date=long_date(issue.date),
    )


def write_issue(issue: Issue, path: str | Path, **kwargs) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render_issue(issue, **kwargs).encode("utf-8"))  # LF on every OS
    return out
