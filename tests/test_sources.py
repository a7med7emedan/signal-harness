"""Source adapters are tested against recorded payloads, never the network."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest

from signal_harness.sources import (
    PreprintServer,
    RecordedFetcher,
    SourceError,
    available,
    get_source,
)
from signal_harness.sources.preprints import _submission_date

DATA = Path(__file__).parent / "data"
START = _dt.date(2026, 10, 6)
END = _dt.date(2026, 10, 7)


@pytest.fixture()
def fetcher() -> RecordedFetcher:
    return RecordedFetcher.from_directory(DATA)


def test_registry_lists_both_servers():
    assert available() == ["biorxiv", "medrxiv"]
    assert get_source("medrxiv").name == "medRxiv"


def test_unknown_source_names_the_alternatives():
    with pytest.raises(SourceError, match="biorxiv"):
        get_source("nature")


def test_pagination_follows_the_reported_total(fetcher):
    # The recorded pages are trimmed to a few records each for readability.
    # Paging is driven by the reported total, exactly as the endpoint documents.
    candidates = PreprintServer.biorxiv().fetch(fetcher, START, END)
    assert len(fetcher.calls) == 2
    assert fetcher.calls[1].endswith("/30")
    assert len(candidates) == 2  # the third record is a revision, see below


def test_revisions_are_dropped_by_default(fetcher):
    titles = [c.title for c in PreprintServer.biorxiv().fetch(fetcher, START, END)]
    assert "Zero shot super resolution for spatial data" not in titles


def test_revisions_can_be_asked_for(fetcher):
    server = PreprintServer.biorxiv()
    server.include_revisions = True
    titles = [c.title for c in server.fetch(fetcher, START, END)]
    assert "Zero shot super resolution for spatial data" in titles


def test_posting_date_is_the_publication_date(fetcher):
    first = PreprintServer.biorxiv().fetch(fetcher, START, END)[0]
    assert first.published == _dt.date(2026, 10, 6)


def test_submission_date_is_carried_when_it_differs(fetcher):
    first = PreprintServer.biorxiv().fetch(fetcher, START, END)[0]
    assert first.submitted == _dt.date(2026, 10, 4)
    assert first.dates_differ is True


def test_article_url_points_at_the_versioned_page(fetcher):
    first = PreprintServer.biorxiv().fetch(fetcher, START, END)[0]
    assert first.url.endswith("/content/10.64898/2026.10.04.756519v1")


def test_medrxiv_uses_its_own_host():
    url = PreprintServer.medrxiv().page_url(START, END, 0)
    assert url.startswith("https://api.medrxiv.org/details/medrxiv/")


def test_a_backwards_date_range_is_refused(fetcher):
    with pytest.raises(ValueError):
        PreprintServer.biorxiv().fetch(fetcher, END, START)


def test_a_missing_payload_is_reported(fetcher):
    with pytest.raises(SourceError, match="no recorded payload"):
        PreprintServer.medrxiv().fetch(fetcher, START, END)


@pytest.mark.parametrize(
    "doi,expected",
    [
        ("10.64898/2026.10.04.756519", _dt.date(2026, 10, 4)),
        ("10.1101/2025.07.17.25331721", _dt.date(2025, 7, 17)),
        ("10.1038/s41592-026-03237-0", None),
        ("nonsense", None),
    ],
)
def test_submission_date_is_read_from_the_identifier(doi, expected):
    assert _submission_date(doi) == expected
