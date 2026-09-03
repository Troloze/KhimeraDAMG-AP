# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""``normalize_and_sanitize`` -- the single chokepoint that guarantees ASCII.

Every string that reaches the wire passes through here, from two directions:

* outbound, via ``Event.sanitize_string`` (slot names, chat messages, death link causes --
  all of them attacker-ish input in the sense that a player picks them);
* inbound, via ``AgentV1.read_file``, which now runs whole *documents* through it before
  the contract ever sees a row.

That second caller is what makes the guarantees below load-bearing rather than cosmetic.
A document is not a word: it contains newlines, ``$`` terminators and ``\\#`` escapes that
the parser depends on, so a normaliser that "cleans up" any of those silently destroys the
message it was meant to rescue. The structural tests are therefore as important as the
character-mapping ones.

The contract these tests pin, in order of how much damage a violation does:

1. The result is always ASCII. This is the entire reason the function exists.
2. It never raises. It sits inside a read path whose only other outcome is a wedged
   channel, so "reject" is not an available answer -- every input must produce a string.
3. Document structure survives: newlines, ``$``, spaces, and backslash escapes.
4. A genuine ``?`` in the input stays a ``?``; only characters that could not be
   represented become the replacement marker. (The ``\\?`` pre-escape inside the function
   exists exactly to keep these two apart, which is why it gets its own section.)
5. Known typographic characters map to sensible ASCII rather than to the marker.
"""

from __future__ import annotations

import pytest

BS = chr(92)


# --- the core guarantee -----------------------------------------------------

ALL_KINDS = [
    pytest.param("plain ascii", id="ascii"),
    pytest.param("", id="empty"),
    pytest.param("café", id="latin-1-accent"),
    pytest.param("Renée", id="two-accents"),
    pytest.param("naïve", id="diaeresis"),
    pytest.param("Ωmega", id="greek"),
    pytest.param("日本語", id="cjk"),
    pytest.param("Здравствуйте", id="cyrillic"),
    pytest.param("مرحبا", id="arabic"),
    pytest.param("🙂🎮", id="emoji"),
    pytest.param("á", id="combining-mark"),
    pytest.param("\u200bzero\u200bwidth", id="zero-width"),
    pytest.param("ﬁre", id="ligature"),
    pytest.param("Ａ１", id="fullwidth"),
    pytest.param("x²", id="superscript"),
    pytest.param("½", id="vulgar-fraction"),
    pytest.param("\xa0nbsp\xa0", id="nbsp"),
    pytest.param("a\x00b", id="embedded-nul"),
    pytest.param("line one\nline two\n$", id="document-shaped"),
]


@pytest.mark.parametrize("value", ALL_KINDS)
def test_the_result_is_always_ascii(normalize: object, value: str) -> None:
    """The one guarantee the whole communication layer is built on.

    ``write_file`` encodes with ``encoding="ascii"``; a non-ASCII character surviving this
    function turns into a ``UnicodeEncodeError`` at write time, one layer too late to do
    anything about it.
    """
    assert normalize(value).isascii()


@pytest.mark.parametrize("value", ALL_KINDS)
def test_it_never_raises(normalize: object, value: str) -> None:
    """Callers have no fallback.

    ``read_file`` calls this on data it has *already* consumed -- the source file was
    renamed to ``.rd`` and is about to be unlinked. If normalising raises, that document is
    gone and the stray ``.rd`` is left behind for the next tick to trip over. There is no
    input for which raising is a better answer than a degraded string.
    """
    normalize(value)


@pytest.mark.parametrize("value", ALL_KINDS)
def test_it_returns_a_string(normalize: object, value: str) -> None:
    assert isinstance(normalize(value), str)


@pytest.mark.parametrize("value", ALL_KINDS)
def test_it_is_idempotent(normalize: object, value: str) -> None:
    """Sanitising twice must equal sanitising once.

    Not academic: ``read_file`` normalises a recovered ``.rd`` and then normalises the
    fresh document, and ``sanitize_string`` can run over a value that already came off the
    wire. A function that escapes on every pass grows backslashes each time it is applied.
    """
    once = normalize(value)
    assert normalize(once) == once


def test_a_wide_sweep_of_codepoints_all_survive(normalize: object) -> None:
    """A blunt sweep -- if any plane crashes it, the read path crashes with it."""
    failures: list[tuple[int, str]] = []
    for cp in range(0, 0x2FFF):
        char = chr(cp)
        try:
            out = normalize(char)
        except Exception as err:  # noqa: BLE001 - the point is that nothing escapes
            failures.append((cp, f"{type(err).__name__}: {err}"))
            continue
        if not out.isascii():
            failures.append((cp, f"non-ascii output {out!r}"))
    assert failures == [], f"{len(failures)} codepoints failed, first few: {failures[:5]}"


# --- the ASCII fast path ----------------------------------------------------

ASCII_PASSTHROUGH = [
    "plain ascii",
    "",
    "with  double  spaces",
    "punctuation!@%^&*()-=+[]{};:,.<>/",
    "tab\tand\nnewline",
    "$",
    "#",
    f"{BS}#",
    f"{BS}",
    "?",
]


@pytest.mark.parametrize("value", ASCII_PASSTHROUGH)
def test_ascii_input_is_returned_unchanged(normalize: object, value: str) -> None:
    """The fast path must be a true identity.

    Anything already ASCII has, by definition, nothing to normalise. If this path ever
    starts modifying its input it will do so to every document the client reads.
    """
    assert normalize(value) == value


# --- document structure -----------------------------------------------------

def test_newlines_survive(normalize: object) -> None:
    """Rows are newline separated; collapsing them merges every event into one."""
    assert normalize("LOC 1\nLOC 2\n$") == "LOC 1\nLOC 2\n$"


def test_newlines_survive_alongside_non_ascii(normalize: object) -> None:
    # The fast path does not apply here, so this exercises the real body.
    out = normalize("MSG café\nLOC 2\n$")
    assert out.count("\n") == 2, f"row structure lost: {out!r}"
    assert out.endswith("\n$"), f"terminator lost: {out!r}"


def test_the_terminator_is_not_altered(normalize: object) -> None:
    assert normalize("naïve\n$").endswith("\n$")


def test_spaces_survive(normalize: object) -> None:
    """Parameters are space separated; losing a space merges two fields into one."""
    assert normalize("SLOT Renée Deux").count(" ") == 2


def test_an_existing_escape_is_not_doubled(normalize: object) -> None:
    r"""``\#`` is the wire escape for an octothorpe; re-escaping it corrupts the value.

    ``sanitize_string`` escapes ``#`` before calling this function, so by the time a value
    arrives here the escape is already in place.
    """
    assert normalize(f"caf{BS}#é") == f"caf{BS}#e"


def test_no_stray_backslash_is_introduced(normalize: object) -> None:
    """The internal ``\\?`` pre-escape must not leak into the result.

    The function escapes ``?`` before encoding so it can tell a real question mark apart
    from one the encoder produced, then unescapes afterwards. A missed unescape leaves a
    backslash the game will read as an escape sequence.
    """
    assert BS not in normalize("Renée")
    assert BS not in normalize("who? café")


# --- question marks ---------------------------------------------------------

def test_a_genuine_question_mark_survives(normalize: object) -> None:
    """The distinction the ``\\?`` dance exists to preserve.

    ``encode("ascii", "replace")`` emits ``?`` for anything it cannot represent, so
    without the pre-escape an author's own ``?`` is indistinguishable from a dropped
    character and would be rewritten to the replacement marker.
    """
    assert normalize("Renée, ok?") == "Renee, ok?"


def test_an_unrepresentable_character_becomes_the_marker(normalize: object) -> None:
    assert normalize("🙂") == "_"


def test_the_marker_is_configurable(normalize: object) -> None:
    assert normalize("🙂", "?") == "?"
    assert normalize("🙂", "") == ""


def test_both_kinds_of_question_mark_coexist(normalize: object) -> None:
    """One string containing an author's ``?`` and an unrepresentable character."""
    assert normalize("what? 🙂") == "what? _"


# --- the conversion map -----------------------------------------------------

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("´", "'", id="acute-accent"),
        pytest.param("’", "'", id="right-single-quote"),
        pytest.param("‘", "'", id="left-single-quote"),
        pytest.param("“", '"', id="left-double-quote"),
        pytest.param("”", '"', id="right-double-quote"),
        pytest.param("„", '"', id="low-double-quote"),
        pytest.param("«", '"', id="left-guillemet"),
        pytest.param("»", '"', id="right-guillemet"),
        pytest.param("「", '"', id="cjk-open-bracket"),
        pytest.param("」", '"', id="cjk-close-bracket"),
        pytest.param("〜", "~", id="wave-dash"),
        pytest.param("。", ".", id="ideographic-full-stop"),
        pytest.param("、", ",", id="ideographic-comma"),
        pytest.param("—", "-", id="em-dash"),
        pytest.param("–", "-", id="en-dash"),
        pytest.param("‐", "-", id="hyphen"),
        pytest.param("•", "*", id="bullet"),
        pytest.param("÷", "/", id="division-sign"),
        pytest.param("×", "x", id="multiplication-sign"),
        pytest.param("＝", "=", id="fullwidth-equals"),
        pytest.param("±", "+/-", id="plus-minus"),
        pytest.param("≠", "!=", id="not-equal"),
        pytest.param("≤", "<=", id="less-or-equal"),
        pytest.param("≥", ">=", id="greater-or-equal"),
        pytest.param("…", "...", id="ellipsis"),
        pytest.param("\xa0", " ", id="nbsp"),
    ],
)
def test_declared_conversions_produce_their_replacement(normalize: object, value: str, expected: str) -> None:
    """Each entry in ``conversion_map`` must actually be applied.

    These are the characters the map exists to *preserve meaning* for -- falling back to
    the ``_`` marker for a smart quote or an em dash would be technically ASCII and
    practically unreadable.
    """
    assert normalize(value) == expected


def test_a_multi_character_replacement_expands_fully(normalize: object) -> None:
    assert normalize("a…b") == "a...b"
    assert normalize("5±3") == "5+/-3"


def test_conversions_apply_inside_a_sentence(normalize: object) -> None:
    assert normalize("he said “hi” — then left") == 'he said "hi" - then left'


# --- unicode normalisation --------------------------------------------------

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("café", "cafe", id="precomposed-e-acute"),
        pytest.param("café", "cafe", id="decomposed-e-acute"),
        pytest.param("Renée", "Renee", id="mixed"),
        pytest.param("naïve", "naive", id="diaeresis"),
        pytest.param("ﬁre", "fire", id="fi-ligature"),
        pytest.param("Ａ１", "A1", id="fullwidth-alnum"),
        pytest.param("x²", "x2", id="superscript-two"),
    ],
)
def test_decomposable_characters_lose_their_marks(normalize: object, value: str, expected: str) -> None:
    """NFKD splits an accented letter into base + combining mark.

    The base letter is ASCII and should be kept; the combining mark is not representable
    and must be *dropped*, not turned into the replacement marker -- otherwise a player
    named ``Renée`` shows up in chat as ``Rene_e``, which is worse than either ``Renee``
    or leaving the name alone.
    """
    assert normalize(value) == expected


def test_precomposed_and_decomposed_forms_agree(normalize: object) -> None:
    """The same name typed two ways must reach the game as the same string."""
    assert normalize("café") == normalize("café")


def test_a_non_decomposable_script_becomes_markers_not_an_exception(normalize: object) -> None:
    out = normalize("日本語")
    assert out.isascii()
    assert set(out) <= {"_"}, f"expected only replacement markers, got {out!r}"


# --- realistic payloads -----------------------------------------------------

@pytest.mark.parametrize(
    "value",
    [
        pytest.param("Renée found Café Key", id="slot-and-item"),
        pytest.param("Chelshia — died to a spike", id="death-link-cause"),
        pytest.param("«Ωmega» sent 日本語 to Renée", id="chat-line"),
        pytest.param("MSG Renée\nLOC 12\nHBEAT 3\n$", id="whole-document"),
    ],
)
def test_realistic_payloads_stay_wire_safe(normalize: object, value: str) -> None:
    """The end-to-end property: whatever comes out can be written and re-parsed.

    ASCII means ``write_file`` can encode it; the preserved newline count means the
    parser still sees the same number of rows it was given.
    """
    out = normalize(value)
    assert out.isascii()
    out.encode("ascii")  # what write_file does; must not raise
    assert out.count("\n") == value.count("\n"), f"row count changed: {out!r}"
