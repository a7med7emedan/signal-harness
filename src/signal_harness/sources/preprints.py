"""Preprint server adapters.

bioRxiv and medRxiv expose the same JSON details endpoint, so one adapter
serves both. The endpoint pages thirty records at a time and reports the total
in a messages block, which is what the pagination loop follows.

Two rules from the editorial side are enforced here rather than later:

* the posting date is the publication date, and the submission date is carried
  alongside it when the two differ;
* a revision whose first version predates the window is not new, so versions
  above one are dropped unless explicitly requested.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass

from .base import Candidate, Fetcher, SourceError

PAGE_SIZE = 30


@dataclass
class PreprintServer:
    """Adapter for one preprint server."""

    name: str
    api_host: str = "api.biorxiv.org"
    server: str = "biorxiv"
    site: str = "www.biorxiv.org"
    include_revisions: bool = False
    max_pages: int = 40

    @classmethod
    def biorxiv(cls) -> PreprintServer:
        return cls(name="bioRxiv")

    @classmethod
    def medrxiv(cls) -> PreprintServer:
        return cls(
            name="medRxiv", api_host="api.medrxiv.org", server="medrxiv", site="www.medrxiv.org"
        )

    # ------------------------------------------------------------------ urls

    def page_url(self, start: _dt.date, end: _dt.date, cursor: int) -> str:
        return (
            f"https://{self.api_host}/details/{self.server}/"
            f"{start.isoformat()}/{end.isoformat()}/{cursor}"
        )

    def article_url(self, doi: str, version: str | int) -> str:
        return f"https://{self.site}/content/{doi}v{version}"

    # ----------------------------------------------------------------- fetch

    def fetch(self, fetcher: Fetcher, start: _dt.date, end: _dt.date) -> list[Candidate]:
        if start > end:
            raise ValueError("start date is after end date")
        candidates: list[Candidate] = []
        cursor = 0
        total: int | None = None
        for _ in range(self.max_pages):
            payload = self._page(fetcher, start, end, cursor)
            messages = payload.get("messages") or [{}]
            total = self._total(messages[0], total)
            collection = payload.get("collection") or []
            if not collection:
                break
            candidates.extend(self._to_candidates(collection))
            cursor += PAGE_SIZE
            if total is not None and cursor >= total:
                break
        return candidates

    def _page(self, fetcher: Fetcher, start: _dt.date, end: _dt.date, cursor: int) -> dict:
        raw = fetcher.get(self.page_url(start, end, cursor))
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SourceError(f"{self.name}: response was not JSON: {exc}") from exc

    @staticmethod
    def _total(message: dict, previous: int | None) -> int | None:
        value = message.get("total")
        if value is None:
            return previous
        try:
            return int(value)
        except (TypeError, ValueError):
            return previous

    def _to_candidates(self, collection: list[dict]) -> list[Candidate]:
        out: list[Candidate] = []
        for record in collection:
            doi = record.get("doi")
            date = record.get("date")
            title = (record.get("title") or "").strip()
            if not (doi and date and title):
                continue
            version = str(record.get("version", "1"))
            if not self.include_revisions and version not in ("1", "1.0"):
                continue
            try:
                published = _dt.date.fromisoformat(date)
            except ValueError:
                continue
            out.append(
                Candidate(
                    title=title,
                    url=self.article_url(doi, version),
                    published=published,
                    submitted=_submission_date(doi),
                    source=self.name,
                    summary=(record.get("abstract") or "").strip(),
                    authors=tuple(
                        a.strip() for a in (record.get("authors") or "").split(";") if a.strip()
                    ),
                    extra={"doi": doi, "version": version, "category": record.get("category", "")},
                )
            )
        return out


def _submission_date(doi: str) -> _dt.date | None:
    """Both servers encode the submission date in the DOI suffix."""
    tail = doi.split("/")[-1]
    parts = tail.split(".")
    if len(parts) < 3:
        return None
    try:
        return _dt.date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (TypeError, ValueError):
        return None
