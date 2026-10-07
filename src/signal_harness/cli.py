"""Command line interface.

    signal-harness demo                     build the bundled example end to end
    signal-harness render issue.json -o x   render one issue
    signal-harness gate x.html              run the publication gates
    signal-harness ledger append issue.json --ledger printed.jsonl
    signal-harness hunt --source medrxiv --from 2026-10-06 --to 2026-10-07

Exit codes: 0 success, 1 a gate failed or input was rejected, 2 a source could
not be reached. Scripts can rely on those.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from dataclasses import asdict
from importlib import resources
from pathlib import Path

from . import __version__
from .gates import errors, run_all
from .ledger import Ledger, records_from_issue
from .models import ValidationError, load_issue
from .render import render_issue, write_issue
from .sources import HttpFetcher, RecordedFetcher, SourceError, available, get_source

EXAMPLE = Path(str(resources.files("signal_harness.examples") / "issue.sample.json"))


def _print(stream, message: str) -> None:
    print(message, file=stream)


# ----------------------------------------------------------------- subcommands


def cmd_render(args: argparse.Namespace) -> int:
    try:
        issue = load_issue(args.issue)
    except ValidationError as exc:
        _print(sys.stderr, f"issue rejected: {exc}")
        return 1
    output = write_issue(issue, args.output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    _print(sys.stdout, f"wrote {output} ({output.stat().st_size} bytes, sha256 {digest[:16]})")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    doc = Path(args.page).read_text(encoding="utf-8")
    findings = run_all(doc, only=args.only)
    for finding in findings:
        _print(sys.stdout, str(finding))
    failed = errors(findings)
    if failed:
        _print(sys.stdout, f"{len(failed)} gate failure(s): not publishable")
        return 1
    _print(sys.stdout, f"all gates passed on {args.page}")
    return 0


def cmd_ledger(args: argparse.Namespace) -> int:
    ledger = Ledger(args.ledger)
    if args.action == "count":
        _print(sys.stdout, str(ledger.count()))
        return 0
    try:
        issue = load_issue(args.issue)
    except ValidationError as exc:
        _print(sys.stderr, f"issue rejected: {exc}")
        return 1
    records = records_from_issue(issue)
    if args.action == "check":
        known = ledger.urls()
        repeats = [r.url for r in records if r.url in known]
        if repeats:
            for url in repeats:
                _print(sys.stdout, f"already printed: {url}")
            return 1
        _print(sys.stdout, f"{len(records)} entries, none printed before")
        return 0
    before = ledger.count()
    added = ledger.append(records)
    _print(
        sys.stdout,
        f"{args.ledger}: {before} -> {before + added} lines, {added} appended, "
        f"{len(records) - added} already present",
    )
    return 0


def cmd_hunt(args: argparse.Namespace) -> int:
    try:
        source = get_source(args.source)
    except SourceError as exc:
        _print(sys.stderr, str(exc))
        return 2
    fetcher = (
        RecordedFetcher.from_directory(args.recorded)
        if args.recorded
        else HttpFetcher(timeout=args.timeout)
    )
    start = _dt.date.fromisoformat(args.start)
    end = _dt.date.fromisoformat(args.end)
    try:
        candidates = source.fetch(fetcher, start, end)
    except SourceError as exc:
        _print(sys.stderr, f"source failed: {exc}")
        return 2
    if args.match:
        needles = [m.lower() for m in args.match]
        candidates = [
            c for c in candidates if any(n in (c.title + " " + c.summary).lower() for n in needles)
        ]
    payload = []
    for candidate in candidates:
        item = asdict(candidate)
        item["published"] = candidate.published.isoformat()
        item["submitted"] = candidate.submitted.isoformat() if candidate.submitted else None
        item["authors"] = list(candidate.authors)
        payload.append(item)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_bytes((text + "\n").encode("utf-8"))
        _print(sys.stdout, f"{len(payload)} candidates written to {args.output}")
    else:
        _print(sys.stdout, text)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    out = Path(args.output)
    issue = load_issue(EXAMPLE)
    html = render_issue(issue)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(html.encode("utf-8"))  # bytes, so Windows keeps LF
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    findings = run_all(html)
    for finding in findings:
        _print(sys.stdout, str(finding))
    if errors(findings):
        _print(sys.stdout, "demo issue did not pass its own gates")
        return 1
    _print(sys.stdout, f"demo issue: {out} ({len(html.encode('utf-8'))} bytes)")
    _print(sys.stdout, f"sha256 {digest}")
    _print(sys.stdout, f"{len(issue.entries)} entries, all gates passed")
    return 0


# --------------------------------------------------------------------- parsing


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signal-harness", description="Build, check and record a daily briefing issue."
    )
    parser.add_argument("--version", action="version", version=f"signal-harness {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="render and gate the bundled example")
    demo.add_argument("-o", "--output", default="build/demo.html")
    demo.set_defaults(func=cmd_demo)

    render = sub.add_parser("render", help="render one issue to HTML")
    render.add_argument("issue")
    render.add_argument("-o", "--output", required=True)
    render.set_defaults(func=cmd_render)

    gate = sub.add_parser("gate", help="run the publication gates on a page")
    gate.add_argument("page")
    gate.add_argument("--only", nargs="*", default=None, help="run only the named checks")
    gate.set_defaults(func=cmd_gate)

    ledger = sub.add_parser("ledger", help="inspect or extend the printed ledger")
    ledger.add_argument("action", choices=("append", "check", "count"))
    ledger.add_argument("issue", nargs="?")
    ledger.add_argument("--ledger", default="ledger/printed.jsonl")
    ledger.set_defaults(func=cmd_ledger)

    hunt = sub.add_parser("hunt", help="list candidates from one source")
    hunt.add_argument("--source", required=True, choices=available())
    hunt.add_argument("--from", dest="start", required=True)
    hunt.add_argument("--to", dest="end", required=True)
    hunt.add_argument(
        "--match",
        nargs="*",
        default=None,
        help="keep candidates whose title or summary contains any of these",
    )
    hunt.add_argument(
        "--recorded",
        default=None,
        help="read from a recorded payload directory instead of the network",
    )
    hunt.add_argument("--timeout", type=float, default=30.0)
    hunt.add_argument("-o", "--output", default=None)
    hunt.set_defaults(func=cmd_hunt)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ledger" and args.action != "count" and not args.issue:
        _print(sys.stderr, "ledger append and check need an issue file")
        return 1
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
