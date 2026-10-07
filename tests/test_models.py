"""The model is the first gate: bad input should never reach the renderer."""

from __future__ import annotations

import pytest

from signal_harness.models import Issue, ValidationError


def test_example_loads(issue):
    assert issue.number == "D-003"
    assert len(issue.entries) == 9
    assert issue.entries[0].kind == "lead"


def test_counts_cover_every_printed_entry(issue):
    assert sum(issue.counts().values()) == len(issue.entries)


def test_reading_time_is_positive(issue):
    assert issue.reading_minutes() >= 1


def test_duplicate_ids_are_refused(raw):
    raw["entries"][2]["id"] = raw["entries"][1]["id"]
    with pytest.raises(ValidationError, match="duplicate entry id"):
        Issue.from_dict(raw)


def test_ids_must_ascend(raw):
    raw["entries"][1]["id"], raw["entries"][2]["id"] = (
        raw["entries"][2]["id"],
        raw["entries"][1]["id"],
    )
    with pytest.raises(ValidationError, match="ascend"):
        Issue.from_dict(raw)


def test_exactly_one_lead(raw):
    raw["entries"][3]["kind"] = "lead"  # already a full story, so only the count changes
    with pytest.raises(ValidationError, match="exactly one lead"):
        Issue.from_dict(raw)


def test_unknown_signal_is_refused(raw):
    raw["entries"][1]["signal"] = "STRONG"
    with pytest.raises(ValidationError, match="signal must be"):
        Issue.from_dict(raw)


def test_unknown_desk_is_refused(raw):
    raw["entries"][1]["desk"] = "sport"
    with pytest.raises(ValidationError, match="unknown desk"):
        Issue.from_dict(raw)


def test_full_story_needs_a_mechanism(raw):
    raw["entries"][0].pop("mechanism")
    with pytest.raises(ValidationError, match="needs a mechanism box"):
        Issue.from_dict(raw)


def test_full_story_needs_every_mechanism_step(raw):
    raw["entries"][0]["mechanism"]["anchor"] = "   "
    with pytest.raises(ValidationError, match="anchor"):
        Issue.from_dict(raw)


def test_entry_outside_its_window_is_refused(raw):
    raw["entries"][2]["date"] = "2026-09-01"  # clinic window is three days
    with pytest.raises(ValidationError, match="outside the 3 day window"):
        Issue.from_dict(raw)


def test_entry_dated_after_the_issue_is_refused(raw):
    raw["entries"][2]["date"] = "2026-11-01"
    with pytest.raises(ValidationError, match="after the issue date"):
        Issue.from_dict(raw)


def test_glossary_cannot_be_empty(raw):
    raw["entries"][1]["glossary"] = []
    with pytest.raises(ValidationError, match="glossary is empty"):
        Issue.from_dict(raw)


def test_glossary_definition_is_required(raw):
    raw["entries"][1]["glossary"][0]["definition"] = ""
    with pytest.raises(ValidationError, match="has no definition"):
        Issue.from_dict(raw)


def test_unknown_field_is_refused(raw):
    raw["entries"][1]["byline"] = "surprise"
    with pytest.raises(ValidationError, match="unknown fields"):
        Issue.from_dict(raw)


def test_every_desk_needs_a_window(raw):
    raw["windows"].pop("geek")
    with pytest.raises(ValidationError, match="no window declared"):
        Issue.from_dict(raw)


def test_issue_number_shape(raw):
    raw["number"] = "003"
    with pytest.raises(ValidationError, match="issue number"):
        Issue.from_dict(raw)


def test_a_malformed_glossary_item_is_reported(raw):
    raw["entries"][1]["glossary"][0] = {"term": "x"}
    with pytest.raises(ValidationError, match="entry s01"):
        Issue.from_dict(raw)


def test_full_story_needs_the_plain_words_box(raw):
    raw["entries"][0]["simple"] = ""
    with pytest.raises(ValidationError, match="plain words box"):
        Issue.from_dict(raw)


def test_a_missing_top_level_field_is_named(raw):
    raw.pop("windows")
    with pytest.raises(ValidationError, match="windows"):
        Issue.from_dict(raw)
