# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Minimal stand-in for Archipelago's Utils."""

from __future__ import annotations

import typing


def async_start(co: typing.Any, name: str | None = None) -> None:
    """No-op in tests; the contract classes never call this."""
    if hasattr(co, "close"):
        co.close()


def user_path(*args: str) -> str:
    import os
    return os.path.join(os.getcwd(), *args)
