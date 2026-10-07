"""Append only ledger of everything that has been printed.

The ledger is the memory that stops an item being printed twice. It is a
JSON Lines file: one object per line, appended, never rewritten. Writes are
atomic at the line level, and a write that would duplicate an existing URL is
refused rather than silently dropped.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

REQUIRED_FIELDS = ("url", "headline", "date", "desk", "issue_number", "printed_on", "signal")


class LedgerError(RuntimeError):
    pass


@dataclass(frozen=True)
class Record:
    url: str
    headline: str
    date: str
    desk: str
    issue_number: str
    printed_on: str
    signal: str

    def as_json(self) -> str:
        return json.dumps(
            {f: getattr(self, f) for f in REQUIRED_FIELDS},
            ensure_ascii=False,
            sort_keys=True,
        )


class Ledger:
    """A read mostly view over the JSON Lines file, plus a guarded append."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    # ------------------------------------------------------------------ read

    def exists(self) -> bool:
        return self.path.exists()

    def __iter__(self) -> Iterator[Record]:
        if not self.path.exists():
            return iter(())
        return self._iter_records()

    def _iter_records(self) -> Iterator[Record]:
        with self.path.open("r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise LedgerError(
                        f"{self.path}: line {number} is not valid JSON: {exc}"
                    ) from exc
                missing = [f for f in REQUIRED_FIELDS if f not in data]
                if missing:
                    raise LedgerError(f"{self.path}: line {number} is missing {missing}")
                yield Record(**{f: data[f] for f in REQUIRED_FIELDS})

    def urls(self) -> set[str]:
        return {record.url for record in self}

    def count(self) -> int:
        return sum(1 for _ in self)

    # ----------------------------------------------------------------- write

    def append(self, records: Iterable[Record], *, allow_empty: bool = True) -> int:
        """Append records that are not already present. Returns how many landed.

        The file is opened in append mode and flushed to disk before the call
        returns, so an interrupted run leaves whole lines behind, never half
        a line.
        """
        known = self.urls()
        fresh: list[Record] = []
        seen_now: set[str] = set()
        for record in records:
            if record.url in known or record.url in seen_now:
                continue
            seen_now.add(record.url)
            fresh.append(record)
        if not fresh:
            if allow_empty:
                return 0
            raise LedgerError("every record was already in the ledger")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            for record in fresh:
                handle.write(record.as_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return len(fresh)


def records_from_issue(issue) -> list[Record]:
    """Build ledger records from a validated issue."""
    return [
        Record(
            url=entry.url,
            headline=entry.headline,
            date=entry.date,
            desk=entry.desk,
            issue_number=issue.number,
            printed_on=issue.date,
            signal=entry.signal,
        )
        for entry in issue.entries
    ]
