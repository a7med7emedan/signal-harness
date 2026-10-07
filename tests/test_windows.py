"""Window arithmetic, including the boundaries, which is where it matters."""

from __future__ import annotations

import datetime as _dt

import pytest

from signal_harness.windows import DEFAULT_WINDOWS, Window, filter_to_window, window_for

ISSUE_DATE = _dt.date(2026, 10, 7)


class Item:
    def __init__(self, published: _dt.date):
        self.published = published


def test_default_table_covers_every_desk():
    assert set(DEFAULT_WINDOWS) == {
        "clinic",
        "bio",
        "machine",
        "policy",
        "record",
        "geek",
        "frontier",
    }


@pytest.mark.parametrize("desk,days", sorted(DEFAULT_WINDOWS.items()))
def test_window_for_returns_the_table_value(desk, days):
    assert window_for(desk).days == days


def test_unknown_desk_raises():
    with pytest.raises(KeyError):
        window_for("sport")


def test_oldest_day_is_inside_the_window():
    window = Window("clinic", 3)
    assert window.contains(_dt.date(2026, 10, 4), ISSUE_DATE) is True


def test_the_day_before_the_window_is_outside():
    window = Window("clinic", 3)
    assert window.contains(_dt.date(2026, 10, 3), ISSUE_DATE) is False


def test_the_issue_date_itself_is_inside():
    window = Window("clinic", 3)
    assert window.contains(ISSUE_DATE, ISSUE_DATE) is True


def test_the_future_is_outside():
    window = Window("frontier", 30)
    assert window.contains(_dt.date(2026, 10, 8), ISSUE_DATE) is False


def test_filter_keeps_only_what_fits():
    items = [Item(_dt.date(2026, 10, 6)), Item(_dt.date(2026, 9, 1)), Item(_dt.date(2026, 10, 7))]
    kept = filter_to_window(items, "clinic", ISSUE_DATE)
    assert len(kept) == 2


def test_describe_names_both_ends():
    text = Window("policy", 10).describe(ISSUE_DATE)
    assert "2026-09-27" in text and "2026-10-07" in text
