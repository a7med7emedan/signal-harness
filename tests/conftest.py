from __future__ import annotations

import json
from pathlib import Path

import pytest

from signal_harness.models import Issue
from signal_harness.render import render_issue

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "src" / "signal_harness" / "examples" / "issue.sample.json"
DATA = Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def example_raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture()
def raw(example_raw) -> dict:
    """A deep copy, so a test can corrupt it without touching its neighbours."""
    return json.loads(json.dumps(example_raw))


@pytest.fixture(scope="session")
def issue(example_raw) -> Issue:
    return Issue.from_dict(json.loads(json.dumps(example_raw)))


@pytest.fixture(scope="session")
def page(issue) -> str:
    return render_issue(issue)
