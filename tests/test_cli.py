"""The command line interface, end to end, with exit codes scripts can rely on."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from signal_harness.cli import EXAMPLE, main

DATA = Path(__file__).parent / "data"


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert "signal-harness" in capsys.readouterr().out


def test_demo_builds_and_passes(tmp_path, capsys):
    out = tmp_path / "demo.html"
    assert main(["demo", "-o", str(out)]) == 0
    assert out.exists()
    assert "all gates passed" in capsys.readouterr().out


def test_render_then_gate(tmp_path):
    out = tmp_path / "issue.html"
    assert main(["render", str(EXAMPLE), "-o", str(out)]) == 0
    assert main(["gate", str(out)]) == 0


def test_gate_fails_a_broken_page(tmp_path, capsys):
    out = tmp_path / "issue.html"
    main(["render", str(EXAMPLE), "-o", str(out)])
    out.write_text(out.read_text(encoding="utf-8").replace("</article>", "", 1), encoding="utf-8")
    assert main(["gate", str(out)]) == 1
    assert "not publishable" in capsys.readouterr().out


def test_render_rejects_an_invalid_issue(tmp_path, capsys):
    bad = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    bad["entries"][1]["signal"] = "LOUD"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert main(["render", str(path), "-o", str(tmp_path / "x.html")]) == 1
    assert "issue rejected" in capsys.readouterr().err


def test_ledger_round_trip(tmp_path, capsys):
    ledger = tmp_path / "printed.jsonl"
    assert main(["ledger", "check", str(EXAMPLE), "--ledger", str(ledger)]) == 0
    assert main(["ledger", "append", str(EXAMPLE), "--ledger", str(ledger)]) == 0
    assert main(["ledger", "count", "--ledger", str(ledger)]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "9"
    # a second check now finds every entry already printed
    assert main(["ledger", "check", str(EXAMPLE), "--ledger", str(ledger)]) == 1


def test_ledger_append_is_idempotent(tmp_path):
    ledger = tmp_path / "printed.jsonl"
    main(["ledger", "append", str(EXAMPLE), "--ledger", str(ledger)])
    main(["ledger", "append", str(EXAMPLE), "--ledger", str(ledger)])
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 9


def test_ledger_needs_an_issue_for_append(capsys):
    assert main(["ledger", "append"]) == 1


def test_hunt_from_recorded_payloads(tmp_path, capsys):
    out = tmp_path / "candidates.json"
    code = main(
        [
            "hunt",
            "--source",
            "biorxiv",
            "--from",
            "2026-10-06",
            "--to",
            "2026-10-07",
            "--recorded",
            str(DATA),
            "-o",
            str(out),
        ]
    )
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert [c["published"] for c in payload] == ["2026-10-06", "2026-10-06"]


def test_hunt_can_filter_by_keyword(tmp_path):
    out = tmp_path / "candidates.json"
    main(
        [
            "hunt",
            "--source",
            "biorxiv",
            "--from",
            "2026-10-06",
            "--to",
            "2026-10-07",
            "--recorded",
            str(DATA),
            "--match",
            "protein",
            "-o",
            str(out),
        ]
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload) == 1 and "protein" in payload[0]["title"].lower()


def test_hunt_reports_an_unreachable_source(capsys):
    code = main(
        [
            "hunt",
            "--source",
            "medrxiv",
            "--from",
            "2026-10-06",
            "--to",
            "2026-10-07",
            "--recorded",
            str(DATA),
        ]
    )
    assert code == 2
    assert "source failed" in capsys.readouterr().err
