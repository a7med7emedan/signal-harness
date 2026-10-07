"""Data model for an issue.

The model is deliberately small and strict. Everything that reaches the
renderer has already been validated here, so the template can stay simple and
the gates can assume well formed input.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SIGNAL_LEVELS = ("WEAK", "EARLY", "SOLID", "HARD")

DESKS = ("policy", "clinic", "bio", "machine", "frontier", "record", "geek")

DESK_TITLES = {
    "policy": "The Policy Desk",
    "clinic": "The Clinic Desk",
    "bio": "The Bio Desk",
    "machine": "The Machine Desk",
    "frontier": "The Frontier Desk",
    "record": "Off the Record",
    "geek": "The Geek Bench",
}

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ValidationError(ValueError):
    """Raised when an issue document does not satisfy the model."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _parse_date(value: str, where: str) -> _dt.date:
    _require(
        isinstance(value, str) and bool(_ISO_DATE.match(value)),
        f"{where}: date must be YYYY-MM-DD, got {value!r}",
    )
    try:
        return _dt.date.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - guarded by the regex
        raise ValidationError(f"{where}: {exc}") from exc


@dataclass(frozen=True)
class Glossary:
    """One term and its one line, plain language definition."""

    term: str
    definition: str

    def validate(self, where: str) -> None:
        _require(bool(self.term.strip()), f"{where}: glossary term is empty")
        _require(
            bool(self.definition.strip()), f"{where}: glossary term '{self.term}' has no definition"
        )


@dataclass(frozen=True)
class Mechanism:
    """The four labelled steps plus the anchor.

    The steps are fixed on purpose. A mechanism box that does not say what the
    pieces are, what usually goes wrong, what changed and what the numbers
    count is a summary wearing a mechanism's clothes.
    """

    pieces: str
    normally_wrong: str
    what_they_did: str
    numbers_mean: str
    anchor: str

    STEPS = ("pieces", "normally_wrong", "what_they_did", "numbers_mean", "anchor")

    def validate(self, where: str) -> None:
        for name in self.STEPS:
            _require(
                bool(getattr(self, name).strip()), f"{where}: mechanism step '{name}' is empty"
            )


@dataclass
class Entry:
    """A single printed item."""

    id: str
    desk: str
    kind: str  # "lead", "story" or "brief"
    headline: str
    source: str
    url: str
    date: str
    signal: str
    body: Sequence[str]
    catch: str
    glossary: Sequence[Glossary]
    mechanism: Mechanism | None = None
    simple: str = ""
    why: str = ""
    submitted: str | None = None
    note: str = ""

    def validate(self) -> None:
        where = f"entry {self.id}"
        _require(bool(re.fullmatch(r"s\d{2}", self.id)), f"{where}: id must look like s00")
        _require(self.desk in DESKS, f"{where}: unknown desk {self.desk!r}")
        _require(self.kind in ("lead", "story", "brief"), f"{where}: unknown kind {self.kind!r}")
        _require(self.signal in SIGNAL_LEVELS, f"{where}: signal must be one of {SIGNAL_LEVELS}")
        _require(self.url.startswith("http"), f"{where}: url must be absolute")
        _parse_date(self.date, where)
        if self.submitted is not None:
            _parse_date(self.submitted, where + " submitted")
        _require(bool(self.headline.strip()), f"{where}: missing headline")
        _require(bool(self.catch.strip()), f"{where}: missing catch")
        _require(len(self.body) >= 1, f"{where}: missing body")
        _require(len(self.glossary) >= 1, f"{where}: glossary is empty")
        for item in self.glossary:
            item.validate(where)
        if self.is_full:
            _require(self.mechanism is not None, f"{where}: a full story needs a mechanism box")
            self.mechanism.validate(where)
            _require(bool(self.simple.strip()), f"{where}: a full story needs the plain words box")
            _require(bool(self.why.strip()), f"{where}: a full story needs the why it matters line")

    @property
    def is_full(self) -> bool:
        return self.kind in ("lead", "story")

    @property
    def published(self) -> _dt.date:
        return _dt.date.fromisoformat(self.date)


@dataclass
class Issue:
    """One dated issue, ready to render."""

    number: str
    date: str
    edition: str
    dateline: str
    entries: list[Entry]
    windows: dict[str, int]
    reading_words_per_minute: int = 200
    furniture: dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------------- loading

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Issue:
        try:
            entries = [cls._entry_from_dict(item) for item in raw["entries"]]
            issue = cls(
                number=raw["number"],
                date=raw["date"],
                edition=raw.get("edition", "Daily Dispatch"),
                dateline=raw.get("dateline", "Luxembourg"),
                entries=entries,
                windows={k: int(v) for k, v in raw["windows"].items()},
                reading_words_per_minute=int(raw.get("reading_words_per_minute", 200)),
                furniture=raw.get("furniture", {}),
            )
        except KeyError as exc:
            raise ValidationError(f"missing required field: {exc.args[0]}") from exc
        issue.validate()
        return issue

    @classmethod
    def from_json(cls, path: str | Path) -> Issue:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @staticmethod
    def _entry_from_dict(raw: dict[str, Any]) -> Entry:
        unknown = set(raw) - set(Entry.__dataclass_fields__)
        if unknown:
            raise ValidationError(f"entry {raw.get('id', '?')}: unknown fields {sorted(unknown)}")
        mech_raw = raw.get("mechanism")
        try:
            mechanism = Mechanism(**mech_raw) if mech_raw else None
            glossary = [Glossary(**g) for g in raw.get("glossary", [])]
        except TypeError as exc:
            raise ValidationError(f"entry {raw.get('id', '?')}: {exc}") from exc
        payload = {k: v for k, v in raw.items() if k not in ("mechanism", "glossary")}
        return Entry(mechanism=mechanism, glossary=glossary, **payload)

    # ------------------------------------------------------------ validation

    def validate(self) -> None:
        _parse_date(self.date, "issue")
        _require(
            bool(re.fullmatch(r"[A-Z]-\d{3}", self.number)),
            f"issue number must look like D-003, got {self.number!r}",
        )
        seen: set[str] = set()
        for entry in self.entries:
            entry.validate()
            _require(entry.id not in seen, f"duplicate entry id {entry.id}")
            seen.add(entry.id)
        ordered = [e.id for e in self.entries]
        _require(ordered == sorted(ordered), "entry ids must ascend in document order")
        leads = [e for e in self.entries if e.kind == "lead"]
        _require(len(leads) == 1, "an issue needs exactly one lead")
        _require(self.entries[0].kind == "lead", "the lead must come first")
        for desk in DESKS:
            _require(desk in self.windows, f"no window declared for desk {desk!r}")
        self.check_windows()

    def check_windows(self) -> None:
        """Refuse any entry dated outside its desk window or after the issue."""
        today = _dt.date.fromisoformat(self.date)
        problems = []
        for entry in self.entries:
            span = self.windows[entry.desk]
            oldest = today - _dt.timedelta(days=span)
            if entry.published < oldest:
                problems.append(
                    f"{entry.id} is dated {entry.date}, outside the "
                    f"{span} day window for the {entry.desk} desk"
                )
            if entry.published > today:
                problems.append(f"{entry.id} is dated after the issue date")
        if problems:
            raise ValidationError("; ".join(problems))

    # --------------------------------------------------------------- queries

    def by_desk(self, desk: str) -> list[Entry]:
        return [e for e in self.entries if e.desk == desk]

    def counts(self) -> dict[str, int]:
        return {desk: len(self.by_desk(desk)) for desk in DESKS}

    def word_count(self) -> int:
        words = 0
        for entry in self.entries:
            parts: list[str] = [entry.headline, entry.catch, entry.simple, entry.why, *entry.body]
            if entry.mechanism:
                parts.extend(v for k, v in asdict(entry.mechanism).items())
            parts.extend(g.definition for g in entry.glossary)
            words += sum(len(p.split()) for p in parts)
        return words

    def reading_minutes(self) -> int:
        return max(1, round(self.word_count() / self.reading_words_per_minute))


def load_issue(path: str | Path) -> Issue:
    """Convenience wrapper used by the command line interface."""
    return Issue.from_json(path)
