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
        return re.sub(r"[\x00-\x1F\x7F]", "", entry)

    entry = entry.translate(string_normalization_table)
    entry = unicodedata.normalize("NFKD", entry)
    entry = "".join(c if c.isascii() else unknown_replacement for c in entry if unicodedata.combining(c) == 0)
    return re.sub(r"[\x00-\x1F\x7F]", "", entry)
