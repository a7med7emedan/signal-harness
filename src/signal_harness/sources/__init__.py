"""Available source adapters, addressable by name."""

from __future__ import annotations

from .base import Candidate, Fetcher, HttpFetcher, RecordedFetcher, Source, SourceError
from .preprints import PreprintServer

__all__ = [
    "REGISTRY",
    "Candidate",
    "Fetcher",
    "HttpFetcher",
    "PreprintServer",
    "RecordedFetcher",
    "Source",
    "SourceError",
    "available",
    "get_source",
]

REGISTRY: dict[str, Source] = {
    "biorxiv": PreprintServer.biorxiv(),
    "medrxiv": PreprintServer.medrxiv(),
}


def get_source(name: str) -> Source:
    try:
        return REGISTRY[name]
    except KeyError as exc:
        raise SourceError(f"unknown source {name!r}. Available: {', '.join(available())}") from exc


def available() -> list[str]:
    return sorted(REGISTRY)
