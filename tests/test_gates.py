"""Each gate is tested twice: it passes the real page, and it catches a planted fault."""

from __future__ import annotations

import pytest

from signal_harness.gates import checks, errors, run_all


def test_the_rendered_example_passes_every_gate(page):
    assert run_all(page) == []


def test_a_subset_can_be_run_by_name(page):
    assert run_all(page, only=["contents", "dashes"]) == []


def names(findings):
    return {f.check for f in findings}


# --------------------------------------------------------------- story parts


@pytest.mark.parametrize(
    "part", ["How it works", "In simple words", "The pieces.", "What the numbers mean.", "Anchor."]
)
def test_a_full_story_missing_a_part_is_caught(page, part):
    broken = page.replace(part, "Something else", 1)
    assert "story_parts" in names(run_all(broken))


def test_a_brief_missing_its_catch_is_caught(page):
    start = page.index('<article id="s01"')
    end = page.index("</article>", start)
    inner = page[start:end].replace("The catch.", "Note.")
    broken = page[:start] + inner + page[end:]
    found = [f for f in run_all(broken) if f.check == "story_parts"]
    assert found and "s01" in found[0].message


# ------------------------------------------------------------------- content


def test_a_long_sentence_is_caught(page):
    long = " ".join(["word"] * 30) + "."
    broken = page.replace("<p>A team in Helsinki", f"<p>{long} A team in Helsinki", 1)
    found = [f for f in run_all(broken) if f.check == "sentence_length"]
    assert found and "30 words" in found[0].message


def test_a_headline_does_not_run_into_its_paragraph(page):
    """Block boundaries end a sentence, or every entry would fail at once."""
    assert "sentence_length" not in names(run_all(page))


def test_sentence_counting_ignores_markup():
    fragment = "<p>One <b>two</b> three.</p><p>Four five.</p>"
    assert [checks.count_words(s) for s in checks.sentences(fragment)] == [3, 2]


@pytest.mark.parametrize("dash", ["\u2013", "\u2014"])
def test_dashes_are_caught(page, dash):
    broken = page.replace("A team in Helsinki", f"A team {dash} in Helsinki", 1)
    assert "dashes" in names(run_all(broken))


def test_dashes_inside_the_stylesheet_are_ignored(page):
    broken = page.replace("<style>", "<style>/* \u2014 */", 1)
    assert "dashes" not in names(run_all(broken))


# ----------------------------------------------------------------- structure


def test_an_unbalanced_tag_is_caught(page):
    broken = page.replace("</article>", "", 1)
    assert "tag_balance" in names(run_all(broken))


def test_a_dangling_anchor_is_caught(page):
    broken = page.replace('href="#s01"', 'href="#s99"', 1)
    found = [f for f in run_all(broken) if f.check == "anchors"]
    assert found and "s99" in found[0].message


def test_a_duplicate_id_is_caught(page):
    broken = page.replace('id="s02"', 'id="s01"', 1)
    assert "ids" in names(run_all(broken))


def test_an_entry_left_out_of_the_contents_is_caught(page):
    broken = page.replace('<li><a href="#s05">', '<li><a href="#s04">', 1)
    found = [f for f in run_all(broken) if f.check == "contents"]
    assert any("s05" in f.message for f in found)


def test_an_external_link_in_the_contents_is_caught(page):
    broken = page.replace('<li><a href="#s01"', '<li><a href="https://example.org"', 1)
    assert "contents" in names(run_all(broken))


def test_furniture_out_of_order_is_caught(page):
    windows = page[page.index('<section class="windows">') : page.index("</section>") + 10]
    broken = page.replace(windows, "", 1).replace("<footer", windows + "<footer", 1)
    assert "furniture" in names(run_all(broken))


# ------------------------------------------------------------ safety, offline


def test_a_script_tag_is_caught(page):
    broken = page.replace("</body>", "<script>alert(1)</script></body>")
    assert "no_script" in names(run_all(broken))


@pytest.mark.parametrize(
    "snippet",
    [
        '<link rel="stylesheet" href="https://cdn.example.org/a.css">',
        '<img src="https://example.org/a.png">',
    ],
)
def test_external_assets_are_caught(page, snippet):
    broken = page.replace("</head>", snippet + "</head>", 1)
    assert "offline" in names(run_all(broken))


def test_a_missing_primary_link_is_caught(page):
    broken = page.replace('class="src"', 'class="nope"')
    assert "sources" in names(run_all(broken))


def test_a_plain_http_source_is_caught(page):
    broken = page.replace('class="src" href="https://', 'class="src" href="http://', 1)
    assert "sources" in names(run_all(broken))


# ------------------------------------------------------------------- helpers


def test_errors_filters_by_severity():
    findings = [checks.Finding("x", "error", "a"), checks.Finding("y", "warning", "b")]
    assert [f.check for f in errors(findings)] == ["x"]


def test_finding_prints_its_severity():
    assert str(checks.Finding("x", "error", "a")).startswith("[FAIL]")
    assert str(checks.Finding("x", "warning", "a")).startswith("[warn]")
