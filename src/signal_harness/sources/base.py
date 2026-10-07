"""Source adapters.

Every adapter turns some remote listing into ``Candidate`` objects. Network
access sits behind the ``Fetcher`` protocol so that the adapters can be tested
against recorded payloads without touching the network.
"""

from __future__ import annotations

import datetime as _dt
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

USER_AGENT = "signal-harness/1.0 (+https://github.com/a7med7emedan/signal-harness)"
DEFAULT_TIMEOUT = 30.0


class SourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Candidate:
    """One item a desk might print, before any editorial judgement."""

    title: str
    url: str
    published: _dt.date
    source: str
    submitted: _dt.date | None = None
    summary: str = ""
    authors: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def dates_differ(self) -> bool:
        return self.submitted is not None and self.submitted != self.published


class Fetcher(Protocol):
    """Anything that can turn a URL into text."""

    def get(self, url: str) -> str:  # pragma: no cover - protocol
        ...


class HttpFetcher:
    """The real one. Plain standard library, no third party client."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, user_agent: str = USER_AGENT):
        self.timeout = timeout
        self.user_agent = user_agent

    def get(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            raise SourceError(f"{url} returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise SourceError(f"{url} could not be reached: {exc.reason}") from exc


class RecordedFetcher:
    """Serves payloads from a dictionary. Used by the tests and by --offline."""

    def __init__(self, payloads: dict[str, str]):
        self.payloads = payloads
        self.calls: list[str] = []

    def get(self, url: str) -> str:
        self.calls.append(url)
        try:
            return self.payloads[url]
        except KeyError as exc:
            raise SourceError(f"no recorded payload for {url}") from exc

    @classmethod
    def from_directory(cls, directory) -> RecordedFetcher:
        from pathlib import Path

        index = json.loads((Path(directory) / "index.json").read_text(encoding="utf-8"))
        payloads = {
            url: (Path(directory) / name).read_text(encoding="utf-8") for url, name in index.items()
        }
        return cls(payloads)


class Source(Protocol):
    """A named adapter that can list candidates for a date range."""

    name: str

    def fetch(
        self, fetcher: Fetcher, start: _dt.date, end: _dt.date
    ) -> list[Candidate]: ...  # pragma: no cover - protocol
