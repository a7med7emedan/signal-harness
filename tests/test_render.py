"""Rendering is deterministic, escaped and structurally faithful to the model."""

from __future__ import annotations

import hashlib
from pathlib import Path

from signal_harness.models import Issue
from signal_harness.render import long_date, pretty_date, render_issue, split_columns

EXAMPLES = Path(__file__).resolve().parents[1] / "src" / "signal_harness" / "examples"
GOLDEN = EXAMPLES / "issue.sample.sha256"


def test_rendering_is_byte_for_byte_deterministic(issue):
    assert render_issue(issue) == render_issue(issue)


def test_rendering_matches_the_published_checksum(page):
    """The reproducibility claim in the README, enforced."""
    expected = GOLDEN.read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(page.encode("utf-8")).hexdigest() == expected


def test_every_entry_appears_once(issue, page):
    for entry in issue.entries:
        assert page.count(f'id="{entry.id}"') == 1


def test_every_primary_link_is_printed(issue, page):
    for entry in issue.entries:
        assert entry.url in page


def test_desk_bands_follow_the_fixed_order(page):
    order = ["b-policy", "b-clinic", "b-bio", "b-machine", "b-frontier", "b-record", "b-geek"]
    positions = [page.find(f"band {name}") for name in order]
    assert all(p > 0 for p in positions)
    assert positions == sorted(positions)


def test_the_page_is_self_contained(page):
    assert "<script" not in page
    assert "<link" not in page
    assert "<style>" in page


def test_user_text_is_escaped(raw):
    raw["entries"][1]["headline"] = "A <script>alert(1)</script> headline"
    page = render_issue(Issue.from_dict(raw))
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_reading_time_is_printed(issue, page):
    assert f"{issue.reading_minutes()} min read" in page


def test_submission_date_is_shown_when_it_differs(page):
    assert "submitted 3 Oct 2026" in page


def test_columns_never_reorder(issue):
    for desk in ("clinic", "bio"):
        entries = issue.by_desk(desk)
        left, right = split_columns(entries)
        assert left + right == entries


def test_columns_of_nothing_are_two_empty_lists():
    assert split_columns([]) == [[], []]


def test_dates_are_formatted_plainly():
    assert pretty_date("2026-10-07") == "7 Oct 2026"
    assert long_date("2026-10-07") == "Wednesday, 7 October 2026"
