"""The ledger is the only thing standing between the magazine and a repeat."""

from __future__ import annotations

import json

import pytest

from signal_harness.ledger import Ledger, LedgerError, Record, records_from_issue


def make(url: str, headline: str = "Something happened") -> Record:
    return Record(
        url=url,
        headline=headline,
        date="2026-10-07",
        desk="bio",
        issue_number="D-003",
        printed_on="2026-10-07",
        signal="EARLY",
    )


def test_missing_file_reads_as_empty(tmp_path):
    ledger = Ledger(tmp_path / "nope.jsonl")
    assert ledger.exists() is False
    assert ledger.count() == 0
    assert ledger.urls() == set()


def test_append_creates_the_file_and_its_parent(tmp_path):
    ledger = Ledger(tmp_path / "deep" / "printed.jsonl")
    assert ledger.append([make("https://example.org/a")]) == 1
    assert ledger.count() == 1


def test_append_is_additive(tmp_path):
    ledger = Ledger(tmp_path / "printed.jsonl")
    ledger.append([make("https://example.org/a")])
    ledger.append([make("https://example.org/b")])
    assert ledger.count() == 2
    assert ledger.urls() == {"https://example.org/a", "https://example.org/b"}


def test_a_url_is_never_written_twice(tmp_path):
    ledger = Ledger(tmp_path / "printed.jsonl")
    ledger.append([make("https://example.org/a")])
    added = ledger.append([make("https://example.org/a", "Reworded headline")])
    assert added == 0
    assert ledger.count() == 1


def test_duplicates_inside_one_batch_are_collapsed(tmp_path):
    ledger = Ledger(tmp_path / "printed.jsonl")
    added = ledger.append([make("https://example.org/a"), make("https://example.org/a")])
    assert added == 1


def test_existing_lines_are_left_untouched(tmp_path):
    path = tmp_path / "printed.jsonl"
    first = make("https://example.org/a").as_json()
    path.write_text(first + "\n", encoding="utf-8")
    Ledger(path).append([make("https://example.org/b")])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == first
    assert len(lines) == 2


def test_every_line_is_valid_json_with_the_required_fields(tmp_path):
    path = tmp_path / "printed.jsonl"
    Ledger(path).append([make("https://example.org/a")])
    data = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert set(data) == {"url", "headline", "date", "desk", "issue_number", "printed_on", "signal"}


def test_a_broken_line_is_reported_with_its_number(tmp_path):
    path = tmp_path / "printed.jsonl"
    path.write_text('{"url": "https://example.org/a"}\nnot json\n', encoding="utf-8")
    with pytest.raises(LedgerError, match="line 1 is missing"):
        Ledger(path).count()


def test_blank_lines_are_tolerated(tmp_path):
    path = tmp_path / "printed.jsonl"
    path.write_text(make("https://example.org/a").as_json() + "\n\n", encoding="utf-8")
    assert Ledger(path).count() == 1


def test_records_from_issue_cover_every_entry(issue):
    records = records_from_issue(issue)
    assert len(records) == len(issue.entries)
    assert {r.issue_number for r in records} == {issue.number}
    assert {r.printed_on for r in records} == {issue.date}


def test_refusing_an_empty_batch_is_opt_in(tmp_path):
    ledger = Ledger(tmp_path / "printed.jsonl")
    ledger.append([make("https://example.org/a")])
    with pytest.raises(LedgerError):
        ledger.append([make("https://example.org/a")], allow_empty=False)
