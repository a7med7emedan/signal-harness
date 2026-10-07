"""Publication gates.

These run against the rendered HTML, not against the model, because the file
is what a reader gets. A gate that passes on the data structure and fails on
the page is worth nothing.

Every check returns a list of findings. An empty list means the gate passed.
The command line tool refuses to publish when any finding has severity
``error``.
"""

from __future__ import annotations

import html as _html
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

MAX_WORDS_PER_SENTENCE = 25
DASHES = {"\u2013": "en dash", "\u2014": "em dash"}
FULL_STORY_PARTS = ("How it works", "In simple words", "Glossary.", "The catch.", 'class="why"')
FULL_STORY_STEPS = (
    "The pieces.",
    "What normally goes wrong.",
    "What they actually did.",
    "What the numbers mean.",
    "Anchor.",
)
BRIEF_PARTS = ("Glossary.", "The catch.")
FURNITURE_ORDER = (
    'class="cover"',
    'class="windows"',
    'class="skim"',
    'class="lead',
    'class="band',
    'class="foot"',
)

PAIRED_TAGS = (
    "div",
    "article",
    "section",
    "p",
    "span",
    "ol",
    "ul",
    "li",
    "table",
    "header",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
)

INLINE_TAGS = re.compile(r"</?(?:b|i|em|strong|sup|sub|a)\b[^>]*>")
ANY_TAG = re.compile(r"<[^>]+>")
STYLE_BLOCK = re.compile(r"<style>.*?</style>", re.S)


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str  # "error" or "warning"
    message: str

    def __str__(self) -> str:
        mark = "FAIL" if self.severity == "error" else "warn"
        return f"[{mark}] {self.check}: {self.message}"


Check = Callable[[str], list[Finding]]


# --------------------------------------------------------------------- helpers


def body_of(doc: str) -> str:
    """The document with its stylesheet removed, so CSS is never read as prose."""
    return STYLE_BLOCK.sub("", doc)


def sentences(fragment: str) -> list[str]:
    """Split an HTML fragment into sentences.

    Block boundaries end a sentence, because a headline is not the first clause
    of the paragraph under it. Inline emphasis does not.
    """
    text = INLINE_TAGS.sub("", fragment)
    text = ANY_TAG.sub(" | ", text)
    text = _html.unescape(text)
    out: list[str] = []
    for segment in text.split("|"):
        segment = re.sub(r"\s+", " ", segment).strip()
        if not segment:
            continue
        for piece in re.split(r"(?<=[.!?:])\s+", segment):
            piece = piece.strip()
            if piece:
                out.append(piece)
    return out


def count_words(sentence: str) -> int:
    return len([w for w in sentence.split() if re.search(r"[A-Za-z0-9]", w)])


def articles(doc: str) -> list[tuple[str, str, str]]:
    """Return (id, attributes, inner html) for every article element."""
    out = []
    for attrs, inner in re.findall(r"<article\b([^>]*)>(.*?)</article>", doc, re.S):
        match = re.search(r'id="([^"]+)"', attrs)
        out.append((match.group(1) if match else "", attrs, inner))
    return out


# ---------------------------------------------------------------------- checks


def check_no_script(doc: str) -> list[Finding]:
    if "<script" in doc.lower():
        return [Finding("no_script", "error", "the page contains a script tag")]
    return []


def check_no_external_assets(doc: str) -> list[Finding]:
    """The page must open offline: no linked stylesheet, font or image host."""
    findings = []
    for pattern, what in (
        (r"<link\b[^>]*rel=\"?stylesheet", "linked stylesheet"),
        (r"@import", "CSS import"),
        (r"<img\b[^>]*src=\"https?://", "remote image"),
        (r"url\(\s*['\"]?https?://", "remote CSS resource"),
    ):
        if re.search(pattern, doc, re.I):
            findings.append(Finding("offline", "error", f"page references a {what}"))
    return findings


def check_dashes(doc: str) -> list[Finding]:
    findings = []
    for char, name in DASHES.items():
        index = doc.find(char)
        if index >= 0:
            context = doc[max(0, index - 50) : index + 40].replace("\n", " ")
            findings.append(Finding("dashes", "error", f"{name} found: ...{context}..."))
    return findings


def check_sentence_length(doc: str) -> list[Finding]:
    findings = []
    for entry_id, _attrs, inner in articles(doc):
        for sentence in sentences(inner):
            words = count_words(sentence)
            if words > MAX_WORDS_PER_SENTENCE:
                findings.append(
                    Finding(
                        "sentence_length", "error", f"{entry_id}: {words} words: {sentence[:120]}"
                    )
                )
    return findings


def check_tag_balance(doc: str) -> list[Finding]:
    findings = []
    for tag in PAIRED_TAGS:
        opened = len(re.findall(rf"<{tag}\b", doc))
        closed = len(re.findall(rf"</{tag}>", doc))
        if opened != closed:
            findings.append(
                Finding(
                    "tag_balance",
                    "error",
                    f"<{tag}> opened {opened} times and closed {closed} times",
                )
            )
    return findings


def check_ids_and_anchors(doc: str) -> list[Finding]:
    findings = []
    ids = re.findall(r'id="([a-z0-9-]+)"', doc)
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        findings.append(Finding("ids", "error", f"duplicate ids: {duplicates}"))
    anchors = set(re.findall(r'href="#([a-z0-9-]+)"', doc))
    dangling = sorted(anchors - set(ids))
    if dangling:
        findings.append(Finding("anchors", "error", f"anchors with no target: {dangling}"))
    story_ids = [i for i in ids if re.fullmatch(r"s\d{2}", i)]
    if story_ids != sorted(story_ids):
        findings.append(Finding("ids", "error", "story ids do not ascend in document order"))
    return findings


def check_contents_list(doc: str) -> list[Finding]:
    if 'class="skim"' not in doc:
        return [Finding("contents", "error", "no contents section")]
    findings = []
    skim = doc.split('class="skim"', 1)[1].split("</section>", 1)[0]
    lists = re.findall(r"<ol>(.*?)</ol>", skim, re.S)
    if len(lists) != 1:
        return [Finding("contents", "error", f"contents must be one list, found {len(lists)}")]
    items = re.findall(r"<li>(.*?)</li>", lists[0], re.S)
    if not items:
        findings.append(Finding("contents", "error", "the contents list is empty"))
    for number, item in enumerate(items, start=1):
        if 'href="#' not in item:
            findings.append(Finding("contents", "error", f"line {number} has no internal anchor"))
    if "http" in lists[0]:
        findings.append(Finding("contents", "error", "the contents list contains an external link"))
    article_ids = {entry_id for entry_id, _a, _i in articles(doc)}
    listed = set(re.findall(r'href="#([a-z0-9-]+)"', lists[0]))
    missing = sorted(article_ids - listed)
    if missing:
        findings.append(
            Finding("contents", "error", f"entries missing from the contents: {missing}")
        )
    return findings


def check_story_parts(doc: str) -> list[Finding]:
    """Every full story carries all its parts. Every brief carries its minimum."""
    findings = []
    for entry_id, attrs, inner in articles(doc):
        is_full = 'class="lead' in attrs or 'class="story' in attrs
        required = FULL_STORY_PARTS + FULL_STORY_STEPS if is_full else BRIEF_PARTS
        for part in required:
            if part not in inner:
                label = part.replace('class="why"', "why it matters line")
                findings.append(Finding("story_parts", "error", f"{entry_id}: missing {label}"))
    return findings


def check_sources_present(doc: str) -> list[Finding]:
    findings = []
    for entry_id, _attrs, inner in articles(doc):
        links = re.findall(r'<a class="src" href="([^"]+)"', inner)
        if not links:
            findings.append(Finding("sources", "error", f"{entry_id}: no primary link"))
        for link in links:
            if not link.startswith("https://"):
                findings.append(
                    Finding("sources", "error", f"{entry_id}: primary link is not https: {link}")
                )
    return findings


def check_furniture_order(doc: str) -> list[Finding]:
    positions = [doc.find(marker) for marker in FURNITURE_ORDER]
    missing = [m for m, p in zip(FURNITURE_ORDER, positions, strict=True) if p < 0]
    if missing:
        return [Finding("furniture", "error", f"missing sections: {missing}")]
    if positions != sorted(positions):
        return [Finding("furniture", "error", "sections are out of order")]
    return []


ALL_CHECKS: tuple[tuple[str, Check], ...] = (
    ("story_parts", check_story_parts),
    ("contents", check_contents_list),
    ("sentence_length", check_sentence_length),
    ("dashes", lambda doc: check_dashes(body_of(doc))),
    ("tag_balance", check_tag_balance),
    ("ids_and_anchors", check_ids_and_anchors),
    ("sources", check_sources_present),
    ("furniture", check_furniture_order),
    ("no_script", check_no_script),
    ("offline", check_no_external_assets),
)


def run_all(doc: str, only: Iterable[str] | None = None) -> list[Finding]:
    """Run every gate, or the named subset, in a fixed order."""
    wanted = set(only) if only else None
    findings: list[Finding] = []
    for name, check in ALL_CHECKS:
        if wanted and name not in wanted:
            continue
        findings.extend(check(doc))
    return findings


def errors(findings: Iterable[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "error"]
