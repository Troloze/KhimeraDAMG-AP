import re
import unicodedata

# ruff: disable[RUF001]
string_normalization_table = str.maketrans({
    "´": "'",
    "`": "'",
    "’": "'",
    "‘": "'",
    "ʻ": "'",

    "“": '"',
    "”": '"',
    "„": '"',
    "«": '"',
    "»": '"',
    "「": '"',
    "」": '"',
    "『": '"',
    "』": '"',
    "〃": '"',

    "〜": "~",
    "～": "~",

    "。": ".",

    "、": ",",

    "—": "-",
    "–": "-",
    "‐": "-",
    "‑": "-",
    "・": "-",

    "\xa0": " ",

    "•": "*",

    "÷": "/",
    "⁄": "/",

    "×": "x",

    "＝": "=",

    "±": "+/-",

    "≠": "!=",
    "≤": "<=",
    "≥": ">=",

    "…": "...",
})
# ruff: enable[RUF001]

# Cleans up a string, transforms to ascii and replaces unknown characters with a string.
def normalize_and_sanitize(entry: str, unknown_replacement: str = "_") -> str:
    if entry.isascii():
        return entry

    entry_clean = entry.translate(string_normalization_table)
    normalized = unicodedata.normalize("NFKD", entry_clean)
    normalized_filtered = "".join(c for c in normalized if unicodedata.combining(c) == 0)
    normalized_dirty = normalized_filtered.replace("?", "\\?")
    ascii_dirty = normalized_dirty.encode("ascii", "replace").decode("ascii")
    return re.sub(
        r"\\\?|\?",
        lambda m: "?" if m.group() == "\\?" else unknown_replacement,
        ascii_dirty
    )
